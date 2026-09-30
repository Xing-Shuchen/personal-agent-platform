"""Store a trusted inbound EPUB against the selected physical reading session."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile

from .gateway_errors import write_error
from .store import Library, LibrarianError

MAX_INPUT_BYTES = 8192
MAX_EPUB_BYTES = 30 * 1024 * 1024
MAX_UNPACKED_BYTES = 150 * 1024 * 1024


def store_inbound_epub(lib: Library, message: dict) -> dict:
    owner, actor, source, raw_path = (message.get(key) for key in
                                      ("owner_id", "actor_id", "source", "data_path"))
    if not isinstance(owner, str) or not owner or not isinstance(actor, str) or not actor:
        raise LibrarianError("VALIDATION_FAILED", "trusted owner and actor required")
    keys = ("transport", "account_id", "conversation_id", "source_event_id")
    if not isinstance(source, dict) or any(not isinstance(source.get(key), str) or
                                            not source[key] for key in keys):
        raise LibrarianError("VALIDATION_FAILED", "stable inbound source required")
    selected = lib.db.execute(
        "SELECT session_id FROM session_scope WHERE owner_id=? AND transport=? "
        "AND account_id=? AND conversation_id=? AND selected=1",
        (owner, source["transport"], source["account_id"],
         source["conversation_id"])).fetchall()
    if len(selected) != 1:
        raise LibrarianError("CONTEXT_CONFLICT", "select one physical reading session first")
    session = lib.get(owner, "ReadingSession", selected[0]["session_id"])
    if session["medium"] != "physical" or not session["edition_id"]:
        raise LibrarianError("CONTEXT_CONFLICT", "selected session has no physical edition")
    edition = lib.get(owner, "Edition", session["edition_id"])
    isbn = edition["isbn"]["isbn13"]
    if not isbn:
        raise LibrarianError("NEEDS_BOOK_RESOLUTION", "selected edition has no ISBN")
    inbox_title = None
    if raw_path is None:
        inbox = message.get("inbox_root")
        if not isinstance(inbox, str) or not Path(inbox).is_absolute():
            raise LibrarianError("VALIDATION_FAILED", "configured EPUB inbox required")
        directory = Path(inbox)
        if directory.is_symlink() or not directory.is_dir():
            raise LibrarianError("VALIDATION_FAILED", "EPUB inbox unavailable")
        work = lib.get(owner, "Work", session["work_id"])
        inbox_title = work["title"]
        matches = [candidate for candidate in directory.glob("*.epub")
                   if not candidate.is_symlink() and
                   (work["title"].casefold() in candidate.name.casefold() or
                    isbn in candidate.name)]
        if len(matches) != 1:
            raise LibrarianError("OBJECT_NOT_FOUND" if not matches else "CONTEXT_CONFLICT",
                                 "one matching EPUB required in configured inbox")
        path = matches[0]
    elif isinstance(raw_path, str) and Path(raw_path).is_absolute():
        path = Path(raw_path)
    else:
        raise LibrarianError("VALIDATION_FAILED", "staged EPUB path required")
    try:
        if path.is_symlink() or not path.is_file() or not 0 < path.stat().st_size <= MAX_EPUB_BYTES:
            raise LibrarianError("VALIDATION_FAILED", "EPUB size or staging path invalid")
        data = path.read_bytes()
        with ZipFile(path) as archive:
            members = archive.infolist()
            opfs = [item.filename for item in members
                    if item.filename.lower().endswith(".opf")]
            if (not members or sum(item.file_size for item in members) > MAX_UNPACKED_BYTES or
                    not opfs):
                raise LibrarianError("VALIDATION_FAILED", "invalid EPUB package")
            if archive.read("mimetype").strip() != b"application/epub+zip" or archive.testzip():
                raise LibrarianError("VALIDATION_FAILED", "invalid EPUB package")
            if inbox_title:
                metadata = ElementTree.fromstring(archive.read(opfs[0]))
                titles = [element.text.strip() for element in metadata.iter()
                          if element.tag.split("}")[-1] == "title" and element.text]
                if not any(inbox_title.casefold() in title.casefold() for title in titles):
                    raise LibrarianError("CONTEXT_CONFLICT", "EPUB title conflicts with selected book")
    except (OSError, BadZipFile, KeyError, ElementTree.ParseError) as error:
        raise LibrarianError("VALIDATION_FAILED", "invalid or unavailable EPUB") from error
    digest = hashlib.sha256(data).hexdigest()
    directory = lib.root / "source-books"
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    target = directory / f"{isbn}.epub"
    if target.exists():
        if hashlib.sha256(target.read_bytes()).hexdigest() != digest:
            raise LibrarianError("CONTEXT_CONFLICT", "a different EPUB is already stored for ISBN")
        return {"status": "unchanged", "isbn13": isbn, "byte_size": len(data),
                "sha256": digest, "source_event_id": source["source_event_id"]}
    fd, temporary = tempfile.mkstemp(prefix=f".{isbn}.", suffix=".tmp", dir=directory)
    try:
        with os.fdopen(fd, "wb") as output:
            output.write(data)
            output.flush()
            os.fsync(output.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, target)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return {"status": "stored", "isbn13": isbn, "byte_size": len(data),
            "sha256": digest, "source_event_id": source["source_event_id"]}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    raw = sys.stdin.buffer.read(MAX_INPUT_BYTES + 1)
    if len(raw) > MAX_INPUT_BYTES:
        return write_error(LibrarianError("VALIDATION_FAILED", "input too large"),
                           "gateway.source_book_intake")
    try:
        message = json.loads(raw)
        if not isinstance(message, dict):
            raise LibrarianError("VALIDATION_FAILED", "request must be an object")
        with Library(args.root) as lib:
            result = store_inbound_epub(lib, message)
    except Exception as error:
        return write_error(error, "gateway.source_book_intake")
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
