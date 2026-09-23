"""SQLite migrations and atomic bundle persistence for World Historian."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PERSONAL_RELATIONS = {
    "experienced", "affected_by", "worked_on", "discussed", "read_about",
    "anticipated", "intellectual_context", "career_context", "location_context",
    "social_context", "later_recalled",
}

# The order is also the deterministic tie-break order used by migration 0006.
ENTITY_KINDS = (
    "company", "organization", "person", "product", "model", "software",
    "benchmark", "aggregator", "media", "government", "place", "concept",
    "unknown",
)
ENTITY_KIND_SET = frozenset(ENTITY_KINDS)


class ChronicleError(ValueError):
    """Raised when a bundle would violate Chronicle invariants."""


def _now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def default_db_path() -> Path:
    state_dir = os.environ.get("PAP_AGENT_STATE_DIR")
    base = Path(state_dir) if state_dir else repo_root() / "var" / "world-historian"
    return base / "chronicle.sqlite"


def connect(path: Path | None = None) -> sqlite3.Connection:
    db_path = Path(path or default_db_path())
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn


def migrate(conn: sqlite3.Connection) -> list[str]:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations ("
        "version TEXT PRIMARY KEY, applied_at TEXT NOT NULL)"
    )
    applied = {row[0] for row in conn.execute("SELECT version FROM schema_migrations")}
    completed: list[str] = []
    migrations = Path(__file__).with_name("migrations")
    for path in sorted(migrations.glob("*.sql")):
        if path.stem in applied:
            continue
        conn.executescript(path.read_text(encoding="utf-8"))
        conn.execute(
            "INSERT INTO schema_migrations(version, applied_at) VALUES (?, ?)",
            (path.stem, _now()),
        )
        conn.commit()
        completed.append(path.stem)
    return completed


def initialize(path: Path | None = None) -> tuple[Path, list[str]]:
    db_path = Path(path or default_db_path())
    for child in ("raw", "reports", "cache"):
        (db_path.parent / child).mkdir(parents=True, exist_ok=True)
    with connect(db_path) as conn:
        completed = migrate(conn)
    return db_path, completed


def _stable(prefix: str, *parts: object) -> str:
    material = "\x1f".join("" if part is None else str(part).strip().casefold() for part in parts)
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()[:20]
    return f"{prefix}_{digest}"


def stable_id(prefix: str, *parts: object) -> str:
    """Public stable-id helper (same scheme as ``_stable``) for runtime modules
    that must insert rows with IDs consistent with ``store_bundle``."""
    return _stable(prefix, *parts)


def _json(value: object, default: object) -> str:
    return json.dumps(default if value is None else value, ensure_ascii=False, sort_keys=True)


def _items(bundle: dict[str, Any], key: str) -> list[dict[str, Any]]:
    value = bundle.get(key, [])
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise ChronicleError(f"{key} must be a list of objects")
    return value


def _required(item: dict[str, Any], key: str, where: str) -> Any:
    value = item.get(key)
    if value is None or (isinstance(value, str) and not value.strip()):
        raise ChronicleError(f"{where}.{key} is required")
    return value


def _confidence(value: object, where: str, default: float = 0.5) -> float:
    result = default if value is None else value
    if isinstance(result, bool) or not isinstance(result, (int, float)) or not 0 <= result <= 1:
        raise ChronicleError(f"{where} must be a number in 0..1")
    return float(result)


def _event_title(item: dict[str, Any]) -> str | None:
    """Validate an optional, deliberately short event heading.

    ``summary`` remains the evidence-bearing event body.  Older bundles did
    not carry a title, so absence is supported for backwards compatibility;
    the Obsidian renderer supplies a compact date-based fallback for them.
    """
    value = item.get("title")
    if value is None:
        return None
    if not isinstance(value, str):
        raise ChronicleError("event.title must be a string")
    value = " ".join(value.split())
    if not value:
        raise ChronicleError("event.title must not be empty")
    if len(value) > 60:
        raise ChronicleError("event.title must be at most 60 characters")
    return value


def _entity_kind(value: object, where: str) -> str:
    if not isinstance(value, str) or value not in ENTITY_KIND_SET:
        raise ChronicleError(
            f"{where}.kind must be one of: {', '.join(ENTITY_KINDS)}"
        )
    return value


def _ensure_entity(conn: sqlite3.Connection, name: str, kind: str, now: str,
                   aliases: object | None = None) -> str:
    """Find an entity by name and only upgrade an unclassified row in place."""
    row = conn.execute("SELECT id, kind FROM entities WHERE name = ?", (name,)).fetchone()
    if row is None:
        entity_id = _stable("ent", name)
        conn.execute(
            "INSERT INTO entities(id, name, kind, aliases_json, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (entity_id, name, kind, _json(aliases, []), now),
        )
        return entity_id
    entity_id, existing_kind = str(row["id"]), str(row["kind"])
    if existing_kind == "unknown" and kind != "unknown":
        conn.execute("UPDATE entities SET kind = ? WHERE id = ?", (kind, entity_id))
    if aliases is not None:
        conn.execute("UPDATE entities SET aliases_json = ? WHERE id = ?",
                     (_json(aliases, []), entity_id))
    return entity_id


def store_bundle(conn: sqlite3.Connection, bundle: dict[str, Any]) -> dict[str, Any]:
    """Validate and atomically upsert one cross-referenced Chronicle bundle.

    Returns ``touched_threads``: threads whose stored content was created or
    modified by this bundle (thread upserts, events attached to a thread,
    claim changes on member events, thread-scoped questions/queries, and
    relations with a thread endpoint). Pure event-level or candidate-level
    writes return an empty list, so callers can skip side effects such as
    the Obsidian export.
    """
    if not isinstance(bundle, dict):
        raise ChronicleError("bundle must be a JSON object")
    migrate(conn)
    now = _now()
    refs: dict[str, str] = {}
    counts: dict[str, int] = {}
    touched: set[str] = set()

    def remember(item: dict[str, Any], identifier: str) -> None:
        ref = item.get("ref")
        if ref is not None:
            if not isinstance(ref, str) or not ref:
                raise ChronicleError("bundle refs must be non-empty strings")
            if ref in refs and refs[ref] != identifier:
                raise ChronicleError(f"duplicate bundle ref {ref!r}")
            refs[ref] = identifier

    def resolve(value: object, where: str) -> str:
        if not isinstance(value, str) or not value:
            raise ChronicleError(f"{where} must be a non-empty id or ref")
        return refs.get(value, value)

    def ensure_entity(raw_entity: object, where: str) -> tuple[str, str]:
        if isinstance(raw_entity, str):
            name, kind, role = raw_entity, "unknown", "mentioned"
        elif isinstance(raw_entity, dict):
            name = raw_entity.get("name")
            kind = raw_entity.get("kind", "unknown")
            role = raw_entity.get("role", "mentioned")
        else:
            raise ChronicleError(f"{where} must contain strings or entity objects")
        if not isinstance(name, str) or not name.strip():
            raise ChronicleError(f"{where} must contain entity names")
        return _ensure_entity(conn, name, _entity_kind(kind, where), now), str(role)

    try:
        conn.execute("BEGIN IMMEDIATE")

        for item in _items(bundle, "sources"):
            url = str(_required(item, "canonical_url", "source"))
            title = str(_required(item, "title", "source"))
            identifier = str(item.get("id") or _stable(
                "src", url, item.get("published_at"), item.get("content_hash")
            ))
            remember(item, identifier)
            conn.execute(
                """INSERT INTO sources
                   (id, canonical_url, title, publisher, source_kind, published_at,
                    updated_at, fetched_at, content_hash, metadata_json, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(id) DO UPDATE SET
                     title=excluded.title, publisher=excluded.publisher,
                     source_kind=excluded.source_kind, updated_at=excluded.updated_at,
                     fetched_at=excluded.fetched_at, content_hash=excluded.content_hash,
                     metadata_json=excluded.metadata_json""",
                (identifier, url, title, item.get("publisher"), item.get("source_kind", "unknown"),
                 item.get("published_at"), item.get("updated_at"), item.get("fetched_at", now),
                 item.get("content_hash"), _json(item.get("metadata"), {}), now),
            )
            counts["sources"] = counts.get("sources", 0) + 1

        for item in _items(bundle, "entities"):
            name = str(_required(item, "name", "entity"))
            kind = _entity_kind(item.get("kind", "unknown"), "entity")
            identifier = _ensure_entity(conn, name, kind, now, item.get("aliases"))
            remember(item, identifier)
            counts["entities"] = counts.get("entities", 0) + 1

        for item in _items(bundle, "threads"):
            title = str(_required(item, "title", "thread"))
            identifier = str(item.get("id") or _stable("thr", title))
            remember(item, identifier)
            touched.add(identifier)
            conn.execute(
                """INSERT INTO threads
                   (id, title, status, priority, seed_type, seed_text, last_checked_at,
                    next_check_at, quiet_count, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(id) DO UPDATE SET
                     title=excluded.title, status=excluded.status, priority=excluded.priority,
                     seed_type=COALESCE(excluded.seed_type, threads.seed_type),
                     seed_text=COALESCE(excluded.seed_text, threads.seed_text),
                     last_checked_at=COALESCE(excluded.last_checked_at, threads.last_checked_at),
                     next_check_at=COALESCE(excluded.next_check_at, threads.next_check_at),
                     quiet_count=excluded.quiet_count, updated_at=excluded.updated_at""",
                (identifier, title, item.get("status", "active"), item.get("priority", "normal"),
                 item.get("seed_type", "user_instruction"), item.get("seed_text"),
                 item.get("last_checked_at"), item.get("next_check_at"),
                 int(item.get("quiet_count", 0)), now, now),
            )
            counts["threads"] = counts.get("threads", 0) + 1

            for question in item.get("questions", []):
                if not isinstance(question, str) or not question.strip():
                    raise ChronicleError("thread.questions must contain non-empty strings")
                qid = _stable("qst", identifier, question)
                conn.execute(
                    """INSERT INTO open_questions
                       (id, thread_id, question, status, created_at, updated_at)
                       VALUES (?, ?, ?, 'open', ?, ?)
                       ON CONFLICT(id) DO UPDATE SET updated_at=excluded.updated_at""",
                    (qid, identifier, question, now, now),
                )
            for raw_query in item.get("watch_queries", []):
                query = raw_query if isinstance(raw_query, str) else raw_query.get("query")
                kind = "exact" if isinstance(raw_query, str) else raw_query.get("kind", "exact")
                if not isinstance(query, str) or not query.strip():
                    raise ChronicleError("thread.watch_queries must contain queries")
                qid = _stable("qry", identifier, query, kind)
                conn.execute(
                    """INSERT INTO watch_queries
                       (id, thread_id, query, query_kind, active, created_at)
                       VALUES (?, ?, ?, ?, 1, ?)
                       ON CONFLICT(id) DO UPDATE SET active=1""",
                    (qid, identifier, query, kind, now),
                )
            for raw_entity in item.get("entity_names", []):
                entity_id, _ = ensure_entity(raw_entity, "thread.entity_names")
                conn.execute(
                    "INSERT OR IGNORE INTO thread_entities(thread_id, entity_id) VALUES (?, ?)",
                    (identifier, entity_id),
                )

        for item in _items(bundle, "events"):
            summary = str(_required(item, "summary", "event"))
            title = _event_title(item)
            identifier = str(item.get("id") or _stable(
                "evt", summary, item.get("occurred_at"), item.get("reported_at")
            ))
            remember(item, identifier)
            conn.execute(
                """INSERT INTO events
                   (id, title, summary, occurred_at, occurred_at_precision, reported_at,
                    observed_at, confidence, status, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(id) DO UPDATE SET
                     title=COALESCE(excluded.title, events.title),
                     summary=excluded.summary, occurred_at=excluded.occurred_at,
                     occurred_at_precision=excluded.occurred_at_precision,
                     reported_at=excluded.reported_at, confidence=excluded.confidence,
                     status=excluded.status, updated_at=excluded.updated_at""",
                (identifier, title, summary, item.get("occurred_at"),
                 item.get("occurred_at_precision", "unknown"), item.get("reported_at"),
                 item.get("observed_at", now), _confidence(item.get("confidence"), "event.confidence"),
                 item.get("status", "active"), now, now),
            )
            counts["events"] = counts.get("events", 0) + 1
            for thread_ref in item.get("thread_refs", []):
                thread_id = resolve(thread_ref, "event.thread_refs[]")
                conn.execute(
                    """INSERT OR IGNORE INTO thread_events
                       (thread_id, event_id, membership_confidence, created_at)
                       VALUES (?, ?, ?, ?)""",
                    (thread_id, identifier,
                     _confidence(item.get("membership_confidence"), "membership_confidence", 1.0), now),
                )
                touched.add(thread_id)
            for raw_entity in item.get("entity_names", []):
                entity_id, role = ensure_entity(raw_entity, "event.entity_names")
                conn.execute(
                    "INSERT OR IGNORE INTO event_entities(event_id, entity_id, role) VALUES (?, ?, ?)",
                    (identifier, entity_id, role),
                )

        for item in _items(bundle, "claims"):
            statement = str(_required(item, "statement", "claim"))
            event_id = resolve(_required(item, "event_ref", "claim"), "claim.event_ref")
            source_id = resolve(_required(item, "source_ref", "claim"), "claim.source_ref")
            identifier = str(item.get("id") or _stable("clm", event_id, source_id, statement))
            remember(item, identifier)
            superseded = item.get("superseded_by")
            conn.execute(
                """INSERT INTO claims
                   (id, event_id, source_id, statement, asserted_at, confidence, status,
                    superseded_by, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(id) DO UPDATE SET
                     confidence=excluded.confidence, status=excluded.status,
                     superseded_by=excluded.superseded_by, updated_at=excluded.updated_at""",
                (identifier, event_id, source_id, statement, item.get("asserted_at", now),
                 _confidence(item.get("confidence"), "claim.confidence"),
                 item.get("status", "active"),
                 resolve(superseded, "claim.superseded_by") if superseded else None, now, now),
            )
            counts["claims"] = counts.get("claims", 0) + 1
            for row in conn.execute(
                "SELECT thread_id FROM thread_events WHERE event_id = ?", (event_id,)
            ):
                touched.add(row[0])

        for item in _items(bundle, "quotes"):
            quote_text = str(_required(item, "quote_text", "quote"))
            speaker = item.get("speaker")
            title = item.get("title")
            event_id = resolve(item["event_ref"], "quote.event_ref") if item.get("event_ref") else None
            source_id = resolve(item["source_ref"], "quote.source_ref") if item.get("source_ref") else None
            if event_id is None and source_id is None:
                raise ChronicleError("quote requires event_ref and/or source_ref")
            quote_format = item.get("quote_format", "text")
            if quote_format not in ("text", "markdown"):
                raise ChronicleError("quote.quote_format must be 'text' or 'markdown'")
            identifier = str(item.get("id") or _stable(
                "qte", speaker, title, quote_text[:400]
            ))
            remember(item, identifier)
            slug = item.get("slug")
            if slug is not None and (not isinstance(slug, str) or not slug.strip()):
                raise ChronicleError("quote.slug must be a non-empty string when present")
            conn.execute(
                """INSERT INTO quotes
                   (id, event_id, source_id, speaker, title, quote_text, quote_format,
                    url, slug, fetched_at, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(id) DO UPDATE SET
                     event_id=excluded.event_id, source_id=excluded.source_id,
                     speaker=excluded.speaker, title=excluded.title,
                     quote_text=excluded.quote_text, quote_format=excluded.quote_format,
                     url=excluded.url, slug=excluded.slug, fetched_at=excluded.fetched_at,
                     updated_at=excluded.updated_at""",
                (identifier, event_id, source_id, speaker, title, quote_text,
                 quote_format, item.get("url"), slug,
                 item.get("fetched_at", now), now, now),
            )
            counts["quotes"] = counts.get("quotes", 0) + 1
            if event_id:
                for row in conn.execute(
                    "SELECT thread_id FROM thread_events WHERE event_id = ?", (event_id,)
                ):
                    touched.add(row[0])

        for item in _items(bundle, "questions"):
            thread_id = resolve(_required(item, "thread_ref", "question"), "question.thread_ref")
            question = str(_required(item, "question", "question"))
            identifier = str(item.get("id") or _stable("qst", thread_id, question))
            touched.add(thread_id)
            answer_ref = item.get("answer_event_ref")
            conn.execute(
                """INSERT INTO open_questions
                   (id, thread_id, question, status, answer_event_id, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(id) DO UPDATE SET status=excluded.status,
                     answer_event_id=excluded.answer_event_id, updated_at=excluded.updated_at""",
                (identifier, thread_id, question, item.get("status", "open"),
                 resolve(answer_ref, "question.answer_event_ref") if answer_ref else None, now, now),
            )
            counts["questions"] = counts.get("questions", 0) + 1

        for item in _items(bundle, "watch_queries"):
            thread_id = resolve(_required(item, "thread_ref", "watch_query"),
                                "watch_query.thread_ref")
            query = str(_required(item, "query", "watch_query"))
            kind = str(item.get("kind", "exact"))
            identifier = str(item.get("id") or _stable("qry", thread_id, query, kind))
            touched.add(thread_id)
            conn.execute(
                """INSERT INTO watch_queries
                   (id, thread_id, query, query_kind, active, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)
                   ON CONFLICT(id) DO UPDATE SET active=excluded.active""",
                (identifier, thread_id, query, kind, 1 if item.get("active", True) else 0, now),
            )
            counts["watch_queries"] = counts.get("watch_queries", 0) + 1

        for item in _items(bundle, "relations"):
            src_id = resolve(_required(item, "src_ref", "relation"), "relation.src_ref")
            dst_id = resolve(_required(item, "dst_ref", "relation"), "relation.dst_ref")
            relation_type = str(_required(item, "relation_type", "relation"))
            identifier = str(item.get("id") or _stable("rel", src_id, dst_id, relation_type))
            conn.execute(
                """INSERT INTO relations
                   (id, src_type, src_id, dst_type, dst_id, relation_type, confidence,
                    evidence_json, status, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(id) DO UPDATE SET confidence=excluded.confidence,
                     evidence_json=excluded.evidence_json, status=excluded.status,
                     updated_at=excluded.updated_at""",
                (identifier, item.get("src_type", "event"), src_id,
                 item.get("dst_type", "event"), dst_id, relation_type,
                 _confidence(item.get("confidence"), "relation.confidence"),
                 _json(item.get("evidence"), []), item.get("status", "active"), now, now),
            )
            counts["relations"] = counts.get("relations", 0) + 1
            if str(item.get("src_type", "event")) == "thread":
                touched.add(src_id)
            if str(item.get("dst_type", "event")) == "thread":
                touched.add(dst_id)

        for item in _items(bundle, "interpretations"):
            earlier = resolve(_required(item, "earlier_event_ref", "interpretation"),
                              "interpretation.earlier_event_ref")
            later = resolve(_required(item, "later_event_ref", "interpretation"),
                            "interpretation.later_event_ref")
            statement = str(_required(item, "statement", "interpretation"))
            identifier = str(item.get("id") or _stable("int", earlier, later, statement))
            conn.execute(
                """INSERT INTO interpretations
                   (id, earlier_event_id, later_event_id, statement, confidence,
                    evidence_json, status, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(id) DO UPDATE SET confidence=excluded.confidence,
                     evidence_json=excluded.evidence_json, status=excluded.status,
                     updated_at=excluded.updated_at""",
                (identifier, earlier, later, statement,
                 _confidence(item.get("confidence"), "interpretation.confidence"),
                 _json(item.get("evidence"), []), item.get("status", "active"), now, now),
            )
            counts["interpretations"] = counts.get("interpretations", 0) + 1

        for item in _items(bundle, "personal_links"):
            event_id = resolve(_required(item, "world_event_ref", "personal_link"),
                               "personal_link.world_event_ref")
            personal_id = str(_required(item, "personal_event_id", "personal_link"))
            relation_type = str(_required(item, "relation_type", "personal_link"))
            if relation_type not in PERSONAL_RELATIONS:
                raise ChronicleError(f"unsupported personal relation {relation_type!r}")
            explanation = str(_required(item, "explanation", "personal_link"))
            identifier = str(item.get("id") or _stable(
                "plk", event_id, personal_id, relation_type
            ))
            conn.execute(
                """INSERT INTO personal_links
                   (id, world_event_id, personal_event_id, relation_type, explanation,
                    confidence, evidence_json, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(id) DO UPDATE SET explanation=excluded.explanation,
                     confidence=excluded.confidence, evidence_json=excluded.evidence_json,
                     updated_at=excluded.updated_at""",
                (identifier, event_id, personal_id, relation_type, explanation,
                 _confidence(item.get("confidence"), "personal_link.confidence"),
                 _json(item.get("evidence"), []), now, now),
            )
            counts["personal_links"] = counts.get("personal_links", 0) + 1

        for item in _items(bundle, "discovery_candidates"):
            title = str(_required(item, "title", "discovery_candidate"))
            kind = str(_required(item, "candidate_type", "discovery_candidate"))
            identifier = str(item.get("id") or _stable("can", kind, title))
            conn.execute(
                """INSERT INTO discovery_candidates
                   (id, candidate_type, title, relation_score, payload_json, status,
                    created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(id) DO UPDATE SET relation_score=excluded.relation_score,
                     payload_json=excluded.payload_json, status=excluded.status,
                     updated_at=excluded.updated_at""",
                (identifier, kind, title,
                 _confidence(item.get("relation_score"), "candidate.relation_score"),
                 _json(item.get("payload"), {}), item.get("status", "candidate"), now, now),
            )
            counts["discovery_candidates"] = counts.get("discovery_candidates", 0) + 1

        for item in _items(bundle, "reports"):
            mode = str(_required(item, "mode", "report"))
            body = str(_required(item, "body", "report"))
            window_end = str(item.get("window_end", now))
            identifier = str(item.get("id") or _stable("rpt", mode, item.get("window_start"), window_end))
            conn.execute(
                """INSERT INTO reports
                   (id, mode, window_start, window_end, body, significance, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(id) DO UPDATE SET body=excluded.body,
                     significance=excluded.significance""",
                (identifier, mode, item.get("window_start"), window_end, body,
                 _confidence(item.get("significance"), "report.significance"), now),
            )
            counts["reports"] = counts.get("reports", 0) + 1

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return {"refs": refs, "counts": counts, "touched_threads": sorted(touched)}


def search(conn: sqlite3.Connection, query: str, limit: int = 20) -> list[dict[str, Any]]:
    pattern = f"%{query}%"
    rows = conn.execute(
        """SELECT 'thread' AS kind, id, title AS label, updated_at AS timestamp
           FROM threads WHERE title LIKE ?
           UNION ALL
           SELECT 'event', id, summary, observed_at FROM events WHERE summary LIKE ?
           UNION ALL
           SELECT 'entity', id, name, created_at FROM entities WHERE name LIKE ?
           ORDER BY timestamp DESC LIMIT ?""",
        (pattern, pattern, pattern, limit),
    )
    return [dict(row) for row in rows]


def thread_detail(conn: sqlite3.Connection, thread_id: str) -> dict[str, Any] | None:
    row = conn.execute("SELECT * FROM threads WHERE id = ?", (thread_id,)).fetchone()
    if row is None:
        return None
    result = dict(row)
    result["questions"] = [dict(item) for item in conn.execute(
        "SELECT * FROM open_questions WHERE thread_id = ? ORDER BY created_at", (thread_id,)
    )]
    result["watch_queries"] = [dict(item) for item in conn.execute(
        "SELECT * FROM watch_queries WHERE thread_id = ? AND active = 1 ORDER BY created_at",
        (thread_id,),
    )]
    result["events"] = [dict(item) for item in conn.execute(
        """SELECT events.* FROM events JOIN thread_events ON events.id = thread_events.event_id
           WHERE thread_events.thread_id = ? ORDER BY COALESCE(occurred_at, reported_at, observed_at)""",
        (thread_id,),
    )]
    return result


def thread_snapshot(conn: sqlite3.Connection, thread_id: str) -> dict[str, Any] | None:
    """Everything the Obsidian projection needs for one thread, or ``None``."""
    row = conn.execute("SELECT * FROM threads WHERE id = ?", (thread_id,)).fetchone()
    if row is None:
        return None
    snapshot: dict[str, Any] = dict(row)
    snapshot["thread_entities"] = [dict(item) for item in conn.execute(
        """SELECT entities.name, entities.kind FROM thread_entities
           JOIN entities ON entities.id = thread_entities.entity_id
           WHERE thread_entities.thread_id = ? ORDER BY entities.name""",
        (thread_id,),
    )]
    snapshot["questions"] = [dict(item) for item in conn.execute(
        "SELECT * FROM open_questions WHERE thread_id = ? ORDER BY created_at",
        (thread_id,),
    )]
    snapshot["watch_queries"] = [dict(item) for item in conn.execute(
        "SELECT * FROM watch_queries WHERE thread_id = ? AND active = 1 ORDER BY created_at",
        (thread_id,),
    )]
    events = [dict(item) for item in conn.execute(
        """SELECT events.* FROM events JOIN thread_events
           ON events.id = thread_events.event_id
           WHERE thread_events.thread_id = ?
           ORDER BY COALESCE(occurred_at, reported_at, observed_at)""",
        (thread_id,),
    )]
    for event in events:
        event["claims"] = [dict(item) for item in conn.execute(
            """SELECT claims.*, sources.title AS source_title,
                      sources.publisher AS source_publisher,
                      sources.source_kind AS source_kind
               FROM claims JOIN sources ON sources.id = claims.source_id
               WHERE claims.event_id = ? ORDER BY claims.created_at, claims.id""",
            (event["id"],),
        )]
        event["entities"] = [dict(item) for item in conn.execute(
            """SELECT entities.name, entities.kind, event_entities.role
               FROM event_entities JOIN entities ON entities.id = event_entities.entity_id
               WHERE event_entities.event_id = ? ORDER BY entities.name""",
            (event["id"],),
        )]
        event["quotes"] = [dict(item) for item in conn.execute(
            """SELECT quotes.*, sources.title AS source_title,
                      sources.publisher AS source_publisher,
                      sources.source_kind AS source_kind
               FROM quotes LEFT JOIN sources ON sources.id = quotes.source_id
               WHERE quotes.event_id = ? ORDER BY quotes.created_at, quotes.id""",
            (event["id"],),
        )]
    snapshot["events"] = events
    snapshot["relations"] = [dict(item) for item in conn.execute(
        """SELECT * FROM relations
           WHERE (src_type = 'thread' AND src_id = ?)
              OR (dst_type = 'thread' AND dst_id = ?)
           ORDER BY created_at""",
        (thread_id, thread_id),
    )]
    event_ids = [event["id"] for event in events]
    interpretations: list[dict[str, Any]] = []
    if event_ids:
        placeholders = ",".join("?" for _ in event_ids)
        interpretations = [dict(item) for item in conn.execute(
            f"""SELECT * FROM interpretations
                WHERE earlier_event_id IN ({placeholders})
                   OR later_event_id IN ({placeholders})
                ORDER BY created_at""",
            (*event_ids, *event_ids),
        )]
    snapshot["interpretations"] = interpretations
    return snapshot


def all_thread_ids(conn: sqlite3.Connection) -> list[str]:
    return [row[0] for row in conn.execute("SELECT id FROM threads ORDER BY id")]


def stats(conn: sqlite3.Connection) -> dict[str, int]:
    tables = ("sources", "claims", "events", "threads", "entities", "relations",
              "interpretations", "personal_links", "discovery_candidates", "reports")
    return {table: int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
            for table in tables}
