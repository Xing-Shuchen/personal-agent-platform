"""Regression tests for Librarian defects confirmed in the 2026-10 audit.

Pins: digital (weread/koodo) trace lookup by ``trace_id`` must answer instead
of crashing the whole search bridge; a user-corrected Koodo note must not be
silently retired when its source record disappears (mirrors the WeRead guard);
and the discard bridge must see a *failed* ProcessingRun as "entered
extraction" (the old guard queried a model name that does not exist).
"""

from __future__ import annotations

import io
import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from PIL import Image

from agents.librarian.runtime.digital import ingest_export
from agents.librarian.runtime.gateway_discard_captures import discard_recent
from agents.librarian.runtime.gateway_search import search_inbound
from agents.librarian.runtime.koodo_native import (
    BOOK_COLUMNS, NOTE_COLUMNS, sync_koodo_sqlite,
)
from agents.librarian.runtime.pipeline import correct_trace, process_capture, search
from agents.librarian.runtime.store import Library, LibrarianError


# ---------------------------------------------------------------------------
# H2: digital trace lookup by id


WEREAD_EXPORT = """---
bookId: synthetic-book
---
> [!abstract] Synthetic Work
# Synthetic Work
# 高亮划线
## Chapter One
> 📌 A synthetic highlighted sentence.
> ⏱ 2026-01-02 12:00:00 ^synthetic-1
""".encode()


def test_digital_trace_lookup_by_id_returns_the_trace(tmp_path):
    with Library(tmp_path) as lib:
        trace = ingest_export(lib, "owner_a", "weread", "synthetic.md", WEREAD_EXPORT)[0]
        assert trace["medium"] == "weread"
        assert "observation_id" not in trace["source"]  # digital source shape
        # Before the fix this raised KeyError('observation_id') and the bridge
        # answered a retryable BRIDGE_FAILED for a perfectly healthy trace.
        result = search_inbound(lib, {"owner_id": "owner_a", "trace_id": trace["id"],
                                      "query": ""})
        assert result["trace_id"] == trace["id"]
        assert result["alignment"] is None
        assert result["location_kind"] == "digital"
        assert result["chapter"] == "Chapter One"
        assert result["page"] is None
        assert result["printed_text"]["text"] == "A synthetic highlighted sentence."


# ---------------------------------------------------------------------------
# M3: corrected Koodo note deletion requires reconciliation


def _koodo_sources(root: Path) -> tuple[Path, Path]:
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
        values = {name: "" for name in NOTE_COLUMNS}
        values.update(key="note-1", bookKey="book-1", text="A synthetic passage",
                      chapter="Chapter One", chapterIndex="1",
                      cfi=json.dumps({"chapterHref": "chapter.xhtml", "xpath": "/p[1]"}),
                      date=json.dumps({"year": 2026, "month": 9, "day": 28}),
                      range=json.dumps({"characterRange": {}}), tag="[]")
        db.execute(f"INSERT INTO notes VALUES({','.join('?' for _ in NOTE_COLUMNS)})",
                   tuple(values[name] for name in NOTE_COLUMNS))
    return books, notes


def test_koodo_refuses_to_retire_user_corrected_trace(tmp_path):
    books, notes = _koodo_sources(tmp_path)
    with Library(tmp_path / "librarian") as lib:
        assert sync_koodo_sqlite(lib, "owner_a", "reader_1", books, notes)["created"] == 1
        review = search(lib, "owner_a", "synthetic passage")[0]
        correct_trace(lib, "owner_a", review["id"], 1,
                      printed_text="User corrected passage", reason="checked")
        with sqlite3.connect(notes) as db:
            db.execute("DELETE FROM notes WHERE key='note-1'")
        # Mirrors the WeRead guard: the correction must not vanish silently.
        with pytest.raises(LibrarianError) as error:
            sync_koodo_sqlite(lib, "owner_a", "reader_1", books, notes,
                              allow_empty_source=True)
        assert error.value.code == "RECONCILIATION_REQUIRED"
        assert lib.get("owner_a", "ReadingTrace", review["id"])["status"] == "active"
        assert search(lib, "owner_a", "User corrected passage")


# ---------------------------------------------------------------------------
# M4: discard guard sees failed extraction runs


def _photo() -> bytes:
    stream = io.BytesIO()
    Image.new("RGB", (60, 80), "white").save(stream, format="PNG")
    return stream.getvalue()


def test_discard_refuses_photos_with_a_failed_processing_run(tmp_path):
    with Library(tmp_path) as lib:
        receipt = lib.ingest(
            "owner_a", transport="gateway", account_id="account", conversation_id="chat",
            source_event_id="message-1", idempotency_key="command-1",
            attachments=[{"source_item_id": "image-1", "mime_type": "image/png",
                          "data": _photo()}])
        capture_id = receipt["capture_ids"][0]

        def broken_extractor(_original):
            raise RuntimeError("extractor exploded")

        with pytest.raises(LibrarianError) as failed:
            process_capture(lib, "owner_a", capture_id, broken_extractor)
        assert failed.value.code == "EXTRACTOR_UNAVAILABLE"
        # The failed run is stored as a ProcessingRun without extractor_attempts;
        # the old guard queried a nonexistent 'ExtractionRun' model and let the
        # photo be discarded as "unprocessed".
        assert lib.db.execute(
            "SELECT COUNT(*) FROM records WHERE owner_id='owner_a' "
            "AND model='ProcessingRun' AND current=1").fetchone()[0] == 1
        assert lib.db.execute(
            "SELECT COUNT(*) FROM extractor_attempts WHERE owner_id='owner_a' "
            "AND capture_id=?", (capture_id,)).fetchone()[0] == 0

        cutoff = (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()
        with pytest.raises(LibrarianError) as refused:
            discard_recent(lib, {
                "owner_id": "owner_a",
                "source": {"transport": "gateway", "account_id": "account",
                           "conversation_id": "chat", "source_event_id": "discard-1"},
                "count": 1,
                "before": cutoff,
            })
        assert refused.value.code == "CONTEXT_CONFLICT"
