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


def search_inbound(lib: Library, message: dict) -> dict:
    owner = message.get("owner_id")
    query = message.get("query")
    limit = message.get("limit", 10)
    if (not isinstance(owner, str) or not owner or not isinstance(query, str)
            or not query.strip() or len(query) > 256 or isinstance(limit, bool)
            or not isinstance(limit, int) or not 1 <= limit <= 20):
        raise LibrarianError("VALIDATION_FAILED", "trusted owner, query and bounded limit required")
    request = {"owner_id": owner, "query": query,
               "filters": {"work_id": None, "edition_id": None,
                           "book_instance_id": None, "session_id": None,
                           "medium": None, "trace_types": [],
                           "include_unresolved": False},
               "limit": limit, "cursor": None}
    return search_response(lib, request, trusted_owner_id=owner)


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
