"""Read-only WeRead Agent API adapter with owner-scoped, replayable sync."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .koodo_native import _revise
from .pipeline import _index_trace
from .store import Library, LibrarianError, _json, _now, _unknown_time, validate

GATEWAY = "https://i.weread.qq.com/api/agent/gateway"


def _call(api_key: str, api_name: str, **params: Any) -> dict[str, Any]:
    body = _json({"api_name": api_name, "skill_version": "1.0.3", **params}).encode()
    request = urllib.request.Request(
        GATEWAY, body, headers={"Authorization": "Bearer " + api_key,
                                "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            result = json.load(response)
    except (urllib.error.URLError, TimeoutError, ValueError) as error:
        raise LibrarianError("UPSTREAM_UNAVAILABLE", "WeRead gateway request failed") from error
    if not isinstance(result, dict) or result.get("errcode") or result.get("error"):
        raise LibrarianError("UPSTREAM_UNAVAILABLE", "WeRead gateway returned an error")
    return result


def fetch_weread_book(api_key: str, book_id: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Fetch a complete single-book snapshot, rejecting partial pagination."""
    if not api_key or not book_id:
        raise LibrarianError("VALIDATION_FAILED", "WeRead API key and book ID required")
    highlights = _call(api_key, "/book/bookmarklist", bookId=book_id)
    book = highlights.get("book")
    if not isinstance(book, dict) or book.get("bookId") != book_id or not book.get("title"):
        raise LibrarianError("UPSTREAM_FORMAT_UNSUPPORTED", "WeRead book identity missing")
    marks = highlights.get("updated")
    if not isinstance(marks, list) or not isinstance(highlights.get("chapters"), list):
        raise LibrarianError("UPSTREAM_FORMAT_UNSUPPORTED", "WeRead highlights incomplete")
    chapters = {chapter.get("chapterUid"): chapter.get("title")
                for chapter in highlights["chapters"] if isinstance(chapter, dict)}
    records: list[dict[str, Any]] = []
    for mark in marks:
        if not isinstance(mark, dict) or mark.get("bookId") != book_id or not mark.get("bookmarkId"):
            raise LibrarianError("UPSTREAM_FORMAT_UNSUPPORTED", "WeRead highlight identity invalid")
        records.append({"kind": "bookmark", "book": book, "record": mark,
                        "chapter": chapters.get(mark.get("chapterUid"))})
    sync_key: int | str = 0
    seen_keys = set()
    for _ in range(100):
        page = _call(api_key, "/review/list/mine", bookid=book_id,
                     synckey=sync_key, count=100)
        reviews = page.get("reviews")
        if not isinstance(reviews, list) or "hasMore" not in page:
            raise LibrarianError("UPSTREAM_FORMAT_UNSUPPORTED", "WeRead reviews incomplete")
        for envelope in reviews:
            if not isinstance(envelope, dict) or not isinstance(envelope.get("review"), dict):
                raise LibrarianError("UPSTREAM_FORMAT_UNSUPPORTED", "WeRead review invalid")
            review = envelope["review"]
            if (not envelope.get("reviewId") or review.get("reviewId") != envelope["reviewId"]
                    or review.get("bookId") != book_id):
                raise LibrarianError("UPSTREAM_FORMAT_UNSUPPORTED", "WeRead review identity invalid")
            records.append({"kind": "review", "book": book, "record": review,
                            "chapter": review.get("chapterTitle") or review.get("chapterName")})
        if not page["hasMore"]:
            break
        next_key = page.get("synckey")
        if next_key is None or next_key == sync_key or next_key in seen_keys:
            raise LibrarianError("UPSTREAM_FORMAT_UNSUPPORTED", "WeRead review cursor stalled")
        seen_keys.add(sync_key)
        sync_key = next_key
    else:
        raise LibrarianError("UPSTREAM_FORMAT_UNSUPPORTED", "WeRead review page limit exceeded")
    keys = [f"{item['kind']}:{item['record']['bookmarkId' if item['kind']=='bookmark' else 'reviewId']}"
            for item in records]
    if len(keys) != len(set(keys)):
        raise LibrarianError("UPSTREAM_FORMAT_UNSUPPORTED", "WeRead record IDs duplicated")
    return book, records


