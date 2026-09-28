"""Adapters for observed Obsidian WeRead/Koodo Markdown export shapes.

These parsers accept export files, not private platform APIs. They are strict
about source IDs and retain the whole raw export as immutable provenance.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from .pipeline import _index_trace
from .store import Library, LibrarianError, _json, _now, _unknown_time, validate


_BLOCK = re.compile(r"\^([A-Za-z0-9_-]+)\s*$")


def parse_weread(raw: bytes) -> tuple[str, str, list[dict[str, Any]]]:
    text = raw.decode("utf-8-sig")
    lines = text.splitlines()
    book_id = next((line.partition(":")[2].strip().strip('"') for line in lines
                    if line.startswith("bookId:")), None)
    title = next((line.removeprefix("> [!abstract]").strip() for line in lines
                  if line.startswith("> [!abstract]")), None)
    if not book_id or not title:
        raise LibrarianError("VALIDATION_FAILED", "WeRead export needs bookId and title")
    section = ""
    chapter = None
    entries: list[dict[str, Any]] = []
    quote: list[str] = []
    mode = None
    note = None

    def flush(anchor: str | None) -> None:
        nonlocal quote, note, mode
        content = "\n".join(part.strip() for part in quote if part.strip()).strip()
        if mode and content and anchor:
            entries.append({"source_record_id": anchor, "chapter": chapter,
                            "printed_text": content, "annotation": note,
                            "trace_types": ["highlight", "inline_note"] if note else ["highlight"]})
        quote, note, mode = [], None, None

    anchor = None
    for line in lines:
        clean = line.strip()
        if clean == "# 高亮划线":
            section, chapter = "highlights", None
            continue
        if clean == "# 读书笔记":
            flush(anchor)
            section, chapter, anchor = "notes", None, None
            continue
        if clean.startswith("# ") and section:
            flush(anchor)
            section, chapter, anchor = "", None, None
            continue
        if clean.startswith("## ") and section:
            chapter = clean[3:].strip()
            continue
        if section == "highlights":
            if clean.startswith("📌") or clean.startswith("> 📌"):
                flush(anchor)
                anchor = None
                mode = "highlight"
                initial = clean.split("📌", 1)[1].strip()
                if initial:
                    quote.append(initial)
            elif mode and clean.startswith("> ⏱"):
                match = _BLOCK.search(clean)
                anchor = match.group(1) if match else None
                flush(anchor)
                anchor = None
            elif mode and clean and not clean.startswith("#"):
                quote.append(clean.removeprefix("> "))
        elif section == "notes":
            if clean == "### 划线评论":
                flush(anchor)
                anchor = None
                mode = "note"
            elif mode and clean.startswith("- 💭"):
                note = clean.removeprefix("- 💭").strip()
            elif mode and clean.startswith("- ⏱"):
                flush(anchor)
                anchor = None
            elif mode and clean and not clean.startswith(("📌", "###")):
                match = _BLOCK.search(clean)
                if match:
                    anchor = match.group(1)
                    clean = clean[:match.start()].strip()
                if clean:
                    quote.append(clean)
    flush(anchor)
    ids = [entry["source_record_id"] for entry in entries]
    if len(ids) != len(set(ids)):
        raise LibrarianError("VALIDATION_FAILED", "duplicate WeRead source record ID")
    return book_id, title, entries


def parse_koodo(raw: bytes) -> tuple[str, str, list[dict[str, Any]]]:
    text = raw.decode("utf-8-sig")
    lines = text.splitlines()
    title = next((line[3:].strip() for line in lines if line.startswith("## ")), None)
    if not title:
        raise LibrarianError("VALIDATION_FAILED", "Koodo export needs a title heading")
    chapter = None
    entries = []
    quote: list[str] = []
    seen: dict[str, int] = {}

    def flush() -> None:
        nonlocal quote
        content = "\n".join(quote).strip()
        if content:
            base = hashlib.sha256(_json([chapter, content]).encode()).hexdigest()[:24]
            seen[base] = seen.get(base, 0) + 1
            entries.append({"source_record_id": f"{base}-{seen[base]}",
                            "chapter": chapter, "printed_text": content,
                            "annotation": None, "trace_types": ["highlight"]})
        quote = []

    for line in lines:
        clean = line.strip()
        if clean.startswith("### "):
            flush()
            chapter = clean[4:].strip()
        elif clean.startswith("> "):
            quote.append(clean[2:])
        elif clean.startswith("*Date:") or clean == "---":
            flush()
    flush()
    return title, title, entries


def ingest_export(lib: Library, owner_id: str, medium: str, source_key: str,
                  raw: bytes) -> list[dict[str, Any]]:
    """Import one stable export; changed files require reconciliation."""
    if not owner_id or not source_key or not isinstance(raw, bytes) or medium not in {"weread", "koodo"}:
        raise LibrarianError("VALIDATION_FAILED", "invalid export identity")
    digest = hashlib.sha256(raw).hexdigest()
    prior = lib.db.execute("SELECT payload_sha256,trace_ids FROM digital_exports WHERE owner_id=? AND medium=? AND source_key=?",
                           (owner_id, medium, source_key)).fetchone()
    if prior:
        if prior["payload_sha256"] != digest:
            raise LibrarianError("RECONCILIATION_REQUIRED", "changed export needs source-record reconciliation")
        return [lib.get(owner_id, "ReadingTrace", identifier) for identifier in json.loads(prior["trace_ids"])]
    source_book_id, title, entries = (parse_weread(raw) if medium == "weread" else parse_koodo(raw))
    if not entries:
        raise LibrarianError("VALIDATION_FAILED", "export contains no identifiable highlights")
    raw_asset = lib._save_object(raw, "text/markdown")
    work_id = "work_" + hashlib.sha256(_json([owner_id, medium, source_book_id]).encode()).hexdigest()[:32]
    existing = lib.db.execute("SELECT 1 FROM records WHERE owner_id=? AND model='Work' AND id=?",
                              (owner_id, work_id)).fetchone()
    work = {"object_type": "Work", "schema_version": "0.1.0", "id": work_id,
            "owner_id": owner_id, "created_at": _now(), "title": title,
            "original_title": None, "authors": [],
            "identifiers": [{"scheme": medium + "_book_id", "value": source_book_id}],
            "revision": 1, "supersedes_revision": None}
    traces = []
    for entry in entries:
        trace_id = "rt_" + hashlib.sha256(_json([owner_id, medium, source_book_id,
                                                   entry["source_record_id"]]).encode()).hexdigest()[:32]
        trace = {"object_type": "ReadingTrace", "schema_version": "0.1.0",
                 "id": trace_id, "owner_id": owner_id, "created_at": _now(),
                 "revision": 1, "supersedes_revision": None, "status": "active",
                 "context_state": "resolved", "work_id": work_id,
                 "edition_id": None, "book_instance_id": None, "session_id": None,
                 "medium": medium,
                 "location": {"kind": "digital", "chapter": entry["chapter"],
                              "paragraph": None, "source_locator": entry["source_record_id"],
                              "epub_cfi": None},
                 "trace_types": entry["trace_types"],
                 "content": {"printed_text": {"text": entry["printed_text"],
                                                "confidence": None, "basis": "source_payload"},
                             "annotation": {"text": entry["annotation"],
                                            "confidence": None,
                                            "basis": "source_payload" if entry["annotation"] else "unknown"},
                             "symbols": []},
                 "source": {"kind": medium, "raw_payload": raw_asset,
                            "source_record_id": entry["source_record_id"]},
                 "provenance": [raw_asset], "confidence": {"book_resolution": None,
                                                            "page_number": None},
                 "marked_at": _unknown_time(),
                 "attribution": {"mark_author": "unknown", "basis": "unknown"},
                 "intent_signals": [],
                 "review": {"required": False, "state": "none", "reason": None}}
        validate("ReadingTrace", trace)
        traces.append(trace)
    with lib.db:
        if not existing:
            lib._put(work)
        for trace in traces:
            old = lib.db.execute("SELECT body FROM records WHERE owner_id=? AND model='ReadingTrace' AND id=? AND current=1",
                                 (owner_id, trace["id"])).fetchone()
            if old:
                previous = json.loads(old["body"])
                if previous["content"] != trace["content"] or previous["location"] != trace["location"]:
                    raise LibrarianError("RECONCILIATION_REQUIRED", "source record changed or was corrected")
                continue
            lib._put(trace)
            _index_trace(lib, trace)
            lib._event(owner_id, "reading.trace.created", "reading_trace", trace["id"], 1,
                       {"trace_id": trace["id"], "revision": 1, "medium": medium,
                        "book_instance_id": None}, source_key)
        lib.db.execute("INSERT INTO digital_exports VALUES(?,?,?,?,?)",
                       (owner_id, medium, source_key, digest,
                        _json([trace["id"] for trace in traces])))
    return [lib.get(owner_id, "ReadingTrace", trace["id"]) for trace in traces]
