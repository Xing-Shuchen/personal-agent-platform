"""Trusted local read-only search bridge for the mapped OpenClaw sender.

This stdin protocol is not an authentication boundary. The plugin derives the
owner from runtime-supplied sender context before invoking this process.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .pipeline import search_response
from .gateway_review import pending_extractions
from .store import Library, LibrarianError
from .gateway_errors import write_error

MAX_INPUT_BYTES = 8192


def _title_key(value: str) -> str:
    return "".join(char.casefold() for char in value if char.isalnum())


def search_inbound(lib: Library, message: dict) -> dict:
    owner = message.get("owner_id")
    trace_id = message.get("trace_id")
    query = message.get("query", "")
    book = message.get("book")
    page = message.get("page")
    limit = message.get("limit", 10)
    if (not isinstance(owner, str) or not owner or not isinstance(query, str)
            or len(query) > 256 or
            (trace_id is not None and (not isinstance(trace_id, str) or
                                       not trace_id.startswith("rt_") or
                                       len(trace_id) > 80 or query or book or page)) or
            (book is not None and (not isinstance(book, str) or not book.strip() or len(book) > 200)) or
            (page is not None and (isinstance(page, bool) or not isinstance(page, int)
                                   or not 1 <= page <= 9999)) or
            not (trace_id or query.strip() or book or page) or isinstance(limit, bool)
            or not isinstance(limit, int) or not 1 <= limit <= 20):
        raise LibrarianError("VALIDATION_FAILED", "trusted owner and bounded search fields required")
    if trace_id:
        trace = lib.get(owner, "ReadingTrace", trace_id)
        if trace["status"] != "active":
            raise LibrarianError("OBJECT_NOT_FOUND", "trace is not active")
        work = lib.get(owner, "Work", trace["work_id"]) if trace["work_id"] else None
        alignment = None
        observation = lib.get(owner, "PageObservation", trace["source"]["observation_id"])
        try:
            report = json.loads(lib._read_object(observation["raw_output_asset"]))
            ids = trace["source"]["detection_ids"]
            indexes = {int(identifier.split("_")[1]) for identifier in ids
                       if identifier.startswith("bookscan_") and
                       identifier.split("_")[1].isdigit()}
            if len(indexes) == 1:
                group = report["groups"][next(iter(indexes))]
                candidate = group.get("epub_candidate") or {}
                alignment = {"match_status": group.get("match_status"),
                             "text_basis": group.get("text_basis"),
                             "review_reasons": group.get("review_reasons", []),
                             "epub_expanded_text": group.get("epub_expanded_text"),
                             "similarity": candidate.get("similarity"),
                             "query_coverage": candidate.get("query_coverage"),
                             "runner_up_margin": candidate.get("runner_up_margin")}
        except (KeyError, IndexError, TypeError, ValueError, UnicodeDecodeError):
            pass
        return {"trace_id": trace_id, "revision": trace["revision"],
                "book_title": work["title"] if work else None,
                "page": trace["location"]["page"],
                "printed_text": trace["content"]["printed_text"],
                "annotation": trace["content"]["annotation"],
                "review": trace["review"], "alignment": alignment}
    work_id = None
    missing_book = False
    if book:
        rows = lib.db.execute("SELECT body FROM records WHERE owner_id=? AND model='Work' AND current=1",
                              (owner,)).fetchall()
        works = [json.loads(row["body"]) for row in rows]
        wanted = _title_key(book)
        matches = [work for work in works if _title_key(work["title"]) == wanted]
        if not matches and len(wanted) >= 3:
            matches = [work for work in works if wanted in _title_key(work["title"])]
        if len(matches) > 1:
            raise LibrarianError("CONTEXT_CONFLICT", "book title matches multiple works")
        work_id = matches[0]["id"] if matches else None
        missing_book = not matches
    request = {"owner_id": owner, "query": query.strip() or (book if missing_book else ""),
               "filters": {"work_id": None, "edition_id": None,
                           "book_instance_id": None, "session_id": None,
                           "medium": None, "trace_types": [],
                           "include_unresolved": False,
                           "page_number": page},
               "limit": limit, "cursor": None}
    request["filters"]["work_id"] = work_id
    result = search_response(lib, request, trusted_owner_id=owner)
    if missing_book:
        result["hits"] = []
        result["next_cursor"] = None
    if book and page and not missing_book:
        pending = pending_extractions(lib, owner)["pending"]
        result["pending_evidence"] = []
        for item in pending:
            if _title_key(item.get("book_title") or "") != _title_key(book):
                continue
            if str(page) not in item.get("pages", []):
                continue
            detail = pending_extractions(lib, owner, item["capture_id"])
            candidates = [{"candidate_index": index, "candidate_id": candidate["candidate_id"],
                           "printed_text": candidate["printed_text"],
                           "page": candidate["page"]}
                          for index, candidate in enumerate(detail["proposed"])
                          if candidate["page"] and candidate["page"]["number"] == page]
            if candidates:
                result["pending_evidence"].append({"capture_id": item["capture_id"],
                                                   "candidates": candidates,
                                                   "status": "pending_review"})
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Trusted Librarian owner-scoped search")
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    raw = sys.stdin.buffer.read(MAX_INPUT_BYTES + 1)
    if len(raw) > MAX_INPUT_BYTES:
        return write_error(LibrarianError("VALIDATION_FAILED", "input too large"), "gateway.search")
    try:
        message = json.loads(raw)
        if not isinstance(message, dict):
            raise LibrarianError("VALIDATION_FAILED", "message must be an object")
        if not (args.root / "librarian.sqlite").is_file():
            raise LibrarianError("OBJECT_STORE_UNAVAILABLE", "Librarian store is unavailable")
        with Library(args.root) as lib:
            result = search_inbound(lib, message)
    except Exception as error:
        return write_error(error, "gateway.search")
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