def _ids(owner_id: str, source_id: str, book_id: str, record_key: str) -> tuple[str, str]:
    work_id = "work_" + hashlib.sha256(_json([owner_id, "weread-api", source_id, book_id]).encode()).hexdigest()[:32]
    trace_id = "rt_" + hashlib.sha256(_json([owner_id, "weread-api", source_id, book_id, record_key]).encode()).hexdigest()[:32]
    return work_id, trace_id


def _fields(item: dict[str, Any]) -> dict[str, Any]:
    record, kind = item["record"], item["kind"]
    printed = record.get("markText") if kind == "bookmark" else record.get("abstract")
    annotation = None if kind == "bookmark" else record.get("content")
    if not isinstance(printed, str):
        printed = None
    if not isinstance(annotation, str):
        annotation = None
    if not printed and not annotation:
        raise LibrarianError("UPSTREAM_FORMAT_UNSUPPORTED", "WeRead record has no text")
    locator = _json({key: record.get(key) for key in ("chapterIdx", "chapterUid", "range")
                     if key in record})
    types = (["highlight", "inline_note"] if printed and annotation else
             ["highlight"] if printed else ["inline_note"])
    return {"location": {"kind": "digital", "chapter": item.get("chapter") or None,
                         "paragraph": None, "source_locator": locator, "epub_cfi": None},
            "trace_types": types,
            "content": {"printed_text": {"text": printed, "confidence": None,
                                         "basis": "source_payload" if printed else "unknown"},
                        "annotation": {"text": annotation, "confidence": None,
                                       "basis": "source_payload" if annotation else "unknown"},
                        "symbols": []}}


def _time(record: dict[str, Any]) -> dict[str, Any]:
    value = record.get("createTime")
    if isinstance(value, int) and 0 < value < 253402300800:
        return {"value": datetime.fromtimestamp(value, timezone.utc).isoformat().replace("+00:00", "Z"),
                "confidence": None, "basis": "source_payload"}
    return _unknown_time()


def _matches_source(lib: Library, trace: dict[str, Any]) -> bool:
    prior = json.loads(lib._read_object(trace["source"]["raw_payload"]))
    fields = _fields(prior)
    return all(trace[key] == value for key, value in fields.items())


