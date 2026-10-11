"""Local, rebuildable Cognitive Retrieval Layer (Phase 1).

This module deliberately indexes evidence projections, never Vault notes.  It
has no network or model dependency and keeps an old COMPLETE generation visible
when a new run fails.
"""
from __future__ import annotations

import argparse
from functools import wraps
import hashlib
import json
import os
import re
import sqlite3
import random
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

from paplog import observe as paplog
from pap.retrieval import (TRANSFORMER_MODEL_ID, cosine, embedding, hard_filter, pair_features, pair_family_key,
                            rank_score, select_stratified, time_bucket as _time_bucket,
                            terms as retrieval_terms, cooldown_active,
                            update_cooldown)

import yaml

SCHEMA_VERSION = "2"
SCANNER_VERSION = "1"
SEGMENTER_VERSION = "markdown-heading-v1"
PROVENANCE_RULES_VERSION = "1"
MAX_RESULT_LIMIT = 20
DEFAULT_EXCERPT = 1200
ABSOLUTE_EXCERPT = 5000
SKIP = {".git", ".obsidian", ".trash", ".index", "_debug_remotely_save"}
HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)
WIKILINK = re.compile(r"(?<!!)\[\[([^\]]+)\]\]")


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().lower()


def parse_markdown(raw: str) -> tuple[dict[str, Any], str, int]:
    """Return YAML, body and the UTF-8-independent character offset of body."""
    if not raw.startswith("---\n"):
        return {}, raw, 0
    end = raw.find("\n---", 4)
    if end < 0:
        return {}, raw, 0
    try:
        meta = yaml.safe_load(raw[4:end]) or {}
    except yaml.YAMLError:
        meta = {}
    return (meta if isinstance(meta, dict) else {}), raw[end + 4:].lstrip("\n"), end + 4


def timestamp(value: Any, source: str) -> dict[str, Any] | None:
    if value is None or str(value).strip() == "":
        return None
    text = str(value)
    precision = "datetime" if "T" in text or ":" in text else ("month" if len(text) == 7 else "date")
    return {"value": text, "precision": precision, "source": source}


def classify(path: str, meta: dict[str, Any], text: str) -> dict[str, Any]:
    """Conservative document-level defaults; segment adapters may refine later."""
    p = path.replace("\\", "/")
    typ = str(meta.get("type") or "")
    if "/原文素材/" in p or typ == "source-material":
        return dict(source_type="source_material", voice="external", origin_type="source_material", assertion_kind="claim", retrieval_only=0, requires_source_verification=1)
    if p.startswith("Clippings/"):
        return dict(source_type="clipping", voice="external", origin_type="saved_external", assertion_kind="claim", retrieval_only=0, requires_source_verification=1)
    if p.startswith("印象笔记/"):
        return dict(source_type="evernote", voice="unknown", origin_type="saved_external", assertion_kind="unknown", retrieval_only=0, requires_source_verification=1)
    if p.startswith("2Area/WeRead Notes/"):
        return dict(source_type="weread", voice="external", origin_type="plugin_highlight", assertion_kind="highlight", retrieval_only=0, requires_source_verification=1)
    if p.startswith("2Area/ZoteroNotes/"):
        return dict(source_type="zotero", voice="unknown", origin_type="plugin_highlight", assertion_kind="unknown", retrieval_only=0, requires_source_verification=1)
    if p.startswith("2Area/41 新闻及事件/") and meta.get("thread_id"):
        return dict(source_type="world_historian_thread", voice="system", origin_type="historian_claim", assertion_kind="summary", retrieval_only=0, requires_source_verification=1)
    if p.startswith("Dairies/"):
        return dict(source_type="diary", voice="self", origin_type="authored", assertion_kind="observation", retrieval_only=0, requires_source_verification=0)
    if typ == "moc":
        return dict(source_type="moc", voice="self", origin_type="authored", assertion_kind="navigation", retrieval_only=0, requires_source_verification=0)
    if p.endswith(("README.md", ".py", ".c", ".cc", ".cpp")):
        return dict(source_type="readme", voice="self", origin_type="authored", assertion_kind="code" if p.endswith(".py") else "summary", retrieval_only=0, requires_source_verification=0)
    return dict(source_type=typ or "markdown", voice="self" if p.startswith(("1Project/", "2Area/", "3Resources/", "4Archive/")) else "unknown", origin_type="authored", assertion_kind="interpretation", retrieval_only=0, requires_source_verification=0)


def permissions(c: dict[str, Any]) -> dict[str, int]:
    self_authored = c["voice"] == "self" and c["origin_type"] == "authored"
    external = c["voice"] == "external" or c["requires_source_verification"]
    return {"supports_user_belief": int(self_authored), "supports_user_decision": int(self_authored), "supports_user_question": int(self_authored), "supports_user_exposure": int(c["origin_type"] in {"saved_external", "plugin_highlight", "source_material"}), "supports_external_claim": int(external), "retrieval_only": int(c["retrieval_only"]), "requires_source_verification": int(c["requires_source_verification"])}


@dataclass
class Unit:
    heading: str
    start: int
    end: int
    text: str
    ordinal: int
    overrides: dict[str, Any] | None = None


def segments(body: str, base: int, max_chars: int = 6000) -> Iterable[Unit]:
    """Heading sections first; only split long sections at paragraph boundaries."""
    marks = [(m.start(), len(m.group(1)), m.group(2).strip()) for m in HEADING.finditer(body)]
    if not marks:
        marks = [(0, 0, "")]
    for number, (start, depth, title) in enumerate(marks):
        end = marks[number + 1][0] if number + 1 < len(marks) else len(body)
        section = body[start:end].strip()
        if not section:
            continue
        pieces = [section]
        if len(section) > max_chars:
            pieces, current = [], ""
            for block in re.split(r"(\n\s*\n)", section):
                if len(current) + len(block) > max_chars and current.strip():
                    pieces.append(current.strip()); current = ""
                current += block
            if current.strip(): pieces.append(current.strip())
        cursor = start
        for piece_no, piece in enumerate(pieces):
            found = body.find(piece, cursor, end)
            found = cursor if found < 0 else found
            yield Unit(title, base + found, base + found + len(piece), piece, number * 1000 + piece_no)
            cursor = found + len(piece)


def typed_unit(path: str, meta: dict[str, Any], unit: Unit, default: dict[str, Any]) -> dict[str, Any]:
    """Phase-2 conservative adapters. They refine evidence, never source text."""
    value = dict(default); heading = unit.heading.lower(); text = unit.text
    if path.startswith("Dairies/"):
        if any(x in unit.heading for x in ("对影成", "反思", "应如是", "观自在")):
            value.update(assertion_kind="interpretation", already_synthesized=1 if "对影成" in unit.heading else 0)
        elif any(x in unit.heading for x in ("大事记", "事实", "流程", "Notes", "记录")):
            value.update(assertion_kind="observation")
        elif any(x in unit.heading for x in ("决定", "决策", "计划", "待办", "问题")):
            value.update(assertion_kind="question" if "问题" in unit.heading else "decision")
    elif path.startswith("2Area/WeRead Notes/"):
        if any(x in unit.heading for x in ("评论", "笔记")):
            value.update(voice="self", origin_type="plugin_comment", assertion_kind="interpretation", requires_source_verification=0)
        else:
            value.update(voice="external", origin_type="plugin_highlight", assertion_kind="highlight", requires_source_verification=1)
    elif path.startswith("2Area/ZoteroNotes/"):
        if "评论" in unit.heading or "note" in unit.heading:
            value.update(voice="self", origin_type="plugin_comment", assertion_kind="interpretation", requires_source_verification=0)
        elif text.lstrip().startswith(">"):
            value.update(voice="external", origin_type="quoted_external", assertion_kind="claim", requires_source_verification=1)
    elif path.startswith("2Area/41 新闻及事件/") and meta.get("thread_id"):
        if "开放问题" in unit.heading or "open question" in heading:
            value.update(assertion_kind="question", origin_type="historian_claim")
        elif "事件" in unit.heading or "时间线" in unit.heading:
            value.update(assertion_kind="claim", origin_type="historian_event")
        elif "主张" in unit.heading or "claim" in heading:
            value.update(assertion_kind="claim", origin_type="historian_claim")
    elif path.startswith("印象笔记/"):
        if "ocr" in heading or "ocr" in text[:120].lower():
            value.update(voice="unknown", origin_type="ocr", assertion_kind="unknown", retrieval_only=1, requires_source_verification=1)
    if value.get("already_synthesized") is None:
        value["already_synthesized"] = 0
    return value


