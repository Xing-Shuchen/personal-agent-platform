from __future__ import annotations

from pathlib import Path

import pytest

from agents.librarian.runtime.digital import ingest_export
from agents.librarian.runtime.events import consume_event, project_trace_event, publish_pending
from agents.librarian.runtime.pipeline import correct_trace
from agents.librarian.runtime.store import Library, LibrarianError
from agents.librarian.runtime.store import validate


EXPORT = """---
bookId: "book-42"
---
> [!abstract] Synthetic Title
# 高亮划线
## Chapter One
> 📌 Weber and Parsons
> ⏱ 2024-01-01 12:00:00 ^book-42-1-10-20
""".encode()


def test_outbox_failure_retries_same_event_id_after_reopen(tmp_path: Path):
    with Library(tmp_path) as lib:
        lib.start_session("owner_a")
        event_id = lib.pending_events("owner_a")[0]["event_id"]
        def fail(_event):
            raise RuntimeError("publisher crashed")
        with pytest.raises(RuntimeError, match="publisher crashed"):
            publish_pending(lib, "owner_a", fail)
        assert lib.pending_events("owner_a")[0]["event_id"] == event_id
    with Library(tmp_path) as reopened:
        sent = []
        assert publish_pending(reopened, "owner_a", sent.append) == 1
        assert [event["event_id"] for event in sent] == [event_id]
        assert publish_pending(reopened, "owner_a", sent.append) == 0
        assert reopened.pending_events("owner_a") == []


def test_late_old_trace_event_does_not_roll_back_current_index(tmp_path: Path):
    with Library(tmp_path) as lib:
        trace = ingest_export(lib, "owner_a", "weread", "export.md", EXPORT)[0]
        corrected = correct_trace(lib, "owner_a", trace["id"], 1,
                                  printed_text="Corrected Parsons", reason="user correction")
        events = [event for event in lib.pending_events("owner_a")
                  if event["event"].startswith("reading.trace.")]
        assert [event["aggregate"]["revision"] for event in events] == [1, 2]
        lib.db.execute("DELETE FROM trace_index")
        lib.db.commit()
        handler = lambda event: project_trace_event(lib, event)
        assert consume_event(lib, "search-v1", events[1], trusted_owner_id="owner_a",
                             handler=handler)
        assert consume_event(lib, "search-v1", events[0], trusted_owner_id="owner_a",
                             handler=handler)
        assert not consume_event(lib, "search-v1", events[0], trusted_owner_id="owner_a",
                                 handler=handler)
        indexed = lib.db.execute("SELECT revision,printed_text FROM trace_index WHERE trace_id=?",
                                 (trace["id"],)).fetchone()
        assert indexed["revision"] == corrected["revision"] == 2
        assert indexed["printed_text"] == "Corrected Parsons"
        with pytest.raises(LibrarianError) as error:
            consume_event(lib, "search-v1", events[0], trusted_owner_id="owner_b",
                          handler=handler)
        assert error.value.code == "UNAUTHORIZED"


def test_failed_consumer_handler_does_not_advance_cursor(tmp_path: Path):
    with Library(tmp_path) as lib:
        event = lib.start_session("owner_a")
        message = lib.pending_events("owner_a")[0]
        def fail(_event):
            raise RuntimeError("projection failed")
        with pytest.raises(RuntimeError):
            consume_event(lib, "projection", message, trusted_owner_id="owner_a", handler=fail)
        assert lib.db.execute("SELECT COUNT(*) FROM consumer_events").fetchone()[0] == 0
        assert consume_event(lib, "projection", message, trusted_owner_id="owner_a",
                             handler=lambda _: None)
        wrong = {**message, "aggregate": {**message["aggregate"], "id": "another-session"}}
        with pytest.raises(LibrarianError, match="aggregate and payload disagree"):
            validate("Event", wrong)


def test_trace_index_consumer_failure_retries_same_event_after_reopen(tmp_path: Path,
                                                                     monkeypatch) -> None:
    from agents.librarian.runtime import events

    with Library(tmp_path) as lib:
        trace = ingest_export(lib, "owner_a", "weread", "export.md", EXPORT)[0]
        event = next(item for item in lib.pending_events("owner_a")
                     if item["event"] == "reading.trace.created")
        lib.db.execute("DELETE FROM trace_index WHERE owner_id=? AND trace_id=?",
                       ("owner_a", trace["id"]))
        lib.db.commit()
        real_index = events._index_trace
        monkeypatch.setattr(events, "_index_trace", lambda *_: (_ for _ in ()).throw(
            RuntimeError("index unavailable")))
        with pytest.raises(RuntimeError, match="index unavailable"):
            consume_event(lib, "search-v2", event, trusted_owner_id="owner_a",
                          handler=lambda item: project_trace_event(lib, item))
        assert lib.db.execute("SELECT COUNT(*) FROM consumer_events WHERE event_id=?",
                              (event["event_id"],)).fetchone()[0] == 0
    monkeypatch.setattr(events, "_index_trace", real_index)
    with Library(tmp_path) as lib:
        assert consume_event(lib, "search-v2", event, trusted_owner_id="owner_a",
                             handler=lambda item: project_trace_event(lib, item))
        assert not consume_event(lib, "search-v2", event, trusted_owner_id="owner_a",
                                 handler=lambda item: project_trace_event(lib, item))
        indexed = lib.db.execute("SELECT revision FROM trace_index WHERE trace_id=?",
                                 (trace["id"],)).fetchone()
        assert indexed["revision"] == trace["revision"]
