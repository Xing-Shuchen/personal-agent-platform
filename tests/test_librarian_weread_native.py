from __future__ import annotations

import copy
import json

import pytest

from agents.librarian.runtime.pipeline import correct_trace, search
from agents.librarian.runtime.store import Library, LibrarianError
from agents.librarian.runtime.weread_native import (
    fetch_weread_book, pending_weread_reconciliation, reconcile_weread_record,
    sync_weread_book,
)


BOOK = {"bookId": "book-1", "title": "Synthetic Book", "author": "Synthetic Author"}


def _items():
    return [
        {"kind": "bookmark", "book": BOOK, "chapter": "One",
         "record": {"bookId": "book-1", "bookmarkId": "mark-1", "markText": "First passage",
                    "chapterIdx": 1, "chapterUid": 10, "range": "1-10", "createTime": 1700000000}},
        {"kind": "review", "book": BOOK, "chapter": "One",
         "record": {"bookId": "book-1", "reviewId": "review-1", "abstract": "Second passage",
                    "content": "My note", "chapterIdx": 1, "chapterUid": 10,
                    "range": "20-30", "createTime": 1700000010}},
    ]


def test_weread_source_commit_survives_index_failure(tmp_path, monkeypatch) -> None:
    from agents.librarian.runtime import pipeline

    real_index = pipeline._index_trace
    monkeypatch.setattr(pipeline, "_index_trace", lambda *_: (_ for _ in ()).throw(
        RuntimeError("index unavailable")))
    with Library(tmp_path) as lib:
        assert sync_weread_book(lib, "owner_a", "reader_1", BOOK, _items())["created"] == 2
        assert lib.db.execute("SELECT COUNT(*) FROM records WHERE model='ReadingTrace'").fetchone()[0] == 2
        assert lib.db.execute("SELECT COUNT(*) FROM trace_index").fetchone()[0] == 0
    monkeypatch.setattr(pipeline, "_index_trace", real_index)
    with Library(tmp_path) as lib:
        assert sync_weread_book(lib, "owner_a", "reader_1", BOOK, _items())["unchanged"] == 2
        assert len(search(lib, "owner_a", "First passage")) == 1


def test_weread_native_replay_update_reconcile_and_delete(tmp_path):
    items = _items()
    with Library(tmp_path) as lib:
        first = sync_weread_book(lib, "owner_a", "reader_1", BOOK, items)
        assert first["created"] == 2
        mark = search(lib, "owner_a", "First passage")[0]
        review = search(lib, "owner_a", "My note")[0]
        assert review["trace_types"] == ["highlight", "inline_note"]
        assert mark["marked_at"]["value"] == "2023-11-14T22:13:20Z"
        raw, mime = lib.read_trace_evidence("owner_a", review["id"])
        assert mime == "application/json" and json.loads(raw) == items[1]
        assert sync_weread_book(lib, "owner_a", "reader_1", BOOK, items)["unchanged"] == 2
        assert search(lib, "owner_b", "First passage") == []

        changed = copy.deepcopy(items)
        changed[0]["record"]["markText"] = "First passage revised"
        assert sync_weread_book(lib, "owner_a", "reader_1", BOOK, changed)["updated"] == 1
        assert search(lib, "owner_a", "First passage revised")[0]["id"] == mark["id"]

        corrected = correct_trace(lib, "owner_a", review["id"], 1,
                                  printed_text="Verified second passage", reason="checked")
        changed[1]["record"]["content"] = "New source note"
        assert sync_weread_book(lib, "owner_a", "reader_1", BOOK, changed)["pending"] == 1
        assert lib.get("owner_a", "ReadingTrace", review["id"]) == corrected
        pending = pending_weread_reconciliation(lib, "owner_a")
        assert len(pending) == 1 and pending_weread_reconciliation(lib, "owner_b") == []
        with pytest.raises(LibrarianError) as denied:
            reconcile_weread_record(lib, "owner_b", "reader_1", pending[0]["record_key"], 2,
                                    accept_source=True)
        assert denied.value.code == "UNAUTHORIZED"
        retained = reconcile_weread_record(lib, "owner_a", "reader_1",
                                           pending[0]["record_key"], 2, accept_source=False)
        assert retained["content"]["printed_text"]["text"] == "Verified second passage"
        assert json.loads(lib.read_trace_evidence("owner_a", review["id"])[0])["record"]["content"] == "New source note"

        changed[1]["record"]["content"] = "Later source note"
        assert sync_weread_book(lib, "owner_a", "reader_1", BOOK, changed)["pending"] == 1
        accepted = reconcile_weread_record(lib, "owner_a", "reader_1",
                                           pending[0]["record_key"], 3, accept_source=True)
        assert accepted["content"]["annotation"]["text"] == "Later source note"
        assert pending_weread_reconciliation(lib, "owner_a") == []

        one = changed[1:]
        assert sync_weread_book(lib, "owner_a", "reader_1", BOOK, one)["deleted"] == 1
        assert lib.get("owner_a", "ReadingTrace", mark["id"])["status"] == "superseded"
        with pytest.raises(LibrarianError) as empty:
            sync_weread_book(lib, "owner_a", "reader_1", BOOK, [])
        assert empty.value.code == "RECONCILIATION_REQUIRED"