def _terms(text: str) -> set[str]:
    """Cheap multilingual features for deterministic candidate construction."""
    latin = re.findall(r"[a-zA-Z][a-zA-Z0-9_+-]{2,}", text.lower())
    chinese = re.findall(r"[\u4e00-\u9fff]{2,}", text)
    grams = [s[i:i + 2] for s in chinese for i in range(len(s) - 1)]
    return set(latin + grams)


def _run_baseline(agent: str) -> dict[str, Any]:
    """Best-effort aggregate from PAP's canonical audit; no production rerun."""
    path = Path(os.environ.get("PAP_RUN_LOG", "var/state/runs.jsonl"))
    if not path.is_absolute():
        # Runtime adapters run with an arbitrary cwd; the canonical log is
        # repo-relative and PAP_ROOT is exported to every child by pap.run.
        path = Path(os.environ.get("PAP_ROOT", ".")) / path
    if not path.is_file():
        return {"state":"unavailable", "reason":"PAP run audit is absent"}
    rows=[]
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            row=json.loads(line)
            if row.get("event")=="run.completed" and row.get("agent_id", row.get("agent"))==agent: rows.append(row)
        except json.JSONDecodeError: continue
    rows=rows[-20:]
    fields=("input_tokens","output_tokens","cost")
    return {"state":"available","sample_runs":len(rows),"totals":{k:sum(float(r[k]) for r in rows if isinstance(r.get(k),(int,float))) for k in fields},"observed":{k:sum(r.get(k) is not None for r in rows) for k in fields},"missing":{"cached_input_tokens":True,"tool_result_bytes":True,"model_call_count":True}}


DDL = """
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS index_generations (generation_id INTEGER PRIMARY KEY, started_at TEXT NOT NULL, completed_at TEXT, status TEXT NOT NULL, scanner_version TEXT NOT NULL, schema_version TEXT NOT NULL, errors_json TEXT NOT NULL DEFAULT '[]', counts_json TEXT NOT NULL DEFAULT '{}');
CREATE TABLE IF NOT EXISTS documents (document_id TEXT PRIMARY KEY, current_path TEXT UNIQUE NOT NULL, source_type TEXT, intrinsic_id TEXT, content_hash TEXT NOT NULL, normalized_hash TEXT NOT NULL, current_revision INTEGER NOT NULL, deleted INTEGER NOT NULL DEFAULT 0, metadata_json TEXT NOT NULL, timestamps_json TEXT NOT NULL, file_mtime REAL, generation_id INTEGER NOT NULL);
CREATE UNIQUE INDEX IF NOT EXISTS documents_intrinsic_id ON documents(intrinsic_id) WHERE intrinsic_id IS NOT NULL;
CREATE TABLE IF NOT EXISTS document_revisions (document_id TEXT NOT NULL, revision INTEGER NOT NULL, content_hash TEXT NOT NULL, normalized_hash TEXT NOT NULL, indexed_at TEXT NOT NULL, generation_id INTEGER NOT NULL, PRIMARY KEY(document_id, revision));
CREATE TABLE IF NOT EXISTS evidence_units (evidence_id TEXT PRIMARY KEY, evidence_family_id TEXT NOT NULL, evidence_revision INTEGER NOT NULL, document_id TEXT NOT NULL, source_path TEXT NOT NULL, source_type TEXT NOT NULL, voice TEXT NOT NULL, origin_type TEXT NOT NULL, assertion_kind TEXT NOT NULL, authority_class TEXT NOT NULL, heading_path TEXT NOT NULL, span_start INTEGER NOT NULL, span_end INTEGER NOT NULL, block_anchor TEXT, text TEXT NOT NULL, content_hash TEXT NOT NULL, normalized_hash TEXT NOT NULL, timestamps_json TEXT NOT NULL, maturity TEXT, sensitivity TEXT NOT NULL, confidence REAL, is_derived INTEGER NOT NULL, already_synthesized INTEGER NOT NULL, retrieval_only INTEGER NOT NULL, requires_source_verification INTEGER NOT NULL, field_provenance_json TEXT NOT NULL, segmenter_version TEXT NOT NULL, extractor_version TEXT NOT NULL, schema_version TEXT NOT NULL, generation_id INTEGER NOT NULL, active INTEGER NOT NULL DEFAULT 1);
CREATE INDEX IF NOT EXISTS evidence_document_active ON evidence_units(document_id, active);
CREATE VIRTUAL TABLE IF NOT EXISTS evidence_fts USING fts5(evidence_id UNINDEXED, text, heading, source_path, tokenize='unicode61');
CREATE TABLE IF NOT EXISTS derivations (derived_evidence_id TEXT NOT NULL, source_evidence_id TEXT NOT NULL, relation TEXT NOT NULL, generation_id INTEGER NOT NULL, PRIMARY KEY(derived_evidence_id, source_evidence_id, relation));
CREATE TABLE IF NOT EXISTS links (left_evidence_id TEXT NOT NULL, right_ref TEXT NOT NULL, relation TEXT NOT NULL, generation_id INTEGER NOT NULL, PRIMARY KEY(left_evidence_id, right_ref, relation));
CREATE TABLE IF NOT EXISTS retrieval_runs (retrieval_run_id TEXT PRIMARY KEY, index_generation INTEGER NOT NULL, metadata_json TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS delivered_connections (pair_key TEXT PRIMARY KEY, external_ref TEXT, canonical_ref TEXT, observed_at TEXT NOT NULL, metadata_json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS watch_hypotheses (watch_hypothesis_id TEXT PRIMARY KEY, status TEXT NOT NULL, prior_evidence_id TEXT NOT NULL, prior_kind TEXT NOT NULL, metadata_json TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS evidence_family_state (family_id TEXT PRIMARY KEY, last_explored_at TEXT, explore_count INTEGER NOT NULL DEFAULT 0, last_llm_seen_at TEXT, llm_seen_count INTEGER NOT NULL DEFAULT 0, accepted_count INTEGER NOT NULL DEFAULT 0, delivered_count INTEGER NOT NULL DEFAULT 0, updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS cooldown_state (scope_kind TEXT NOT NULL, scope_key TEXT NOT NULL, reason_code TEXT NOT NULL, reject_count INTEGER NOT NULL DEFAULT 0, cooldown_until TEXT, penalty REAL NOT NULL DEFAULT 0, last_reject_at TEXT, last_positive_at TEXT, PRIMARY KEY(scope_kind, scope_key, reason_code));
CREATE TABLE IF NOT EXISTS candidate_rejections (event_id TEXT PRIMARY KEY, run_id TEXT NOT NULL, agent TEXT NOT NULL, candidate_id TEXT NOT NULL, evidence_ids_json TEXT NOT NULL, family_ids_json TEXT NOT NULL, recall_channels_json TEXT NOT NULL, reason_code TEXT NOT NULL, pair_family_key TEXT, at TEXT NOT NULL, anchor_refs_json TEXT NOT NULL DEFAULT '[]');
CREATE TABLE IF NOT EXISTS evidence_embeddings (evidence_id TEXT NOT NULL, model_id TEXT NOT NULL, text_hash TEXT NOT NULL, dim INTEGER NOT NULL, vector_json TEXT NOT NULL, created_at TEXT NOT NULL, PRIMARY KEY(evidence_id, model_id, text_hash));
"""


