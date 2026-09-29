"""Resolve an owner's catalogued EPUB for trusted Feishu file delivery."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from .gateway_errors import write_error
from .store import Library, LibrarianError

MAX_INPUT_BYTES = 8192
MAX_EPUB_BYTES = 30 * 1024 * 1024


def source_book_for_owner(lib: Library, owner: str, book: str) -> dict:
    if (not isinstance(owner, str) or not owner or not isinstance(book, str) or
            not book.strip() or len(book) > 200):
        raise LibrarianError("VALIDATION_FAILED", "owner and book title required")
    wanted = book.strip().casefold()
    works = [json.loads(row[0]) for row in lib.db.execute(
        "SELECT body FROM records WHERE owner_id=? AND model='Work' AND current=1",
        (owner,))]
    matches = [work for work in works if work["title"].strip().casefold() == wanted]
    if not matches:
        raise LibrarianError("OBJECT_NOT_FOUND", "catalogued book not found")
    if len(matches) != 1:
        raise LibrarianError("CONTEXT_CONFLICT", "book title is ambiguous")
    work = matches[0]
    editions = [json.loads(row[0]) for row in lib.db.execute(
        "SELECT body FROM records WHERE owner_id=? AND model='Edition' AND current=1 "
        "AND json_extract(body,'$.work_id')=?", (owner, work["id"]))]
    directory = (lib.root / "source-books").resolve()
    found = []
    for edition in editions:
        isbn = edition["isbn"]["isbn13"]
        if not isinstance(isbn, str) or not re.fullmatch(r"\d{13}", isbn):
            continue
        path = (directory / f"{isbn}.epub").resolve()
        if path.parent != directory or not path.is_file():
            continue
        size = path.stat().st_size
        if not 0 < size <= MAX_EPUB_BYTES:
            raise LibrarianError("VALIDATION_FAILED", "source book exceeds delivery limit")
        found.append((isbn, path, size))
    if not found:
        raise LibrarianError("OBJECT_NOT_FOUND", "catalogued EPUB not available")
    if len(found) != 1:
        raise LibrarianError("CONTEXT_CONFLICT", "multiple EPUB editions available")
    isbn, path, size = found[0]
    return {"book_title": work["title"], "isbn13": isbn,
            "media_path": str(path), "byte_size": size}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    raw = sys.stdin.buffer.read(MAX_INPUT_BYTES + 1)
    if len(raw) > MAX_INPUT_BYTES:
        return write_error(LibrarianError("VALIDATION_FAILED", "input too large"),
                           "gateway.source_book")
    try:
        message = json.loads(raw)
        if not isinstance(message, dict):
            raise LibrarianError("VALIDATION_FAILED", "request must be an object")
        if not (args.root / "librarian.sqlite").is_file():
            raise LibrarianError("OBJECT_STORE_UNAVAILABLE", "Librarian store unavailable")
        with Library(args.root) as lib:
            result = source_book_for_owner(lib, message.get("owner_id"), message.get("book"))
    except Exception as error:
        return write_error(error, "gateway.source_book")
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
