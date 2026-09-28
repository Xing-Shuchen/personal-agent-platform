from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from agents.librarian.runtime.koodo_native import (
    BOOK_COLUMNS, NOTE_COLUMNS, pending_koodo_reconciliation,
    read_koodo_snapshot, reconcile_koodo_note, sync_koodo_sqlite,
)
from agents.librarian.runtime.pipeline import correct_trace, search
from agents.librarian.runtime.store import Library, LibrarianError


def _source_databases(root: Path) -> tuple[Path, Path]:
    books = root / "books.db"
    notes = root / "notes.db"
    with sqlite3.connect(books) as db:
        db.execute("CREATE TABLE books (key TEXT PRIMARY KEY," +
                   ",".join(f"{name} TEXT" for name in BOOK_COLUMNS[1:]) + ")")
        values = {name: "" for name in BOOK_COLUMNS}
        values.update(key="book-1", name="Synthetic Book", author="Synthetic Author",
                      format="EPUB")
        db.execute(f"INSERT INTO books VALUES({','.join('?' for _ in BOOK_COLUMNS)})",
                   tuple(values[name] for name in BOOK_COLUMNS))
    with sqlite3.connect(notes) as db:
        db.execute("CREATE TABLE notes (key TEXT PRIMARY KEY," +
                   ",".join(f"{name} TEXT" for name in NOTE_COLUMNS[1:]) + ")")
        for key, content in (("note-1", "First passage"), ("note-2", "Second passage")):
            values = {name: "" for name in NOTE_COLUMNS}
            values.update(key=key, bookKey="book-1", text=content,
                          chapter="Chapter One", chapterIndex="1",
                          cfi=json.dumps({"chapterHref": "chapter.xhtml", "xpath": "/p[1]"}),
                          date=json.dumps({"year": 2026, "month": 9, "day": 28}),
                          range=json.dumps({"characterRange": {}}), tag="[]")
            db.execute(f"INSERT INTO notes VALUES({','.join('?' for _ in NOTE_COLUMNS)})",
                       tuple(values[name] for name in NOTE_COLUMNS))
    return books, notes


def test_native_koodo_sync_replays_updates_deletes_and_reconciles_user_correction(tmp_path: Path):
    books, notes = _source_databases(tmp_path)
    assert len(read_koodo_snapshot(books, notes)) == 2
    with Library(tmp_path / "librarian") as lib:
        first = sync_koodo_sqlite(lib, "owner_a", "reader_1", books, notes)
        assert first == {"source_notes": 2, "created": 2, "updated": 0,
                         "deleted": 0, "unchanged": 0, "pending": 0}
        assert len(search(lib, "owner_a", "First")) == 1
        first_trace = search(lib, "owner_a", "First")[0]
        second_trace = search(lib, "owner_a", "Second")[0]
        assert first_trace["location"]["epub_cfi"] is None
        assert 'chapterHref' in first_trace["location"]["source_locator"]
        raw, mime = lib.read_trace_evidence("owner_a", first_trace["id"])
        assert mime == "application/json"
        assert json.loads(raw)["note"]["text"] == "First passage"
        assert sync_koodo_sqlite(lib, "owner_a", "reader_1", books, notes)["unchanged"] == 2
        assert len(lib.pending_events("owner_a")) == 2

        with sqlite3.connect(notes) as db:
            db.execute("UPDATE notes SET text='First passage revised' WHERE key='note-1'")
        changed = sync_koodo_sqlite(lib, "owner_a", "reader_1", books, notes)
        assert changed["updated"] == 1 and changed["unchanged"] == 1
        assert lib.get("owner_a", "ReadingTrace", first_trace["id"])["revision"] == 2
        assert search(lib, "owner_a", "First passage revised")[0]["id"] == first_trace["id"]

        corrected = correct_trace(lib, "owner_a", second_trace["id"], 1,
                                  printed_text="User checked second passage",
                                  reason="checked against book")
        with sqlite3.connect(notes) as db:
            db.execute("UPDATE notes SET text='Second passage revised' WHERE key='note-2'")
        conflict = sync_koodo_sqlite(lib, "owner_a", "reader_1", books, notes)
        assert conflict["pending"] == 1
        assert lib.get("owner_a", "ReadingTrace", second_trace["id"]) == corrected
        assert pending_koodo_reconciliation(lib, "owner_a") == [
            {"source_id": "reader_1", "note_key": "note-2", "trace_id": second_trace["id"]}]
        assert pending_koodo_reconciliation(lib, "owner_b") == []
        with pytest.raises(LibrarianError) as denied:
            reconcile_koodo_note(lib, "owner_b", "reader_1", "note-2", 2,
                                 accept_source=False)
        assert denied.value.code == "UNAUTHORIZED"
        retained = reconcile_koodo_note(lib, "owner_a", "reader_1", "note-2", 2,
                                        accept_source=False)
        assert retained["revision"] == 3
        assert retained["content"]["printed_text"]["text"] == "User checked second passage"
        assert json.loads(lib.read_trace_evidence("owner_a", second_trace["id"])[0])["note"]["text"] == "Second passage revised"
        assert pending_koodo_reconciliation(lib, "owner_a") == []

        with sqlite3.connect(notes) as db:
            db.execute("UPDATE notes SET text='Second passage final' WHERE key='note-2'")
        assert sync_koodo_sqlite(lib, "owner_a", "reader_1", books, notes)["pending"] == 1
        accepted = reconcile_koodo_note(lib, "owner_a", "reader_1", "note-2", 3,
                                        accept_source=True)
        assert accepted["revision"] == 4
        assert accepted["content"]["printed_text"]["text"] == "Second passage final"
        assert pending_koodo_reconciliation(lib, "owner_a") == []

        with sqlite3.connect(notes) as db:
            db.execute("DELETE FROM notes WHERE key='note-1'")
        removed = sync_koodo_sqlite(lib, "owner_a", "reader_1", books, notes)
        assert removed["deleted"] == 1
        assert lib.get("owner_a", "ReadingTrace", first_trace["id"])["status"] == "superseded"
        assert search(lib, "owner_a", "First passage revised") == []
        assert sync_koodo_sqlite(lib, "owner_a", "reader_1", books, notes)["deleted"] == 0

        with sqlite3.connect(notes) as db:
            db.execute("DELETE FROM notes WHERE key='note-2'")
        with pytest.raises(LibrarianError) as empty:
            sync_koodo_sqlite(lib, "owner_a", "reader_1", books, notes)
        assert empty.value.code == "RECONCILIATION_REQUIRED"
        confirmed = sync_koodo_sqlite(lib, "owner_a", "reader_1", books, notes,
                                      allow_empty_source=True)
        assert confirmed["deleted"] == 1
        assert lib.get("owner_a", "ReadingTrace", second_trace["id"])["status"] == "superseded"


def test_native_koodo_rejects_missing_book_before_writing(tmp_path: Path):
    books, notes = _source_databases(tmp_path)
    with sqlite3.connect(notes) as db:
        db.execute("UPDATE notes SET bookKey='missing' WHERE key='note-2'")
    with Library(tmp_path / "librarian") as lib:
        with pytest.raises(LibrarianError) as error:
            sync_koodo_sqlite(lib, "owner_a", "reader_1", books, notes)
        assert error.value.code == "UPSTREAM_FORMAT_UNSUPPORTED"
        assert lib.db.execute("SELECT COUNT(*) FROM records").fetchone()[0] == 0