class Index:
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        # Concurrent writers (two pulse jobs, a manual index, a model-invoked
        # evidence read) are expected; wait out short writer windows.
        self.db.execute("PRAGMA busy_timeout = 10000")
        self.db.executescript(DDL)
        try:
            self.db.execute("ALTER TABLE candidate_rejections ADD COLUMN anchor_refs_json TEXT NOT NULL DEFAULT '[]'")
        except sqlite3.OperationalError:
            pass

    def close(self) -> None: self.db.close()

    @staticmethod
    def retrieval_flags() -> dict[str, bool]:
        def flag(name: str, default: bool = True) -> bool:
            value = os.environ.get(name)
            return default if value is None else value.lower() not in {"0", "false", "no", "off"}
        return {"candidate_retrieval_v06_enabled": flag("PAP_CANDIDATE_RETRIEVAL_V06_ENABLED"), "candidate_retrieval_v06_shadow": flag("PAP_CANDIDATE_RETRIEVAL_V06_SHADOW", False), "candidate_retrieval_embeddings_enabled": flag("PAP_CANDIDATE_RETRIEVAL_EMBEDDINGS_ENABLED"), "candidate_retrieval_hard_filter_enabled": flag("PAP_CANDIDATE_RETRIEVAL_HARD_FILTER_ENABLED"), "candidate_retrieval_stratified_sampling_enabled": flag("PAP_CANDIDATE_RETRIEVAL_STRATIFIED_SAMPLING_ENABLED"), "candidate_retrieval_cooldown_enabled": flag("PAP_CANDIDATE_RETRIEVAL_COOLDOWN_ENABLED")}
    def complete_generation(self) -> int | None:
        row = self.db.execute("SELECT generation_id FROM index_generations WHERE status='COMPLETE' ORDER BY generation_id DESC LIMIT 1").fetchone()
        return row[0] if row else None

    @staticmethod
    def _observed_read(function):
        @wraps(function)
        def wrapped(self, *args, **kwargs):
            if not (os.environ.get("PAP_RUN_ID") or os.environ.get("PAP_OBSERVABILITY_DIR")):
                return function(self, *args, **kwargs)
            with paplog.database(str(self.path), effect="read"):
                return function(self, *args, **kwargs)
        return wrapped

    @_observed_read.__func__
    def status(self) -> dict[str, Any]:
        generation = self.complete_generation()
        return {"index_path": str(self.path), "generation": generation, "documents": self.db.execute("SELECT count(*) FROM documents WHERE deleted=0").fetchone()[0], "evidence_units": self.db.execute("SELECT count(*) FROM evidence_units WHERE active=1").fetchone()[0], "fts": self.db.execute("SELECT count(*) FROM evidence_fts").fetchone()[0], "failed_generations": self.db.execute("SELECT count(*) FROM index_generations WHERE status='FAILED'").fetchone()[0], "versions": {"schema": SCHEMA_VERSION, "scanner": SCANNER_VERSION, "segmenter": SEGMENTER_VERSION, "provenance_rules": PROVENANCE_RULES_VERSION}}

    def _document_id(self, vault: Path, path: str, intrinsic: str | None, content_hash: str) -> str:
        row = self.db.execute("SELECT document_id FROM documents WHERE current_path=?", (path,)).fetchone()
        if row:
            return row["document_id"]
        if intrinsic:
            row = self.db.execute("SELECT document_id FROM documents WHERE intrinsic_id=?", (intrinsic,)).fetchone()
            if row: return row[0]
        row = self.db.execute("SELECT document_id,current_path FROM documents WHERE content_hash=? AND deleted=0", (content_hash,)).fetchone()
        # A missing former path + exact bytes is a safe rename.  Two extant files
        # with equal text are duplicates, not the same logical document.
        if row and not (vault / row["current_path"]).exists():
            return row["document_id"]
        return "doc_" + digest(path + content_hash)[:24]

    @staticmethod
    def _observed_build(function):
        """Add explicit PAP telemetry without changing standalone cognition."""
        @wraps(function)
        def wrapped(self, *args, **kwargs):
            if not (os.environ.get("PAP_RUN_ID") or os.environ.get("PAP_OBSERVABILITY_DIR")):
                return function(self, *args, **kwargs)
            with paplog.operation(
                "pap.cognition.index",
                runtime={"backend": "pap", "mode": "deterministic"},
                attributes={"index_path": str(self.path)},
            ):
                with paplog.database(str(self.path), effect="write"):
                    return function(self, *args, **kwargs)
        return wrapped

    @_observed_build.__func__
    def build(self, vault: Path, *, dry_run: bool = False) -> dict[str, Any]:
        if not vault.is_dir():
            raise FileNotFoundError(f"Vault directory unavailable: {vault}")
        files = sorted(p for p in vault.rglob("*.md") if not any(x in SKIP for x in p.relative_to(vault).parts))
        if dry_run: return {"candidates": len(files), "dry_run": True}
        seen: set[str] = set(); skipped = failed = 0
        embeddings_enabled = self.retrieval_flags()["candidate_retrieval_embeddings_enabled"]
        try:
            # BEGIN IMMEDIATE lives inside the try on purpose: lock contention
            # with a concurrent build must be recorded as a FAILED generation
            # and surface as an error, not escape unrecorded.
            self.db.execute("BEGIN IMMEDIATE")
            generation = self.db.execute("INSERT INTO index_generations(started_at,status,scanner_version,schema_version) VALUES(?,?,?,?)", (now(), "BUILDING", SCANNER_VERSION, SCHEMA_VERSION)).lastrowid
            for file in files:
                before = file.stat()
                if os.environ.get("PAP_RUN_ID") or os.environ.get("PAP_OBSERVABILITY_DIR"):
                    with paplog.filesystem(file, effect="read"):
                        raw = file.read_text("utf-8", errors="replace")
                else:
                    raw = file.read_text("utf-8", errors="replace")
                after = file.stat()
                path = file.relative_to(vault).as_posix()
                if (before.st_mtime_ns, before.st_size) != (after.st_mtime_ns, after.st_size):
                    failed += 1
                    # A file written during the scan stays on its prior good
                    # revision and is retried next build (INDEX_LIFECYCLE
                    # contract); it must not be tombstoned by the sweep below.
                    prior = self.db.execute("SELECT document_id FROM documents WHERE current_path=? AND deleted=0", (path,)).fetchone()
                    if prior: seen.add(prior["document_id"])
                    continue
                content_hash = digest(raw); normalized_hash = digest(normalize(raw))
                meta, body, base = parse_markdown(raw)
                # Namespace source IDs by their field; a Thread ID is not an ID
                # for every source-material file attached to that Thread.
                intrinsic = next((f"{k}:{meta[k]}" for k in ("id", "source_id", "yinxiang_guid", "zotero-key", "event_id", "thread_id") if meta.get(k)), None)
                doc_id = self._document_id(vault, path, intrinsic, content_hash); seen.add(doc_id)
                old = self.db.execute("SELECT content_hash,current_revision FROM documents WHERE document_id=?", (doc_id,)).fetchone()
                if old and old["content_hash"] == content_hash:
                    self.db.execute("UPDATE documents SET current_path=?,deleted=0,file_mtime=?,generation_id=? WHERE document_id=?", (path, after.st_mtime, generation, doc_id)); skipped += 1; continue
                rev = (old["current_revision"] + 1) if old else 1; c = classify(path, meta, body); ts = {k: timestamp(meta.get(k), "frontmatter") for k in ("occurred_at","recorded_at","created","published_at","observed_at","updated_at")}; ts["indexed_at"] = timestamp(now(), "system"); ts["file_mtime"] = timestamp(datetime.fromtimestamp(after.st_mtime, timezone.utc).isoformat(), "filesystem")
                self.db.execute("INSERT INTO documents(document_id,current_path,source_type,intrinsic_id,content_hash,normalized_hash,current_revision,deleted,metadata_json,timestamps_json,file_mtime,generation_id) VALUES(?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(document_id) DO UPDATE SET current_path=excluded.current_path,source_type=excluded.source_type,intrinsic_id=excluded.intrinsic_id,content_hash=excluded.content_hash,normalized_hash=excluded.normalized_hash,current_revision=excluded.current_revision,deleted=0,metadata_json=excluded.metadata_json,timestamps_json=excluded.timestamps_json,file_mtime=excluded.file_mtime,generation_id=excluded.generation_id", (doc_id,path,c["source_type"],intrinsic,content_hash,normalized_hash,rev,0,json.dumps(meta,default=str,ensure_ascii=False),json.dumps(ts,ensure_ascii=False),after.st_mtime,generation))
                self.db.execute("INSERT OR REPLACE INTO document_revisions VALUES(?,?,?,?,?,?)", (doc_id,rev,content_hash,normalized_hash,now(),generation))
                old_ids = [r[0] for r in self.db.execute("SELECT evidence_id FROM evidence_units WHERE document_id=? AND active=1", (doc_id,))]; self.db.execute("UPDATE evidence_units SET active=0 WHERE document_id=?", (doc_id,));
                if old_ids: self.db.executemany("DELETE FROM evidence_fts WHERE evidence_id=?", [(x,) for x in old_ids])
                for unit in segments(body, base):
                    if not normalize(unit.text): continue
                    unit_c = typed_unit(path, meta, unit, c)
                    anchor = f"h{unit.ordinal}"; family = "evf_" + digest(doc_id + anchor)[:24]; evidence_id = family + f":r{rev}"; synth = int(unit_c.pop("already_synthesized", 0) or ("对影成" in unit.heading)); field = {"classification":"source_adapter","heading_path":"markdown_structure","spans":"markdown_structure","timestamps":"frontmatter","permissions":"deterministic_rule"}
                    derived = int(unit_c["source_type"] == "world_historian_thread" or any(x in unit.heading.lower() for x in ("weekly", "monthly", "周报", "月报", "总结")))
                    self.db.execute("INSERT INTO evidence_units VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (evidence_id,family,rev,doc_id,path,unit_c["source_type"],unit_c["voice"],unit_c["origin_type"],unit_c["assertion_kind"],"conservative",unit.heading,unit.start,unit.end,anchor,unit.text,digest(unit.text),digest(normalize(unit.text)),json.dumps(ts,ensure_ascii=False),str(meta.get("status") or ""),str(meta.get("sensitivity") or "S1_personal"),None,derived,synth,unit_c["retrieval_only"],unit_c["requires_source_verification"],json.dumps({"fields":field,"permissions":permissions(unit_c)},ensure_ascii=False),SEGMENTER_VERSION,"typed-rules-v1",SCHEMA_VERSION,generation,1))
                    if embeddings_enabled:
                        # PAP_CANDIDATE_RETRIEVAL_EMBEDDINGS_ENABLED=0 must also
                        # disable build-time embedding, not only the pair lookup.
                        embedding_hash = digest(normalize(unit.text))
                        embedding_model, embedding_vector = embedding(unit.text)
                        self.db.execute("INSERT OR IGNORE INTO evidence_embeddings VALUES(?,?,?,?,?,?)", (evidence_id, embedding_model, embedding_hash, len(embedding_vector), json.dumps(embedding_vector, separators=(",", ":")), now()))
                    self.db.execute("INSERT INTO evidence_fts(evidence_id,text,heading,source_path) VALUES(?,?,?,?)", (evidence_id,unit.text,unit.heading,path))
                    for link in WIKILINK.findall(unit.text):
                        target = link.split("|",1)[0].split("#",1)[0]
                        self.db.execute("INSERT OR IGNORE INTO links VALUES(?,?,?,?)", (evidence_id,target,"wikilink",generation))
                        if derived: self.db.execute("INSERT OR IGNORE INTO derivations VALUES(?,?,?,?)", (evidence_id,target,"references_source",generation))
            if seen:
                self.db.execute("UPDATE documents SET deleted=1 WHERE deleted=0 AND document_id NOT IN (SELECT value FROM json_each(?))", (json.dumps(sorted(seen)),))
            else:
                self.db.execute("UPDATE documents SET deleted=1 WHERE deleted=0")
            self.db.execute("DELETE FROM evidence_fts WHERE evidence_id IN (SELECT evidence_id FROM evidence_units WHERE document_id IN (SELECT document_id FROM documents WHERE deleted=1))")
            self.db.execute("UPDATE evidence_units SET active=0 WHERE document_id IN (SELECT document_id FROM documents WHERE deleted=1)")
            self._ensure_embeddings()
            counts = {"candidates":len(files),"skipped":skipped,"failed":failed,"documents":len(seen),"evidence":self.db.execute("SELECT count(*) FROM evidence_units WHERE active=1").fetchone()[0]}
            self.db.execute("UPDATE index_generations SET status='COMPLETE',completed_at=?,counts_json=? WHERE generation_id=?", (now(),json.dumps(counts),generation)); self.db.commit(); return {"generation":generation,**counts}
        except Exception as exc:
            try:
                self.db.rollback()
            except sqlite3.Error:
                pass
            try:
                self.db.execute("INSERT INTO index_generations(started_at,completed_at,status,scanner_version,schema_version,errors_json) VALUES(?,?,?,?,?,?)", (now(),now(),"FAILED",SCANNER_VERSION,SCHEMA_VERSION,json.dumps([str(exc)[:1000]]))); self.db.commit()
            except sqlite3.Error:
                pass  # under lock contention even the failure record is best effort
            raise

    @_observed_read.__func__
    def get(self, evidence_id: str, excerpt: int = DEFAULT_EXCERPT) -> dict[str, Any] | None:
        excerpt = max(1, min(excerpt, ABSOLUTE_EXCERPT)); row = self.db.execute("SELECT * FROM evidence_units WHERE evidence_id=? AND active=1", (evidence_id,)).fetchone()
        if not row: return None
        data=dict(row); data["text"] = data.pop("text")[:excerpt]; data["field_provenance"] = json.loads(data.pop("field_provenance_json")); data["timestamps"] = json.loads(data.pop("timestamps_json")); return data

    @_observed_read.__func__
    def search(self, query: str, *, limit: int = 10, source_type: str | None = None, voice: str | None = None) -> list[dict[str, Any]]:
        limit=max(1,min(limit,MAX_RESULT_LIMIT)); filters=["u.active=1", "evidence_fts MATCH ?"]; values=[query]
        if source_type: filters.append("u.source_type=?"); values.append(source_type)
        if voice: filters.append("u.voice=?"); values.append(voice)
        values.append(limit)
        rows=self.db.execute("SELECT u.evidence_id,u.source_path,u.heading_path,u.voice,u.origin_type,u.assertion_kind,u.requires_source_verification,highlight(evidence_fts,1,'[',']') AS excerpt,bm25(evidence_fts) AS score FROM evidence_fts JOIN evidence_units u ON u.evidence_id=evidence_fts.evidence_id WHERE " + " AND ".join(filters) + " ORDER BY score LIMIT ?", values).fetchall()
        return [dict(r) for r in rows]

    def _candidate_rows(self, voice: str, limit: int | None = None) -> list[sqlite3.Row]:
        """Return the complete eligible corpus; limiting happens after strata."""
        rows = self.db.execute("SELECT evidence_id,evidence_family_id,source_path,source_type,voice,origin_type,assertion_kind,heading_path,text,content_hash,normalized_hash,timestamps_json,is_derived,already_synthesized,retrieval_only,requires_source_verification FROM evidence_units WHERE active=1 AND voice=? AND retrieval_only=0", (voice,)).fetchall()
        return rows if limit is None else rows[:limit]

    def _family_state(self) -> dict[str, dict[str, Any]]:
        return {r["family_id"]: dict(r) for r in self.db.execute("SELECT * FROM evidence_family_state")}

    def _embedding(self, evidence_id: str) -> list[float] | None:
        if not self.retrieval_flags()["candidate_retrieval_embeddings_enabled"]:
            return None
        row = self.db.execute("SELECT vector_json FROM evidence_embeddings WHERE evidence_id=? ORDER BY created_at DESC LIMIT 1", (evidence_id,)).fetchone()
        return json.loads(row[0]) if row else None

    def _ensure_embeddings(self) -> None:
        """Incrementally populate the configured local transformer cache."""
        if not self.retrieval_flags()["candidate_retrieval_embeddings_enabled"]:
            return
        rows = self.db.execute("SELECT evidence_id,text,normalized_hash FROM evidence_units WHERE active=1 AND retrieval_only=0").fetchall()
        for row in rows:
            if self.db.execute("SELECT 1 FROM evidence_embeddings WHERE evidence_id=? AND model_id=? AND text_hash=? LIMIT 1", (row["evidence_id"], TRANSFORMER_MODEL_ID, row["normalized_hash"])).fetchone():
                continue
            model_id, vector = embedding(row["text"])
            self.db.execute("INSERT OR IGNORE INTO evidence_embeddings VALUES(?,?,?,?,?,?)", (row["evidence_id"], model_id, row["normalized_hash"], len(vector), json.dumps(vector, separators=(",", ":")), now()))

    def _embedding_model(self) -> str:
        row = self.db.execute("SELECT model_id, count(*) AS n FROM evidence_embeddings GROUP BY model_id ORDER BY n DESC LIMIT 1").fetchone()
        return row["model_id"] if row else "unavailable"

    def _mark_explored(self, rows: Iterable[sqlite3.Row], at: str) -> None:
        for row in rows:
            self.db.execute("INSERT INTO evidence_family_state(family_id,last_explored_at,explore_count,updated_at) VALUES(?,?,1,?) ON CONFLICT(family_id) DO UPDATE SET last_explored_at=excluded.last_explored_at,explore_count=evidence_family_state.explore_count+1,updated_at=excluded.updated_at", (row["evidence_family_id"], at, at))

    def record_rejection(self, *, run_id: str, agent: str, candidate_id: str,
                         evidence_ids: Iterable[str], family_ids: Iterable[str],
                         recall_channels: Iterable[str], reason_code: str,
                         anchor_refs: Iterable[str] = (), _persist_event: bool = True) -> None:
        """Append a replayable rejection and update only derived cooldown state."""
        at = now(); evidence_ids, family_ids = list(evidence_ids), list(family_ids)
        recall_channels, anchor_refs = list(recall_channels), list(anchor_refs)
        channel = recall_channels[0] if recall_channels else ""
        pair_key = pair_family_key(*(list(family_ids)[:2] or [candidate_id, candidate_id]), channel)
        event_id = "rej_" + digest("|".join((run_id, candidate_id, reason_code, at)))[:24]
        if _persist_event:
            self.db.execute("INSERT INTO candidate_rejections(event_id,run_id,agent,candidate_id,evidence_ids_json,family_ids_json,recall_channels_json,reason_code,pair_family_key,at,anchor_refs_json) VALUES(?,?,?,?,?,?,?,?,?,?,?)", (event_id, run_id, agent, candidate_id, json.dumps(evidence_ids), json.dumps(family_ids), json.dumps(recall_channels), reason_code, pair_key, at, json.dumps(anchor_refs)))
        if reason_code in {"LEXICAL_COLLISION", "WEAK_CONNECTION", "OBVIOUS_CONNECTION", "MODEL_REJECT_OTHER"}:
            for anchor in anchor_refs:
                row = self.db.execute("SELECT reject_count FROM cooldown_state WHERE scope_kind='anchor' AND scope_key=? AND reason_code=?", (anchor, reason_code)).fetchone()
                count = (row[0] if row else 0) + 1
                qualified = True
                if reason_code == "LEXICAL_COLLISION":
                    cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
                    recent = self.db.execute("SELECT pair_family_key,anchor_refs_json FROM candidate_rejections WHERE reason_code='LEXICAL_COLLISION' AND at>=?", (cutoff,)).fetchall()
                    qualified_pairs = {item["pair_family_key"] for item in recent if anchor in json.loads(item["anchor_refs_json"] or "[]")}
                    qualified = len(qualified_pairs) >= 3
                policy = update_cooldown(count, scope_kind="anchor") if reason_code == "LEXICAL_COLLISION" and qualified else {"reject_count": count, "cooldown_until": None, "penalty": min(1.0, count / 3)}
                self.db.execute("INSERT INTO cooldown_state(scope_kind,scope_key,reason_code,reject_count,cooldown_until,penalty,last_reject_at) VALUES('anchor',?,?,?,?,?,?) ON CONFLICT(scope_kind,scope_key,reason_code) DO UPDATE SET reject_count=excluded.reject_count,cooldown_until=excluded.cooldown_until,penalty=excluded.penalty,last_reject_at=excluded.last_reject_at", (anchor, reason_code, policy["reject_count"], policy["cooldown_until"], policy["penalty"], at))
        if reason_code in {"LEXICAL_COLLISION", "OBVIOUS_CONNECTION"}:
            row = self.db.execute("SELECT reject_count FROM cooldown_state WHERE scope_kind='pair_family' AND scope_key=? AND reason_code=?", (pair_key, reason_code)).fetchone()
            count = (row[0] if row else 0) + 1
            policy = update_cooldown(count, scope_kind="pair_family") if count >= 2 else {"reject_count": count, "cooldown_until": None, "penalty": count / 3}
            self.db.execute("INSERT INTO cooldown_state(scope_kind,scope_key,reason_code,reject_count,cooldown_until,penalty,last_reject_at) VALUES('pair_family',?,?,?,?,?,?) ON CONFLICT(scope_kind,scope_key,reason_code) DO UPDATE SET reject_count=excluded.reject_count,cooldown_until=excluded.cooldown_until,penalty=excluded.penalty,last_reject_at=excluded.last_reject_at", (pair_key, reason_code, policy["reject_count"], policy["cooldown_until"], policy["penalty"], at))
        self.db.commit()

    def record_positive(self, *, family_ids: Iterable[str] = (), pair_key: str | None = None) -> None:
        """Reduce exact-scope learned penalties after an accepted candidate."""
        for family_id in family_ids:
            self.db.execute("UPDATE evidence_family_state SET accepted_count=accepted_count+1,updated_at=? WHERE family_id=?", (now(), family_id))
        if pair_key:
            self.db.execute("UPDATE cooldown_state SET penalty=0,cooldown_until=NULL,last_positive_at=? WHERE scope_kind='pair_family' AND scope_key=?", (now(), pair_key))
        self.db.commit()

    def rebuild_derived_state(self) -> dict[str, int]:
        """Rebuild cooldown materializations from the append-only event table."""
        self.db.execute("DELETE FROM cooldown_state")
        rows = self.db.execute("SELECT run_id,agent,candidate_id,evidence_ids_json,family_ids_json,recall_channels_json,reason_code,pair_family_key,at,anchor_refs_json FROM candidate_rejections ORDER BY at,event_id").fetchall()
        for row in rows:
            self.record_rejection(run_id=row["run_id"], agent=row["agent"], candidate_id=row["candidate_id"], evidence_ids=json.loads(row["evidence_ids_json"]), family_ids=json.loads(row["family_ids_json"]), recall_channels=json.loads(row["recall_channels_json"]), reason_code=row["reason_code"], anchor_refs=json.loads(row["anchor_refs_json"] or "[]"), _persist_event=False)
        return {"rejection_events": len(rows), "cooldown_rows": self.db.execute("SELECT count(*) FROM cooldown_state").fetchone()[0]}

    def complete_retrieval(self, *, run_id: str, agent: str, decisions: Iterable[Mapping[str, Any]]) -> dict[str, int]:
        """Consume optional structured judge decisions without requiring them.

        A decision is ``{candidate_id, status, reason_code?, anchor_refs?}``.
        Unknown IDs are ignored, keeping completion idempotent and safe when a
        model returns a prose response instead of the optional envelope.
        """
        row = self.db.execute("SELECT metadata_json FROM retrieval_runs WHERE retrieval_run_id=?", (run_id,)).fetchone()
        if not row: return {"seen": 0, "accepted": 0, "rejected": 0}
        metadata = json.loads(row[0]); records = {x.get("candidate_id"): x for x in metadata.get("candidate_records", [])}
        seen = accepted = rejected = 0
        for decision in decisions:
            candidate_id = str(decision.get("candidate_id") or "")
            candidate = records.get(candidate_id)
            if not candidate: continue
            seen += 1
            families = candidate.get("family_ids", [])
            for family in families:
                self.db.execute("INSERT INTO evidence_family_state(family_id,last_llm_seen_at,llm_seen_count,updated_at) VALUES(?,?,?,?) ON CONFLICT(family_id) DO UPDATE SET last_llm_seen_at=excluded.last_llm_seen_at,llm_seen_count=evidence_family_state.llm_seen_count+1,updated_at=excluded.updated_at", (family, now(), 1, now()))
            status = str(decision.get("status") or decision.get("decision") or "").lower()
            if status in {"accepted", "accept", "delivered"}:
                accepted += 1; self.record_positive(family_ids=families, pair_key=candidate.get("pair_key"))
            else:
                rejected += 1
                self.record_rejection(run_id=run_id, agent=agent, candidate_id=candidate_id, evidence_ids=[candidate.get("left_evidence_id"), candidate.get("right_evidence_id")], family_ids=families, recall_channels=candidate.get("retrieval", {}).get("channels", []), reason_code=str(decision.get("reason_code") or "MODEL_REJECT_OTHER"), anchor_refs=decision.get("anchor_refs", []))
        metadata.update({"model_seen_count": seen, "model_accepted_count": accepted, "model_rejected_count": rejected, "completed_at": now()})
        self.db.execute("UPDATE retrieval_runs SET metadata_json=? WHERE retrieval_run_id=?", (json.dumps(metadata, ensure_ascii=False), run_id)); self.db.commit()
        return {"seen": seen, "accepted": accepted, "rejected": rejected}

    def _pair_candidates(self, run_id: str, count: int = 8) -> tuple[list[dict[str, Any]], dict[str, int], str]:
        generation = self.complete_generation()
        seed = digest(f"{run_id}:{generation}:retrieval-v1")
        rng = random.Random(seed)
        state = self._family_state()
        self_pool = [r for r in self._candidate_rows("self") if not r["already_synthesized"] and not r["is_derived"]]
        other_pool = [r for voice in ("external", "system", "unknown") for r in self._candidate_rows(voice)]
        self_rows = list(select_stratified(self_pool, seed=seed + ":self", limit=24, state=state))
        other_rows = list(select_stratified(other_pool, seed=seed + ":other", limit=32, state=state))
        self._mark_explored(self_rows + other_rows, now())
        candidates: list[dict[str, Any]] = []; excluded = {"same_family":0,"already_synthesized":0,"weak_provenance":0,"duplicate":0}
        seen: set[str] = set()
        for left in self_rows[:70]:
            lt = _terms(left["heading_path"] + " " + left["text"][:1600])
            if not lt: continue
            for right in other_rows[:120]:
                if left["evidence_family_id"] == right["evidence_family_id"]: excluded["same_family"] += 1; continue
                rt = retrieval_terms(right["heading_path"] + " " + right["text"][:1600]); shared = sorted(lt & rt)
                linked = any(x[0] in right["source_path"] or x[0] in left["source_path"] for x in self.db.execute("SELECT right_ref FROM links WHERE left_evidence_id=?", (left["evidence_id"],)))
                same_domain = left["source_path"].split("/",1)[0] == right["source_path"].split("/",1)[0]
                # Exploration is an independent recall channel. A pair with no
                # lexical overlap is valid if it is selected from distinct,
                # substantive families; lexical overlap is never an admission gate.
                semantic_similarity = cosine(self._embedding(left["evidence_id"]) or [], self._embedding(right["evidence_id"]) or [])
                channels = ["lexical", "bm25"] if shared else ["explore"]
                if semantic_similarity >= 0.12:
                    channels.append("semantic")
                if linked: channels.append("entity")
                if json.loads(left["timestamps_json"]) and json.loads(right["timestamps_json"]):
                    channels.append("temporal")
                if not same_domain:
                    channels.append("domain")
                # Lexical cooldown is channel-scoped: preserve semantic/entity/
                # exploration recall for the same subject when available.
                cooldown_enabled = self.retrieval_flags()["candidate_retrieval_cooldown_enabled"]
                active_anchor = cooldown_enabled and any(cooldown_active(r["cooldown_until"]) for term in shared for r in self.db.execute("SELECT cooldown_until FROM cooldown_state WHERE scope_kind='anchor' AND scope_key=? AND reason_code='LEXICAL_COLLISION'", (digest(term),)))
                if active_anchor and set(channels) <= {"lexical", "bm25"}:
                    excluded["cooldown"] = excluded.get("cooldown", 0) + 1
                    continue
                if active_anchor:
                    channels = [c for c in channels if c not in {"lexical", "bm25"}]
                strategy = "lexical_fts" if shared else "exploration"
                if linked: strategy = "wikilink"
                elif left["assertion_kind"] == "question" or right["assertion_kind"] == "question": strategy = "question_possible_closure"
                elif left["assertion_kind"] == "decision" or right["assertion_kind"] == "decision": strategy = "decision_possible_outcome"
                elif not same_domain and len(shared) >= 1: strategy = "cross_domain_structural_candidate"
                ldates=json.loads(left["timestamps_json"]); rdates=json.loads(right["timestamps_json"])
                if strategy == "lexical_fts" and ldates.get("recorded_at") and rdates.get("recorded_at"): strategy = "temporal_recurrence"
                features = pair_features(left, right, channels=channels, semantic_similarity=semantic_similarity, exploration_bonus=1.0 if "explore" in channels else 0.0)
                pair_base_key = pair_family_key(left["evidence_family_id"], right["evidence_family_id"], channels[0])
                active_pair = cooldown_enabled and any(cooldown_active(r["cooldown_until"]) for r in self.db.execute("SELECT cooldown_until FROM cooldown_state WHERE scope_kind='pair_family' AND scope_key=?", (pair_base_key,)))
                if active_pair and not ({"semantic", "entity"} & set(channels)):
                    excluded["cooldown"] = excluded.get("cooldown", 0) + 1
                    continue
                reason = hard_filter(left, right, features) if self.retrieval_flags()["candidate_retrieval_hard_filter_enabled"] else None
                if reason:
                    excluded[reason.lower()] = excluded.get(reason.lower(), 0) + 1
                    continue
                key = pair_family_key(left["evidence_family_id"], right["evidence_family_id"], "lexical" if "lexical" in channels else channels[0])
                if key in seen or self.db.execute("SELECT 1 FROM delivered_connections WHERE pair_key=?", (key,)).fetchone(): excluded["duplicate"] += 1; continue
                seen.add(key)
                candidates.append({"candidate_id":"cand_" + key[:16],"pair_key":key,"family_ids":[left["evidence_family_id"], right["evidence_family_id"]],"left_evidence_id":left["evidence_id"],"right_evidence_id":right["evidence_id"],"left":{"source_type":left["source_type"],"voice":left["voice"],"timestamps":json.loads(left["timestamps_json"])},"right":{"source_type":right["source_type"],"voice":right["voice"],"timestamps":json.loads(right["timestamps_json"])},"strategy":strategy,"reason_features":{"shared_terms":shared[:8],"shared_entity_candidates":shared[:4],"domain_distance":not same_domain, **features.as_dict()},"retrieval":{"channels":channels,"fused_score":rank_score(features),"features":features.as_dict(),"strata":{"time_a": _time_bucket(left), "time_b": _time_bucket(right), "domain_a": left["source_path"].split("/",1)[0], "domain_b": right["source_path"].split("/",1)[0], "source_type_a": left["source_type"], "source_type_b": right["source_type"]}},"strategy_local_scores":{"overlap":len(shared),"random_tiebreak":rng.random()}})
        ranked = sorted(candidates, key=lambda item: (-item["retrieval"]["fused_score"], item["strategy_local_scores"]["random_tiebreak"], item["candidate_id"]))
        selected: list[dict[str, Any]] = []
        family_counts: dict[str, int] = {}
        reserve = max(0, min(count, int(count * (0.20 if count <= 8 else 0.10))))
        exploration = [item for item in ranked if "explore" in item["retrieval"]["channels"]]
        order = exploration[:reserve] + [item for item in ranked if item not in exploration[:reserve]]
        for item in order:
            if len(selected) >= count: break
            if any(family_counts.get(f, 0) >= 2 for f in item["family_ids"]): continue
            selected.append(item)
            for family in item["family_ids"]: family_counts[family] = family_counts.get(family, 0) + 1
        if selected:
            return selected, excluded, seed
        # A controlled random leap remains provenance-qualified, bounded, and
        # replayable. It is a candidate only; it never becomes an insight itself.
        if self_rows and other_rows and len(candidates) < count:
            left, right = self_rows[0], other_rows[0]
            key=digest("leap|"+left["evidence_family_id"]+"|"+right["evidence_family_id"])
            if key not in seen:
                candidates.append({"candidate_id":"cand_"+key[:16],"pair_key":key,"left_evidence_id":left["evidence_id"],"right_evidence_id":right["evidence_id"],"strategy":"controlled_random_leap","reason_features":{"seeded":True,"domain_distance":left["source_path"].split("/",1)[0] != right["source_path"].split("/",1)[0]},"strategy_local_scores":{"random_tiebreak":rng.random()}})
        return candidates, excluded, seed

    def shadow_pack(self, kind: str, run_id: str | None = None) -> dict[str, Any]:
        """Build, persist, and audit a non-production ContextPack; never calls a model."""
        if kind not in {"serendipity", "intelligence"}: raise ValueError("kind must be serendipity or intelligence")
        generation = self.complete_generation()
        if generation is None: raise ValueError("index has no COMPLETE generation")
        run_id = run_id or f"shadow_{kind}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        candidates, excluded, seed = self._pair_candidates(run_id, 8 if kind == "serendipity" else 10)
        if kind == "serendipity":
            eligible = self.db.execute("SELECT count(*) FROM evidence_units WHERE active=1 AND retrieval_only=0").fetchone()[0]
            families = self.db.execute("SELECT count(DISTINCT evidence_family_id) FROM evidence_units WHERE active=1 AND retrieval_only=0").fetchone()[0]
            pack: dict[str, Any] = {"schema":"serendipity.context-pack.v1","run_id":run_id,"index_generation":generation,"rng_seed":"sha256:"+seed,"window":{"mode":"index-current"},"budget":{"initial_tokens":8000,"max_expansions":4,"max_expansion_tokens":1200,"max_total_tool_tokens":5000,"final_tokens":1200},"seeds":sorted({x["left_evidence_id"] for x in candidates})[:6],"candidates":candidates[:8],"excluded":excluded,"retrieval_summary":{"eligible_evidence_count":eligible,"eligible_family_count":families,"seed_count":len(set(x["left_evidence_id"] for x in candidates)),"raw_pair_count":sum(excluded.values()) + len(candidates),"hard_filtered_count":sum(v for k,v in excluded.items() if k in {"title_only","structure_only","template_only","insufficient_body","stopword_only_collision","duplicate_content","same_family_trivial","same_topic_no_mechanism_delta","unverified_source"}),"llm_candidate_count":len(candidates[:8]),"embedding_degraded":not self.retrieval_flags()["candidate_retrieval_embeddings_enabled"],"silence_class":"NORMAL_SILENCE" if candidates else "HARD_FILTER_STARVATION","flags":self.retrieval_flags()},"versions":{"schema":SCHEMA_VERSION,"segmenter":SEGMENTER_VERSION,"retrieval_policy":"v0.6","embedding":self._embedding_model()}}
        else:
            worlds = [r for r in self._candidate_rows("system") if r["assertion_kind"] in {"claim","question","summary"}]
            targets = [r for r in self._candidate_rows("self") if r["assertion_kind"] in {"belief","decision","question","interpretation","observation"} and not r["already_synthesized"]]
            worlds = list(select_stratified(worlds, seed=seed + ":world", limit=32, state=self._family_state()))
            targets = list(select_stratified(targets, seed=seed + ":personal", limit=24, state=self._family_state()))
            matches=[]
            intelligence_excluded = dict(excluded)
            for world in worlds:
                for personal in targets:
                    features = pair_features(world, personal, channels=("semantic", "explore"), exploration_bonus=1.0)
                    reason = hard_filter(world, personal, features)
                    if reason:
                        intelligence_excluded[reason.lower()] = intelligence_excluded.get(reason.lower(), 0) + 1
                        continue
                    relation = {"question":"answers_question", "belief":"updates_belief", "decision":"changes_decision_input", "interpretation":"updates_belief", "observation":"changes_project_assumption"}.get(personal["assertion_kind"], "closes_uncertainty")
                    shared=sorted(retrieval_terms(world["text"]) & retrieval_terms(personal["text"]))
                    matches.append({"candidate_id":"cand_" + digest(world["evidence_id"] + "|" + personal["evidence_id"])[:16],"pair_key":pair_family_key(world["evidence_family_id"], personal["evidence_family_id"], "semantic"),"family_ids":[world["evidence_family_id"], personal["evidence_family_id"]],"left_evidence_id":world["evidence_id"],"right_evidence_id":personal["evidence_id"],"world_evidence_id":world["evidence_id"],"personal_evidence_id":personal["evidence_id"],"match_reason":{"shared_terms":shared[:8],"retrieval_channels":["semantic","explore"]},"relation_type":relation,"possible_update_type":relation,"urgency":"unknown","retrieval":{"channels":features.recall_channels,"fused_score":rank_score(features, profile="intelligence"),"features":features.as_dict()}})
            pack={"schema":"intelligence.context-pack.v1","run_id":run_id,"index_generation":generation,"world_watermark":None,"budget":{"initial_tokens":6000,"max_expansions":3,"max_expansion_tokens":1200,"max_total_tool_tokens":4000},"world_deltas":[r["evidence_id"] for r in worlds[:10]],"personal_match_targets":[r["evidence_id"] for r in targets[:6]],"matches":matches[:10],"excluded":intelligence_excluded,"retrieval_summary":{"eligible_world_evidence":len(worlds),"eligible_personal_hooks":len(targets),"raw_pair_count":len(worlds)*len(targets),"llm_candidate_count":len(matches[:10]),"embedding_degraded":not self.retrieval_flags()["candidate_retrieval_embeddings_enabled"],"flags":self.retrieval_flags()},"versions":{"schema":SCHEMA_VERSION,"segmenter":SEGMENTER_VERSION,"retrieval_policy":"v0.6","embedding":self._embedding_model()}}
        ids = set(pack.get("seeds", [])) | {v for item in pack.get("candidates", []) for v in (item["left_evidence_id"], item["right_evidence_id"])} | set(pack.get("world_deltas", [])) | set(pack.get("personal_match_targets", []))
        if ids:
            placeholders=",".join("?" for _ in ids)
            chars=self.db.execute(f"SELECT COALESCE(sum(length(text)),0) FROM evidence_units WHERE evidence_id IN ({placeholders})", tuple(ids)).fetchone()[0]
        else: chars=0
        pack["comparison"]={"before_index":_run_baseline(kind),"after_context_pack":{"candidate_evidence_count":len(ids),"bounded_source_characters":chars,"rough_initial_token_upper_bound":(chars + 3)//4,"provider_usage":"not_called_in_shadow"}}
        unsigned=dict(pack); pack["pack_hash"]="sha256:"+digest(json.dumps(unsigned,ensure_ascii=False,sort_keys=True))
        candidate_records = pack.get("candidates", []) if kind == "serendipity" else pack.get("matches", [])
        self.db.execute("INSERT OR REPLACE INTO retrieval_runs VALUES(?,?,?,?)", (run_id,generation,json.dumps({"kind":kind,"pack_hash":pack["pack_hash"],"candidate_count":len(candidate_records),"candidate_records":candidate_records,"excluded":pack.get("excluded", excluded),"retrieval_summary":pack.get("retrieval_summary", {}),"retrieval_policy":"v0.6"},ensure_ascii=False),now())); self.db.commit()
        return pack


def default_index(vault: Path) -> Path: return vault / ".index" / "cognition" / "cognition.sqlite3"

def main(argv: list[str] | None = None) -> int:
    parser=argparse.ArgumentParser(prog="pap cognition", description="Local derived evidence index")
    parser.add_argument("--vault", type=Path, default=Path(os.environ.get("PAP_VAULT", Path.home()/"Documents/Obsidian")))
    parser.add_argument("--db", type=Path)
    sub=parser.add_subparsers(dest="cmd",required=True); sub.add_parser("status"); pindex=sub.add_parser("index"); pindex.add_argument("--dry-run",action="store_true"); pindex.add_argument("--full",action="store_true",help="rebuild only the derived cognitive SQLite database"); pe=sub.add_parser("evidence"); pe.add_argument("evidence_id"); pe.add_argument("--excerpt",type=int,default=DEFAULT_EXCERPT); ps=sub.add_parser("search"); ps.add_argument("query"); ps.add_argument("--limit",type=int,default=10); ps.add_argument("--source-type"); ps.add_argument("--voice"); pshadow=sub.add_parser("shadow",help="build a non-production ContextPack"); pshadow.add_argument("kind",choices=("serendipity","intelligence")); pshadow.add_argument("--run-id")
    args=parser.parse_args(argv); vault=args.vault.expanduser().resolve(); db=(args.db or default_index(vault)).expanduser(); index=Index(db)
    try:
        if args.cmd=="status": result=index.status()
        elif args.cmd=="index":
            if args.full:
                index.close(); db.unlink(missing_ok=True); index=Index(db)
            result=index.build(vault,dry_run=args.dry_run)
        elif args.cmd=="evidence": result=index.get(args.evidence_id,args.excerpt) or {"error":"not found"}
        elif args.cmd=="search": result=index.search(args.query,limit=args.limit,source_type=args.source_type,voice=args.voice)
        else:
            result=index.shadow_pack(args.kind,args.run_id)
            pack_dir=db.parent / "context-packs"; pack_dir.mkdir(exist_ok=True)
            pack_path = pack_dir / f"{result['run_id']}.json"
            serialized = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
            if os.environ.get("PAP_RUN_ID") or os.environ.get("PAP_OBSERVABILITY_DIR"):
                with paplog.filesystem(pack_path, effect="write",
                                       attributes={"bytes": len(serialized.encode("utf-8"))}):
                    pack_path.write_text(serialized, encoding="utf-8")
            else:
                pack_path.write_text(serialized, encoding="utf-8")
            evidence_ids = sorted(set(result.get("seeds", [])) | set(result.get("world_deltas", [])) |
                                  set(result.get("personal_match_targets", [])))
            paplog.event("pap.context_pack.created", subject={"type": result["schema"], "id": result["run_id"]},
                         execution={"run_id": os.environ.get("PAP_RUN_ID")},
                         attributes={"uri": str(pack_path), "pack_hash": result.get("pack_hash"),
                                     "bytes": len(serialized.encode("utf-8")), "kind": args.kind,
                                     "index_generation": result.get("index_generation")},
                         links=[{"type": "derived_from", "target_type": "evidence", "target_id": item}
                                for item in evidence_ids])
        print(json.dumps(result,ensure_ascii=False,indent=2,default=str)); return 0 if not (isinstance(result,dict) and result.get("error")) else 2
    finally: index.close()

if __name__ == "__main__": raise SystemExit(main())