def sync_weread_book(lib: Library, owner_id: str, source_id: str, book: dict[str, Any],
                     items: list[dict[str, Any]], *, allow_empty_source: bool = False) -> dict[str, int]:
    """Apply a verified complete snapshot; source edits to corrected traces are held."""
    if not owner_id or not re.fullmatch(r"[A-Za-z0-9_-]+", source_id):
        raise LibrarianError("VALIDATION_FAILED", "trusted owner and stable source ID required")
    book_id = book.get("bookId")
    if not isinstance(book_id, str) or not book_id or not isinstance(book.get("title"), str):
        raise LibrarianError("UPSTREAM_FORMAT_UNSUPPORTED", "WeRead book identity invalid")
    if not isinstance(items, list):
        raise LibrarianError("UPSTREAM_FORMAT_UNSUPPORTED", "WeRead records invalid")
    prepared = []
    for item in items:
        if not isinstance(item, dict) or item.get("kind") not in {"bookmark", "review"} or item.get("book") != book:
            raise LibrarianError("UPSTREAM_FORMAT_UNSUPPORTED", "WeRead source item invalid")
        record = item.get("record")
        id_field = "bookmarkId" if item["kind"] == "bookmark" else "reviewId"
        if not isinstance(record, dict) or not isinstance(record.get(id_field), str) or not record[id_field] or record.get("bookId") != book_id:
            raise LibrarianError("UPSTREAM_FORMAT_UNSUPPORTED", "WeRead source item identity invalid")
        key = f"{item['kind']}:{record[id_field]}"
        prepared.append((key, item, _fields(item)))
    if len({key for key, _, _ in prepared}) != len(prepared):
        raise LibrarianError("UPSTREAM_FORMAT_UNSUPPORTED", "WeRead source IDs duplicated")
    if not prepared and not allow_empty_source and lib.db.execute(
            "SELECT 1 FROM weread_native_records WHERE owner_id=? AND source_id=? AND book_id=? LIMIT 1",
            (owner_id, source_id, book_id)).fetchone():
        raise LibrarianError("RECONCILIATION_REQUIRED", "empty WeRead snapshot needs explicit confirmation")
    counts = {"source_records": len(prepared), "created": 0, "updated": 0,
              "deleted": 0, "unchanged": 0, "pending": 0}
    seen = set()
    with lib.transaction():
        lib.bind_digital_source(owner_id, "weread", source_id)
        for key, item, fields in prepared:
            seen.add(key)
            work_id, trace_id = _ids(owner_id, source_id, book_id, key)
            raw = _json(item).encode()
            digest = hashlib.sha256(raw).hexdigest()
            row = lib.db.execute(
                "SELECT * FROM weread_native_records WHERE owner_id=? AND source_id=? AND record_key=?",
                (owner_id, source_id, key)).fetchone()
            if row and row["book_id"] != book_id:
                raise LibrarianError("RECONCILIATION_REQUIRED", "WeRead record moved between books")
            if row and row["state"] == "active" and row["accepted_sha256"] == digest:
                counts["unchanged"] += 1
                continue
            if row and row["state"] == "pending" and row["pending_sha256"] == digest:
                counts["pending"] += 1
                continue
            if row and row["state"] == "pending" and row["accepted_sha256"] == digest:
                lib.db.execute("UPDATE weread_native_records SET state='active',pending_sha256=NULL,pending_asset=NULL "
                               "WHERE owner_id=? AND source_id=? AND record_key=?",
                               (owner_id, source_id, key))
                counts["unchanged"] += 1
                continue
            asset = lib._save_object(raw, "application/json")
            if row is None:
                if lib.db.execute("SELECT 1 FROM records WHERE owner_id=? AND model='Work' AND id=?",
                                  (owner_id, work_id)).fetchone() is None:
                    work = {"object_type": "Work", "schema_version": "0.1.0", "id": work_id,
                            "owner_id": owner_id, "created_at": _now(), "title": book["title"],
                            "original_title": None,
                            "authors": [{"name": book["author"], "entity_id": None}]
                            if book.get("author") else [],
                            "identifiers": [{"scheme": "weread_book_id", "value": book_id}],
                            "revision": 1, "supersedes_revision": None}
                    lib._put(work)
                trace = {"object_type": "ReadingTrace", "schema_version": "0.1.0",
                         "id": trace_id, "owner_id": owner_id, "created_at": _now(),
                         "revision": 1, "supersedes_revision": None, "status": "active",
                         "context_state": "resolved", "work_id": work_id,
                         "edition_id": None, "book_instance_id": None, "session_id": None,
                         "medium": "weread", **fields,
                         "source": {"kind": "weread", "raw_payload": asset,
                                    "source_record_id": key}, "provenance": [asset],
                         "confidence": {"book_resolution": None, "page_number": None},
                         "marked_at": _time(item["record"]),
                         "attribution": {"mark_author": "unknown", "basis": "unknown"},
                         "intent_signals": [], "vocabulary_version": None,
                         "review": {"required": False, "state": "none", "reason": None}}
                validate("ReadingTrace", trace)
                lib._put(trace)
                _index_trace(lib, trace)
                lib._event(owner_id, "reading.trace.created", "reading_trace", trace_id, 1,
                           {"trace_id": trace_id, "revision": 1, "medium": "weread",
                            "book_instance_id": None}, source_id)
                lib.db.execute("INSERT INTO weread_native_records VALUES(?,?,?,?,?,?,?,?,?)",
                               (owner_id, source_id, key, book_id, trace_id, digest,
                                "active", None, None))
                counts["created"] += 1
                continue
            prior = lib.get(owner_id, "ReadingTrace", row["trace_id"])
            if row["state"] != "deleted" and not _matches_source(lib, prior):
                lib.db.execute("UPDATE weread_native_records SET state='pending',pending_sha256=?,pending_asset=? "
                               "WHERE owner_id=? AND source_id=? AND record_key=?",
                               (digest, _json(asset), owner_id, source_id, key))
                counts["pending"] += 1
                continue
            _revise(lib, owner_id, prior, fields={**fields, "marked_at": _time(item["record"])},
                    asset=asset, reason="WeRead source record changed", source_id=source_id)
            lib.db.execute("UPDATE weread_native_records SET accepted_sha256=?,state='active',"
                           "pending_sha256=NULL,pending_asset=NULL WHERE owner_id=? AND source_id=? AND record_key=?",
                           (digest, owner_id, source_id, key))
            counts["updated"] += 1
        for row in lib.db.execute(
                "SELECT record_key,trace_id,state FROM weread_native_records "
                "WHERE owner_id=? AND source_id=? AND book_id=?",
                (owner_id, source_id, book_id)).fetchall():
            if row["record_key"] in seen or row["state"] == "deleted":
                continue
            prior = lib.get(owner_id, "ReadingTrace", row["trace_id"])
            if row["state"] == "pending" or not _matches_source(lib, prior):
                raise LibrarianError("RECONCILIATION_REQUIRED", "corrected WeRead record was removed")
            _revise(lib, owner_id, prior, status="superseded",
                    reason="WeRead source record removed", source_id=source_id)
            lib.db.execute("UPDATE weread_native_records SET state='deleted',pending_sha256=NULL,pending_asset=NULL "
                           "WHERE owner_id=? AND source_id=? AND record_key=?",
                           (owner_id, source_id, row["record_key"]))
            counts["deleted"] += 1
    return counts