def test_weread_native_rejects_partial_or_duplicate_source_before_writing(tmp_path):
    with Library(tmp_path) as lib:
        with pytest.raises(LibrarianError) as duplicate:
            sync_weread_book(lib, "owner_a", "reader_1", BOOK, _items() + _items()[:1])
        assert duplicate.value.code == "UPSTREAM_FORMAT_UNSUPPORTED"
        assert lib.db.execute("SELECT COUNT(*) FROM records").fetchone()[0] == 0


def test_weread_source_cannot_be_reassigned_to_another_owner(tmp_path):
    with Library(tmp_path) as lib:
        sync_weread_book(lib, "owner_a", "reader_1", BOOK, _items())
        with pytest.raises(LibrarianError) as denied:
            sync_weread_book(lib, "owner_b", "reader_1", BOOK, _items())
        assert denied.value.code == "UNAUTHORIZED"
        assert search(lib, "owner_b", "First passage") == []
        assert lib.db.execute("SELECT COUNT(*) FROM weread_native_records "
                              "WHERE owner_id='owner_b'").fetchone()[0] == 0


def test_weread_gateway_paginates_and_rejects_stalled_cursor(monkeypatch):
    from agents.librarian.runtime import weread_native

    calls = []

    def fake_call(_key, endpoint, **params):
        calls.append((endpoint, params))
        if endpoint == "/book/bookmarklist":
            return {"book": BOOK, "chapters": [{"chapterUid": 10, "title": "One"}],
                    "updated": [_items()[0]["record"]], "removed": []}
        if params["synckey"] == 0:
            return {"reviews": [{"reviewId": "review-1", "review": _items()[1]["record"]}],
                    "hasMore": 1, "synckey": 123}
        return {"reviews": [], "hasMore": 0, "synckey": 123}

    monkeypatch.setattr(weread_native, "_call", fake_call)
    book, records = fetch_weread_book("secret", "book-1")
    assert book == BOOK and len(records) == 2
    assert records[0]["chapter"] == "One"
    assert [params.get("synckey") for _, params in calls] == [None, 0, 123]

    def stalled(_key, endpoint, **_params):
        if endpoint == "/book/bookmarklist":
            return {"book": BOOK, "chapters": [], "updated": []}
        return {"reviews": [], "hasMore": 1, "synckey": 0}

    monkeypatch.setattr(weread_native, "_call", stalled)
    with pytest.raises(LibrarianError) as error:
        fetch_weread_book("secret", "book-1")
    assert error.value.code == "UPSTREAM_FORMAT_UNSUPPORTED"


def test_weread_refuses_to_retire_user_corrected_trace(tmp_path):
    with Library(tmp_path) as lib:
        sync_weread_book(lib, "owner_a", "reader_1", BOOK, _items())
        review = search(lib, "owner_a", "My note")[0]
        corrected = correct_trace(lib, "owner_a", review["id"], 1,
                                  printed_text="User verified", reason="checked")
        with pytest.raises(LibrarianError) as error:
            sync_weread_book(lib, "owner_a", "reader_1", BOOK, _items()[:1])
        assert error.value.code == "RECONCILIATION_REQUIRED"
        assert lib.get("owner_a", "ReadingTrace", review["id"]) == corrected
