"""Canonical pap.event.v2 storage, identity, redaction, and projections.

The module intentionally uses only the standard library so a failed optional
runtime integration can never turn observability into a deployment dependency.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import sqlite3
import subprocess
import tempfile
import time
import statistics
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

SCHEMA = "pap.event.v2"
_CROCKFORD = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
_ULID = re.compile(r"^[0-9A-HJKMNP-TV-Z]{26}$")
_EVENT_NAME = re.compile(r"^[a-z][a-z0-9_.-]+$")
_SENSITIVE = re.compile(r"(?:token|secret|password|authorization|cookie|api[_-]?key|apikey|credential|private[_-]?key)", re.I)
_SECRET_VALUE = re.compile(r"(?:sk-[A-Za-z0-9_-]{12,}|Bearer\s+[A-Za-z0-9._-]+|-----BEGIN [A-Z ]*PRIVATE KEY-----)", re.I)
_INLINE_SECRET = re.compile(
    r"(?:token|secret|password|authorization|cookie|api[_-]?key|apikey|credential|private[_-]?key)"
    r"\s*(?:=|:)\s*(?:Bearer\s+)?[^\s,;]+",
    re.I,
)
# These names contain sensitive-looking words but designate bounded metadata,
# not a credential value.  Keep profile *identities* queryable while redacting
# every actual credential-bearing field.
_SAFE_USAGE_KEYS = frozenset({"input_tokens", "output_tokens", "cache_read_tokens", "cache_write_tokens", "reasoning_tokens", "estimated_tokens", "credential_profile", "credential-profile"})
_CONTENT_KEYS = frozenset({
    "prompt", "prompt_text", "completion", "completion_text", "message", "message_body",
    "body", "request_body", "response_body", "content", "content_text", "source",
    "source_text", "source_body", "stdout", "stderr",
})
_PRICING_CACHE: tuple[str, int, Mapping[str, Any] | None] | None = None


def now() -> datetime:
    return datetime.now(timezone.utc).astimezone()


def ulid(timestamp: datetime | None = None) -> str:
    """Return a sortable 26-character ULID without a third-party dependency."""
    millis = int((timestamp or now()).timestamp() * 1000)
    value = (millis << 80) | secrets.randbits(80)
    chars = []
    for _ in range(26):
        chars.append(_CROCKFORD[value & 31])
        value >>= 5
    return "".join(reversed(chars))


def trace_id() -> str:
    return secrets.token_hex(16)


def span_id() -> str:
    return secrets.token_hex(8)


def state_dir(value: str | os.PathLike[str] | None = None) -> Path:
    if value:
        return Path(value).expanduser()
    if os.environ.get("PAP_OBSERVABILITY_DIR"):
        return Path(os.environ["PAP_OBSERVABILITY_DIR"]).expanduser()
    base = Path(os.environ.get("XDG_STATE_HOME", "~/.local/state")).expanduser()
    return base / "pap" / "ledger"


def node_id() -> str:
    return os.environ.get("PAP_NODE_ID") or os.uname().nodename


def content_metadata(value: Any) -> dict[str, Any]:
    raw = value.encode("utf-8") if isinstance(value, str) else json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return {"sha256": "sha256:" + hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}


def _estimate_model_cost(event: dict[str, Any]) -> None:
    """Apply an explicitly configured, versioned price table once at ingest.

    The table is optional and deliberately never inferred from a model name.
    Historical events retain the resulting amount and pricing version in their
    immutable payload, so changing the table cannot rewrite old accounting.
    """
    if event.get("event_name") != "pap.model.call":
        return
    attrs = event.get("attributes")
    if not isinstance(attrs, dict) or attrs.get("cost.amount") is not None:
        return
    model = attrs.get("returned_model") or attrs.get("requested_model")
    provider = attrs.get("provider")
    if not model or not provider:
        return
    config_path = os.environ.get("PAPLOG_PRICING_JSON")
    if not config_path:
        return
    try:
        global _PRICING_CACHE
        pricing_path = Path(config_path).expanduser()
        mtime_ns = pricing_path.stat().st_mtime_ns
        if _PRICING_CACHE and _PRICING_CACHE[:2] == (str(pricing_path), mtime_ns):
            table = _PRICING_CACHE[2]
        else:
            loaded = json.loads(pricing_path.read_text(encoding="utf-8"))
            table = loaded if isinstance(loaded, Mapping) else None
            _PRICING_CACHE = (str(pricing_path), mtime_ns, table)
        if not isinstance(table, Mapping):
            return
        version = table.get("version")
        prices = table.get("models", {})
        price = prices.get(f"{provider}/{model}") if isinstance(prices, Mapping) else None
        if not isinstance(price, Mapping) or not version:
            return
        input_tokens = attrs.get("input_tokens") or 0
        output_tokens = attrs.get("output_tokens") or 0
        if not isinstance(input_tokens, (int, float)) or not isinstance(output_tokens, (int, float)):
            return
        input_rate = price.get("input_per_million")
        output_rate = price.get("output_per_million")
        if not isinstance(input_rate, (int, float)) or not isinstance(output_rate, (int, float)):
            return
        attrs["cost.amount"] = (input_tokens * input_rate + output_tokens * output_rate) / 1_000_000
        attrs["cost.currency"] = str(price.get("currency") or "USD")
        attrs["cost.source"] = "estimated"
        attrs["cost.pricing_version"] = str(version)
    except (OSError, TypeError, ValueError, json.JSONDecodeError):
        return


def redact(value: Any, *, mode: str | None = None, key: str = "") -> Any:
    """Recursively remove secrets and default-content fields before persistence."""
    mode = mode or os.environ.get("PAP_LOG_CONTENT", "metadata")
    if _SENSITIVE.search(key) and key.lower() not in _SAFE_USAGE_KEYS:
        return "[REDACTED]"
    if isinstance(value, Mapping):
        return {str(k): redact(v, mode=mode, key=str(k)) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v, mode=mode, key=key) for v in value]
    if isinstance(value, tuple):
        return [redact(v, mode=mode, key=key) for v in value]
    if isinstance(value, str):
        # Errors and environment snapshots are commonly strings such as
        # ``connection failed: api_key=...`` rather than secret-named fields.
        # They must receive the same protection as structured metadata.
        if _SECRET_VALUE.search(value) or _INLINE_SECRET.search(value):
            return "[REDACTED]"
        if mode != "full" and key.lower() in _CONTENT_KEYS:
            return content_metadata(value)
    return value


def git_provenance(cwd: Path | None = None) -> dict[str, Any]:
    cwd = cwd or Path.cwd()
    try:
        def git(*args: str) -> str:
            return subprocess.run(["git", *args], cwd=cwd, text=True, capture_output=True, timeout=2, check=True).stdout.strip()
        return {"repository": git("rev-parse", "--show-toplevel"), "git_commit": git("rev-parse", "HEAD"), "git_branch": git("branch", "--show-current"), "git_dirty": bool(git("status", "--porcelain"))}
    except Exception:
        return {}


class Ledger:
    def __init__(self, directory: str | os.PathLike[str] | None = None):
        self.directory = state_dir(directory)
        self.db_path = self.directory / "events.sqlite3"
        self.spool = self.directory / "spool" / node_id()
        self.jsonl = self.directory / "jsonl"
        self.exports = self.directory / "exports"

    def _connect(self) -> sqlite3.Connection:
        self.directory.mkdir(parents=True, exist_ok=True)
        con = sqlite3.connect(self.db_path, timeout=5)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA journal_mode=WAL")
        con.execute("PRAGMA synchronous=NORMAL")
        con.execute("PRAGMA busy_timeout=5000")
        self._schema(con)
        return con

    @staticmethod
    def _schema(con: sqlite3.Connection) -> None:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS events (
          seq INTEGER PRIMARY KEY AUTOINCREMENT, event_id TEXT NOT NULL UNIQUE,
          timestamp_us INTEGER NOT NULL, observed_timestamp_us INTEGER NOT NULL,
          schema_version INTEGER NOT NULL, event_name TEXT NOT NULL, kind TEXT NOT NULL,
          phase TEXT, severity_number INTEGER NOT NULL, trace_id TEXT, span_id TEXT,
          parent_span_id TEXT, run_id TEXT, operation_id TEXT, action_id TEXT,
          node_id TEXT, repo TEXT, service TEXT, component TEXT, job_id TEXT,
          job_definition_version TEXT, agent_id TEXT, skill_id TEXT,
          skill_definition_version TEXT, actor_type TEXT, actor_id TEXT,
          subject_type TEXT, subject_id TEXT, outcome TEXT, duration_ms REAL,
          error_type TEXT, error_message TEXT, attributes_json TEXT NOT NULL,
          body_json TEXT NOT NULL, privacy_classification TEXT, content_mode TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS artifact_links (source_id TEXT NOT NULL, type TEXT NOT NULL, target_type TEXT NOT NULL, target_id TEXT NOT NULL, event_id TEXT NOT NULL, PRIMARY KEY(source_id,type,target_type,target_id,event_id));
        CREATE TABLE IF NOT EXISTS runs (run_id TEXT PRIMARY KEY, trace_id TEXT, job_id TEXT, agent_id TEXT, skill_id TEXT, started_event_id TEXT, terminal_event_id TEXT, started_at_us INTEGER, completed_at_us INTEGER, outcome TEXT, duration_ms REAL);
        CREATE TABLE IF NOT EXISTS operations (operation_id TEXT PRIMARY KEY, trace_id TEXT, run_id TEXT, event_name TEXT, started_event_id TEXT, terminal_event_id TEXT, started_at_us INTEGER, completed_at_us INTEGER, outcome TEXT, duration_ms REAL);
        CREATE TABLE IF NOT EXISTS actions (action_id TEXT PRIMARY KEY, trace_id TEXT, run_id TEXT, operation_id TEXT, event_name TEXT, started_event_id TEXT, terminal_event_id TEXT, started_at_us INTEGER, completed_at_us INTEGER, outcome TEXT, duration_ms REAL);
        CREATE TABLE IF NOT EXISTS model_usage (event_id TEXT PRIMARY KEY, run_id TEXT, job_id TEXT, agent_id TEXT, skill_id TEXT, provider TEXT, model TEXT, routing_profile TEXT, credential_profile TEXT, workload_class TEXT, input_tokens INTEGER, output_tokens INTEGER, cost_amount REAL, cost_currency TEXT, cost_source TEXT, retry_count INTEGER, fallback_count INTEGER, latency_ms REAL, cache_read_tokens INTEGER, cache_write_tokens INTEGER, reasoning_tokens INTEGER, pricing_version TEXT);
        CREATE TABLE IF NOT EXISTS projections_meta (name TEXT PRIMARY KEY, rebuilt_at TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS events_timestamp ON events(timestamp_us);
        CREATE INDEX IF NOT EXISTS events_trace ON events(trace_id);
        CREATE INDEX IF NOT EXISTS events_run ON events(run_id);
        CREATE INDEX IF NOT EXISTS events_operation ON events(operation_id);
        CREATE INDEX IF NOT EXISTS events_action ON events(action_id);
        CREATE INDEX IF NOT EXISTS events_name ON events(event_name);
        CREATE INDEX IF NOT EXISTS events_job ON events(job_id);
        CREATE INDEX IF NOT EXISTS events_agent ON events(agent_id);
        CREATE INDEX IF NOT EXISTS events_skill ON events(skill_id);
        CREATE INDEX IF NOT EXISTS events_outcome ON events(outcome);
        CREATE INDEX IF NOT EXISTS events_subject ON events(subject_id);
        """)
        existing = {row[1] for row in con.execute("PRAGMA table_info(model_usage)")}
        for name, sql_type in (("cache_read_tokens", "INTEGER"), ("cache_write_tokens", "INTEGER"),
                               ("reasoning_tokens", "INTEGER"), ("pricing_version", "TEXT")):
            if name not in existing:
                con.execute(f"ALTER TABLE model_usage ADD COLUMN {name} {sql_type}")

    def emit(self, record: Mapping[str, Any]) -> dict[str, Any]:
        event = redact(dict(record))
        event["schema"] = SCHEMA
        if not isinstance(event.get("event_name"), str) or not _EVENT_NAME.fullmatch(event["event_name"]):
            event = {"schema": SCHEMA, "event_name": "paplog.invalid_event",
                     "attributes": {"rejected_event_name": content_metadata(str(event.get("event_name")))}}
        if not isinstance(event.get("event_id"), str) or not _ULID.fullmatch(event["event_id"]):
            event["event_id"] = ulid()
        stamp = now(); event.setdefault("timestamp", stamp.isoformat()); event.setdefault("observed_timestamp", now().isoformat())
        event.setdefault("kind", "event"); event.setdefault("phase", None); event.setdefault("severity", "INFO")
        for key, fallback in (("trace", {}), ("execution", {}), ("attributes", {}),
                              ("job", {}), ("agent", {}), ("skill", {}),
                              ("actor", {}), ("subject", {}), ("outcome", {}),
                              ("error", {}), ("links", [])):
            expected = list if key == "links" else Mapping
            if not isinstance(event.get(key), expected):
                event[key] = fallback
        event.setdefault("privacy", {"classification": "private", "content_mode": os.environ.get("PAP_LOG_CONTENT", "metadata")})
        if not isinstance(event.get("privacy"), Mapping):
            event["privacy"] = {"classification": "private", "content_mode": os.environ.get("PAP_LOG_CONTENT", "metadata")}
        _estimate_model_cost(event)
        event["execution"].setdefault("node_id", node_id())
        if isinstance(event.get("runtime"), Mapping):
            event["execution"].setdefault("runtime", dict(event["runtime"]))
        persisted = False
        for attempt in range(4):
            try:
                self._persist(event)
                persisted = True
                break
            except sqlite3.OperationalError as exc:
                # WAL permits concurrent writers, but schema initialization and
                # short writer windows can still report busy/locked. Retry the
                # bounded transient before relying on the fail-open spool.
                if "locked" not in str(exc).lower() and "busy" not in str(exc).lower():
                    break
                time.sleep(0.02 * (attempt + 1))
            except (sqlite3.Error, OSError):
                break
        if not persisted:
            # Observability is strictly fail-open.  A read-only filesystem can
            # prevent even the spool directory from being created; retaining
            # the original execution behavior matters more than raising that
            # secondary diagnostic failure.
            try:
                self._jsonl(event)
            except OSError:
                pass
            try:
                self._spool(event)
            except OSError:
                pass
        return event

    def _persist(self, event: Mapping[str, Any], *, mirror: bool = True) -> None:
        timestamp = datetime.fromisoformat(str(event["timestamp"])).timestamp()
        observed = datetime.fromisoformat(str(event["observed_timestamp"])).timestamp()
        trace = event.get("trace", {}); execution = event.get("execution", {})
        job = event.get("job", {}); agent = event.get("agent", {}); skill = event.get("skill", {})
        actor = event.get("actor", {}); subject = event.get("subject", {}); outcome = event.get("outcome", {})
        err = event.get("error", {}) if isinstance(event.get("error"), Mapping) else {}
        error_message = err.get("message")
        if error_message is not None and not isinstance(error_message, str):
            error_message = json.dumps(error_message, ensure_ascii=False, sort_keys=True)
        severity = {"DEBUG": 5, "INFO": 9, "WARN": 13, "ERROR": 17, "FATAL": 21}.get(event.get("severity"), 9)
        body = json.dumps(event, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        values = (event["event_id"], int(timestamp * 1_000_000), int(observed * 1_000_000), 2, event["event_name"], event["kind"], event.get("phase"), severity, trace.get("trace_id"), trace.get("span_id"), trace.get("parent_span_id"), execution.get("run_id"), execution.get("operation_id"), execution.get("action_id"), execution.get("node_id"), event.get("repository") or event.get("repo"), event.get("service"), event.get("component"), job.get("id"), job.get("definition_version"), agent.get("id"), skill.get("id"), skill.get("definition_version"), actor.get("type"), actor.get("id"), subject.get("type"), subject.get("id"), outcome.get("status"), event.get("duration_ms"), err.get("type"), error_message, json.dumps(event.get("attributes", {}), ensure_ascii=False, sort_keys=True), body, event["privacy"].get("classification"), event["privacy"].get("content_mode", "metadata"))
        with self._connect() as con:
            con.execute("""INSERT OR IGNORE INTO events VALUES (NULL,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", values)
            source = subject.get("id")
            if source:
                for link in event.get("links", []):
                    if isinstance(link, Mapping) and link.get("target_id"):
                        con.execute("INSERT OR IGNORE INTO artifact_links VALUES (?,?,?,?,?)", (source, str(link.get("type", "references")), str(link.get("target_type", "artifact")), str(link["target_id"]), event["event_id"]))
        if mirror:
            self._jsonl(event)

    def _jsonl(self, event: Mapping[str, Any]) -> None:
        self.jsonl.mkdir(parents=True, exist_ok=True)
        date = str(event["timestamp"])[:10]
        with (self.jsonl / f"{date}.jsonl").open("a", encoding="utf-8") as out:
            out.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")

    def _spool(self, event: Mapping[str, Any]) -> None:
        self.spool.mkdir(parents=True, exist_ok=True)
        path = self.spool / f"{os.getpid()}-{event['event_id']}.json"
        path.write_text(json.dumps(event, ensure_ascii=False, sort_keys=True), encoding="utf-8")

    def reconcile(self) -> tuple[int, int]:
        imported = failed = 0
        if not self.spool.exists(): return imported, failed
        quarantine = self.spool / "quarantine"; quarantine.mkdir(exist_ok=True)
        for path in self.spool.glob("*.json"):
            try:
                value = json.loads(path.read_text(encoding="utf-8"))
                if not isinstance(value, Mapping):
                    raise ValueError("spool record is not an object")
                # Spools normally originate from ``emit`` and are already
                # redacted, but they are durable files and may outlive an older
                # policy or be altered. Never let reconciliation bypass the
                # same privacy boundary as a live write.
                record = redact(value)
                record["schema"] = SCHEMA
                if not isinstance(record.get("event_name"), str) or not _EVENT_NAME.fullmatch(record["event_name"]):
                    record["event_name"] = "paplog.invalid_event"
                    record["attributes"] = {"rejected_event_name": content_metadata(str(value.get("event_name")))}
                if not isinstance(record.get("event_id"), str) or not _ULID.fullmatch(record["event_id"]):
                    record["event_id"] = ulid()
                record.setdefault("timestamp", now().isoformat())
                record.setdefault("observed_timestamp", now().isoformat())
                record.setdefault("kind", "event")
                record.setdefault("phase", None)
                record.setdefault("severity", "INFO")
                for key, fallback in (("trace", {}), ("execution", {}), ("attributes", {}),
                                      ("job", {}), ("agent", {}), ("skill", {}),
                                      ("actor", {}), ("subject", {}), ("outcome", {}),
                                      ("error", {}), ("links", [])):
                    expected = list if key == "links" else Mapping
                    if not isinstance(record.get(key), expected):
                        record[key] = fallback
                record.setdefault("privacy", {"classification": "private", "content_mode": "metadata"})
                if not isinstance(record.get("privacy"), Mapping):
                    record["privacy"] = {"classification": "private", "content_mode": "metadata"}
                record["execution"].setdefault("node_id", node_id())
                self._persist(record, mirror=False); path.unlink(); imported += 1
            except Exception:
                path.replace(quarantine / path.name); failed += 1
        return imported, failed

    def query(self, **filters: Any) -> list[dict[str, Any]]:
        clauses: list[str] = []; values: list[Any] = []
        mapping = {"event": "event_name", "kind": "kind", "job": "job_id", "agent": "agent_id", "skill": "skill_id", "run": "run_id", "trace": "trace_id", "outcome": "outcome", "node": "node_id", "subject": "subject_id"}
        for arg, column in mapping.items():
            if filters.get(arg):
                value = str(filters[arg]); clauses.append(f"{column} {'LIKE' if '*' in value else '='} ?"); values.append(value.replace('*', '%'))
        if filters.get("since"):
            clauses.append("timestamp_us >= ?"); values.append(_time_filter(filters["since"]))
        if filters.get("until"):
            clauses.append("timestamp_us <= ?"); values.append(_time_filter(filters["until"]))
        sql = "SELECT body_json FROM events" + (" WHERE " + " AND ".join(clauses) if clauses else "") + " ORDER BY seq"
        with self._connect() as con: return [json.loads(row[0]) for row in con.execute(sql, values)]

    def rebuild_index(self) -> int:
        with self._connect() as con:
            con.execute("DELETE FROM artifact_links")
            con.execute("DELETE FROM runs")
            con.execute("DELETE FROM operations")
            con.execute("DELETE FROM actions")
            con.execute("DELETE FROM model_usage")
            rows = con.execute("SELECT event_id, body_json FROM events").fetchall()
            run_rows: dict[str, dict[str, Any]] = {}
            operation_rows: dict[str, dict[str, Any]] = {}
            action_rows: dict[str, dict[str, Any]] = {}
            for event_id, body in rows:
                event = json.loads(body); subject = event.get("subject", {}); source = subject.get("id")
                if source:
                    for link in event.get("links", []):
                        if isinstance(link, Mapping) and link.get("target_id"):
                            con.execute("INSERT OR IGNORE INTO artifact_links VALUES (?,?,?,?,?)", (source, str(link.get("type", "references")), str(link.get("target_type", "artifact")), str(link["target_id"]), event_id))
                execution = event.get("execution", {}); run_id = execution.get("run_id")
                kind = event.get("kind")
                scope_id = execution.get("action_id") if kind == "action" else execution.get("operation_id") if kind == "operation" else None
                if isinstance(scope_id, str):
                    target = action_rows if kind == "action" else operation_rows
                    if kind == "operation":
                        initial = {"operation_id": scope_id, "trace_id": event.get("trace", {}).get("trace_id"), "run_id": run_id,
                                   "event_name": event.get("event_name"), "started_event_id": None, "terminal_event_id": None,
                                   "started_at_us": None, "completed_at_us": None, "outcome": None, "duration_ms": None}
                    else:
                        initial = {"action_id": scope_id, "trace_id": event.get("trace", {}).get("trace_id"), "run_id": run_id,
                                   "operation_id": execution.get("operation_id"), "event_name": event.get("event_name"),
                                   "started_event_id": None, "terminal_event_id": None, "started_at_us": None,
                                   "completed_at_us": None, "outcome": None, "duration_ms": None}
                    row = target.setdefault(scope_id, initial)
                    if event.get("phase") == "started":
                        row.update(started_event_id=event_id, started_at_us=int(datetime.fromisoformat(event["timestamp"]).timestamp() * 1_000_000))
                    elif event.get("phase") in {"completed", "failed", "abandoned"}:
                        row.update(terminal_event_id=event_id, completed_at_us=int(datetime.fromisoformat(event["timestamp"]).timestamp() * 1_000_000), outcome=(event.get("outcome") or {}).get("status"), duration_ms=event.get("duration_ms"))
                if isinstance(run_id, str):
                    row = run_rows.setdefault(run_id, {"run_id": run_id, "trace_id": event.get("trace", {}).get("trace_id"), "job_id": event.get("job", {}).get("id"), "agent_id": event.get("agent", {}).get("id"), "skill_id": event.get("skill", {}).get("id"), "started_event_id": None, "terminal_event_id": None, "started_at_us": None, "completed_at_us": None, "outcome": None, "duration_ms": None})
                    if event.get("event_name") == "pap.run.started": row.update(started_event_id=event_id, started_at_us=int(datetime.fromisoformat(event["timestamp"]).timestamp() * 1_000_000))
                    if event.get("event_name") in {"pap.run.completed", "pap.run.failed", "pap.operation.abandoned"}: row.update(terminal_event_id=event_id, completed_at_us=int(datetime.fromisoformat(event["timestamp"]).timestamp() * 1_000_000), outcome=event.get("outcome", {}).get("status"), duration_ms=event.get("duration_ms"))
                if event.get("event_name") == "pap.model.call":
                    attrs = event.get("attributes", {})
                    con.execute("""INSERT OR REPLACE INTO model_usage
                        (event_id,run_id,job_id,agent_id,skill_id,provider,model,routing_profile,credential_profile,workload_class,
                         input_tokens,output_tokens,cost_amount,cost_currency,cost_source,retry_count,fallback_count,latency_ms,
                         cache_read_tokens,cache_write_tokens,reasoning_tokens,pricing_version)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (event_id, run_id, event.get("job", {}).get("id"), event.get("agent", {}).get("id"), event.get("skill", {}).get("id"), attrs.get("provider"), attrs.get("returned_model") or attrs.get("requested_model"), attrs.get("routing_profile"), attrs.get("credential_profile"), attrs.get("workload_class"), attrs.get("input_tokens"), attrs.get("output_tokens"), attrs.get("cost.amount"), attrs.get("cost.currency"), attrs.get("cost.source"), attrs.get("retry_count"), attrs.get("fallback_count"), attrs.get("latency_ms") if attrs.get("latency_ms") is not None else event.get("duration_ms"), attrs.get("cache_read_tokens"), attrs.get("cache_write_tokens"), attrs.get("reasoning_tokens"), attrs.get("pricing_version")))
            for row in run_rows.values():
                con.execute("INSERT INTO runs VALUES (?,?,?,?,?,?,?,?,?,?,?)", tuple(row.values()))
            for row in operation_rows.values():
                con.execute("INSERT INTO operations VALUES (?,?,?,?,?,?,?,?,?,?)", tuple(row.values()))
            for row in action_rows.values():
                con.execute("INSERT INTO actions VALUES (?,?,?,?,?,?,?,?,?,?,?)", tuple(row.values()))
            con.execute("INSERT OR REPLACE INTO projections_meta VALUES (?,?)", ("paplog.v1", now().isoformat()))
        return len(rows)

    def lineage(self, identifier: str, *, depth: int = 1) -> list[dict[str, Any]]:
        """Traverse provenance links in both directions with a bounded BFS."""
        if depth < 1:
            return []
        frontier = {identifier}
        seen_nodes = {identifier}
        seen_links: set[tuple[str, str, str, str, str]] = set()
        found: list[dict[str, Any]] = []
        with self._connect() as con:
            for distance in range(1, depth + 1):
                if not frontier:
                    break
                placeholders = ",".join("?" for _ in frontier)
                rows = con.execute(
                    f"SELECT * FROM artifact_links WHERE source_id IN ({placeholders}) OR target_id IN ({placeholders})",
                    [*frontier, *frontier],
                ).fetchall()
                next_frontier: set[str] = set()
                for row in rows:
                    item = dict(row)
                    key = (item["source_id"], item["type"], item["target_type"], item["target_id"], item["event_id"])
                    if key not in seen_links:
                        found.append({**item, "depth": distance} if depth > 1 else item)
                        seen_links.add(key)
                    for node in (item["source_id"], item["target_id"]):
                        if node not in seen_nodes:
                            seen_nodes.add(node)
                            next_frontier.add(node)
                frontier = next_frontier
        return found

    def scheduler_health(self) -> dict[str, Any]:
        """Derive scheduler health entirely from immutable canonical events."""
        events = self.query(event="pap.*")
        due = [event for event in events if event["event_name"] == "pap.schedule.due"]
        dispatched = [event for event in events if event["event_name"] == "pap.schedule.dispatched"]
        started = [event for event in events if event["event_name"] == "pap.run.started"]
        runs = [event for event in events if event["event_name"] in {"pap.run.completed", "pap.run.failed", "pap.operation.abandoned"}]
        lag = [float(event.get("attributes", {}).get("schedule_lag_ms")) for event in due if isinstance(event.get("attributes", {}).get("schedule_lag_ms"), (int, float))]
        queue = [float(event.get("attributes", {}).get("queue_delay_ms")) for event in started if isinstance(event.get("attributes", {}).get("queue_delay_ms"), (int, float))]
        duration = [float(event.get("duration_ms")) for event in runs if isinstance(event.get("duration_ms"), (int, float))]
        by_class: dict[str, list[tuple[float, str]]] = {}
        for event in dispatched:
            attrs = event.get("attributes", {})
            klass = attrs.get("tracking_class")
            job = event.get("job", {}).get("id")
            if not isinstance(klass, str) or not isinstance(job, str):
                continue
            by_class.setdefault(klass, []).append((datetime.fromisoformat(event["timestamp"]).timestamp(), job))
        cadence: dict[str, float | None] = {}
        for klass, entries in by_class.items():
            per_job: dict[str, list[float]] = {}
            for stamp, job in entries: per_job.setdefault(job, []).append(stamp)
            intervals = [later - earlier for points in per_job.values() for earlier, later in zip(sorted(points), sorted(points)[1:])]
            cadence[klass] = statistics.median(intervals) if intervals else None
        inversions = []
        # PAP's configured vocabulary is ordinal: urgent/high must not have a
        # longer observed interval than normal/low. Unknown classes stay visible
        # but are never assigned an invented priority.
        rank = {"urgent": 0, "high": 1, "normal": 2, "low": 3}
        known = [(rank[name], name, value) for name, value in cadence.items() if name in rank and value is not None]
        for priority, name, interval in known:
            for lower_priority, lower_name, lower_interval in known:
                if priority < lower_priority and interval > lower_interval:
                    inversions.append({"higher_class": name, "higher_interval_s": interval, "lower_class": lower_name, "lower_interval_s": lower_interval})
        abandoned = {event.get("execution", {}).get("run_id") or event.get("event_id")
                     for event in runs if event["event_name"] == "pap.operation.abandoned"}
        return {"scheduled_runs": len(due), "dispatched_runs": len(dispatched), "completed_runs": sum(e["event_name"] == "pap.run.completed" for e in runs), "failed_runs": sum(e["event_name"] == "pap.run.failed" for e in runs), "abandoned_runs": len(abandoned), "missed_runs": max(0, len(due) - len(dispatched)), "late_runs": sum(value > 0 for value in lag), "median_schedule_lag_ms": statistics.median(lag) if lag else None, "median_queue_delay_ms": statistics.median(queue) if queue else None, "median_execution_duration_ms": statistics.median(duration) if duration else None, "observed_cadence_s": cadence, "frequency_inversions": inversions}

    def abandon_stale(self, older_than_seconds: int = 3600) -> int:
        cutoff = int((time.time() - older_than_seconds) * 1_000_000)
        with self._connect() as con:
            starts = con.execute("SELECT body_json FROM events WHERE kind='operation' AND phase='started' AND timestamp_us < ?", (cutoff,)).fetchall()
            terminals = {row[0] for row in con.execute("SELECT operation_id FROM events WHERE kind='operation' AND phase IN ('completed','failed','abandoned')")}
        count = 0
        for row in starts:
            event = json.loads(row[0]); operation = event.get("execution", {}).get("operation_id")
            if operation and operation not in terminals:
                self.emit({"event_name": "pap.operation.abandoned", "kind": "operation", "phase": "abandoned", "severity": "WARN", "trace": event.get("trace", {}), "execution": event.get("execution", {}), "outcome": {"status": "abandoned"}, "attributes": {"stale_after_s": older_than_seconds}}); count += 1
        return count


def _time_filter(value: str) -> int:
    if value.endswith("d") and value[:-1].isdigit(): return int((time.time() - int(value[:-1]) * 86400) * 1_000_000)
    if value.endswith("h") and value[:-1].isdigit(): return int((time.time() - int(value[:-1]) * 3600) * 1_000_000)
    return int(datetime.fromisoformat(value).timestamp() * 1_000_000)