def pending_weread_reconciliation(lib: Library, owner_id: str) -> list[dict[str, str]]:
    if not owner_id:
        raise LibrarianError("VALIDATION_FAILED", "trusted owner required")
    rows = lib.db.execute(
        "SELECT source_id,record_key,trace_id FROM weread_native_records "
        "WHERE owner_id=? AND state='pending' ORDER BY source_id,record_key", (owner_id,))
    return [dict(row) for row in rows]


def reconcile_weread_record(lib: Library, owner_id: str, source_id: str,
                            record_key: str, expected_trace_revision: int, *,
                            accept_source: bool) -> dict[str, Any]:
    with lib.transaction():
        row = lib.db.execute(
            "SELECT * FROM weread_native_records WHERE owner_id=? AND source_id=? AND record_key=?",
            (owner_id, source_id, record_key)).fetchone()
        if row is None:
            raise LibrarianError("UNAUTHORIZED", "WeRead record not found for owner")
        if row["state"] != "pending" or not row["pending_asset"]:
            raise LibrarianError("INVALID_STATE_TRANSITION", "WeRead record has no pending edit")
        prior = lib.get(owner_id, "ReadingTrace", row["trace_id"])
        if prior["revision"] != expected_trace_revision:
            raise LibrarianError("REVISION_CONFLICT", "trace revision changed")
        asset = json.loads(row["pending_asset"])
        item = json.loads(lib._read_object(asset))
        record = item["record"]
        actual_key = f"{item['kind']}:{record['bookmarkId' if item['kind'] == 'bookmark' else 'reviewId']}"
        if item["book"].get("bookId") != row["book_id"] or actual_key != record_key:
            raise LibrarianError("VALIDATION_FAILED", "pending WeRead identity changed")
        revised = _revise(
            lib, owner_id, prior,
            fields={**_fields(item), "marked_at": _time(record)} if accept_source else None,
            asset=asset, reason=("WeRead source edit accepted" if accept_source
                                 else "WeRead source edit linked; user correction retained"),
            source_id=source_id)
        lib.db.execute(
            "UPDATE weread_native_records SET accepted_sha256=pending_sha256,state='active',"
            "pending_sha256=NULL,pending_asset=NULL "
            "WHERE owner_id=? AND source_id=? AND record_key=?",
            (owner_id, source_id, record_key))
        return revised


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync a WeRead book using its read-only Agent API")
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--owner", required=True, help="trusted local owner ID")
    parser.add_argument("--source-id", required=True, help="stable ID for this WeRead account")
    parser.add_argument("--book-id", required=True)
    parser.add_argument("--allow-empty-source", action="store_true")
    args = parser.parse_args()
    key = os.environ.get("LIBRARIAN_WEREAD_API_KEY", "")
    book, records = fetch_weread_book(key, args.book_id)
    with Library(args.root) as lib:
        counts = sync_weread_book(lib, args.owner, args.source_id, book, records,
                                  allow_empty_source=args.allow_empty_source)
    print(json.dumps(counts, sort_keys=True))


if __name__ == "__main__":
    main()
