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
from .store import Library, LibrarianError

MAX_INPUT_BYTES = 8192


def _title_key(value: str) -> str:
    return "".join(char.casefold() for char in value if char.isalnum())


def search_inbound(lib: Library, message: dict) -> dict:
    owner = message.get("owner_id")
    query = message.get("query", "")
    book = message.get("book")
    page = message.get("page")
    limit = message.get("limit", 10)
    if (not isinstance(owner, str) or not owner or not isinstance(query, str)
            or len(query) > 256 or
            (book is not None and (not isinstance(book, str) or not book.strip() or len(book) > 200)) or
            (page is not None and (isinstance(page, bool) or not isinstance(page, int)
                                   or not 1 <= page <= 9999)) or
            not (query.strip() or book or page) or isinstance(limit, bool)
            or not isinstance(limit, int) or not 1 <= limit <= 20):
        raise LibrarianError("VALIDATION_FAILED", "trusted owner and bounded search fields required")
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
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Trusted Librarian owner-scoped search")
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    raw = sys.stdin.buffer.read(MAX_INPUT_BYTES + 1)
    if len(raw) > MAX_INPUT_BYTES:
        print(json.dumps({"error": {"code": "VALIDATION_FAILED"}}))
        return 2
    try:
        message = json.loads(raw)
        if not isinstance(message, dict):
            raise LibrarianError("VALIDATION_FAILED", "message must be an object")
        if not (args.root / "librarian.sqlite").is_file():
            raise LibrarianError("OBJECT_STORE_UNAVAILABLE", "Librarian store is unavailable")
        with Library(args.root) as lib:
            result = search_inbound(lib, message)
    except (json.JSONDecodeError, LibrarianError) as error:
        code = error.code if isinstance(error, LibrarianError) else "VALIDATION_FAILED"
        print(json.dumps({"error": {"code": code}}))
        return 2
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
