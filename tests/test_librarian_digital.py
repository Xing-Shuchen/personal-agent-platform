from __future__ import annotations

import json
from pathlib import Path

import pytest

from agents.librarian.runtime.digital import ingest_export, parse_koodo, parse_weread
from agents.librarian.runtime.pipeline import search, search_response
from agents.librarian.runtime.store import Library, LibrarianError


WEREAD = """---
bookId: "book-42"
---
> [!abstract] Synthetic Title
# 高亮划线
## Chapter One
> 📌 Weber and Parsons
> ⏱ 2024-01-01 12:00:00 ^book-42-1-10-20
# 读书笔记
## Chapter One
### 划线评论
📌
The quoted passage ^note-123
 - 💭 Parsons?
 - ⏱ 2024-01-02 10:00:00
""".encode()

KOODO = """# Koodo Reader - Highlights
## Synthetic Koodo Book
### Chapter A
> A highlighted passage
*Date: 2026-09-20 | Color: #FF0000*
---
### Chapter B
> Another passage
*Date: 2026-09-21 | Color: #FF0000*
""".encode()


def test_parsers_keep_source_identity_and_separate_comment():
    book_id, title, entries = parse_weread(WEREAD)
    assert (book_id, title) == ("book-42", "Synthetic Title")
    assert [item["source_record_id"] for item in entries] == ["book-42-1-10-20", "note-123"]
    assert entries[1]["printed_text"] == "The quoted passage"
    assert entries[1]["annotation"] == "Parsons?"
    _, title, entries = parse_koodo(KOODO)
    assert title == "Synthetic Koodo Book"
    assert len(entries) == 2
    assert entries[0]["chapter"] == "Chapter A"


def test_storage_rejects_digital_trace_with_foreign_or_missing_catalog(tmp_path: Path) -> None:
    with Library(tmp_path) as lib:
        trace = ingest_export(lib, "owner_a", "weread", "book.md", WEREAD)[0]
        foreign = {"object_type": "Work", "schema_version": "0.1.0",
                   "id": "work_foreign", "owner_id": "owner_b",
                   "created_at": trace["created_at"], "title": "Foreign book",
                   "original_title": None, "authors": [], "identifiers": [],
                   "revision": 1, "supersedes_revision": None}
        lib.register("owner_b", foreign)
        for suffix, work_id in (("foreign", "work_foreign"),
                                ("missing", "work_missing")):
            forged = json.loads(json.dumps(trace))
            forged["id"] = f"rt_digital_{suffix}"
            forged["work_id"] = work_id
            with pytest.raises(LibrarianError) as rejected:
                with lib.transaction():
                    lib._put(forged)
            assert rejected.value.code == "VALIDATION_FAILED"
            assert lib.db.execute("SELECT 1 FROM records WHERE id=?",
                                  (forged["id"],)).fetchone() is None


def test_export_commit_survives_index_failure(tmp_path: Path, monkeypatch) -> None:
    from agents.librarian.runtime import pipeline

    real_index = pipeline._index_trace
    monkeypatch.setattr(pipeline, "_index_trace", lambda *_: (_ for _ in ()).throw(
        RuntimeError("index unavailable")))
    with Library(tmp_path) as lib:
        traces = ingest_export(lib, "owner_a", "weread", "book.md", WEREAD)
        assert len(traces) == 2
        assert lib.db.execute("SELECT COUNT(*) FROM trace_index").fetchone()[0] == 0
        assert lib.db.execute("SELECT COUNT(*) FROM digital_exports").fetchone()[0] == 1
    monkeypatch.setattr(pipeline, "_index_trace", real_index)
    with Library(tmp_path) as lib:
        assert ingest_export(lib, "owner_a", "weread", "book.md", WEREAD) == traces
        assert len(search(lib, "owner_a", "Weber")) == 1


def test_trace_event_failure_rolls_back_digital_export_and_retries(tmp_path: Path) -> None:
    with Library(tmp_path) as lib:
        lib.db.execute("CREATE TRIGGER fail_trace_event BEFORE INSERT ON outbox "
                       "WHEN NEW.event_type='reading.trace.created' "
                       "BEGIN SELECT RAISE(ABORT, 'event unavailable'); END")
        with pytest.raises(Exception, match="event unavailable"):
            ingest_export(lib, "owner_a", "weread", "book.md", WEREAD)
        assert lib.db.execute("SELECT COUNT(*) FROM records WHERE model IN "
                              "('Work','ReadingTrace')").fetchone()[0] == 0
        assert lib.db.execute("SELECT COUNT(*) FROM digital_exports").fetchone()[0] == 0
        assert lib.db.execute("SELECT COUNT(*) FROM outbox").fetchone()[0] == 0
        lib.db.execute("DROP TRIGGER fail_trace_event")
        assert len(ingest_export(lib, "owner_a", "weread", "book.md", WEREAD)) == 2


def test_exports_converge_at_trace_and_retry_is_idempotent(tmp_path: Path):
    with Library(tmp_path) as lib:
        weread = ingest_export(lib, "owner_a", "weread", "vault/weread/book.md", WEREAD)
        koodo = ingest_export(lib, "owner_a", "koodo", "vault/koodo/book.md", KOODO)
        assert len(weread) == 2 and len(koodo) == 2
        assert {trace["medium"] for trace in weread + koodo} == {"weread", "koodo"}
        assert all(trace["source"]["raw_payload"]["sha256"] for trace in weread + koodo)
        assert all(trace["attribution"]["mark_author"] == "unknown" for trace in weread + koodo)
        assert all(trace["marked_at"]["value"] is None for trace in weread + koodo)
        assert lib.read_trace_evidence("owner_a", weread[0]["id"]) == (WEREAD, "text/markdown")
        with pytest.raises(LibrarianError) as err:
            lib.read_trace_evidence("owner_b", weread[0]["id"])
        assert err.value.code == "UNAUTHORIZED"
        assert len(search(lib, "owner_a", "Parsons")) == 2
        assert len(search(lib, "owner_a", "Another")) == 1
        request = {"owner_id": "owner_a", "query": "Parsons",
                   "filters": {"work_id": None, "edition_id": None,
                               "book_instance_id": None, "session_id": None,
                               "medium": "weread", "trace_types": [],
                               "include_unresolved": False},
                   "limit": 1, "cursor": None}
        page_one = search_response(lib, request, trusted_owner_id="owner_a")
        assert page_one["index_state"] == "ready"
        assert page_one["hits"][0]["title"] == "Synthetic Title"
        assert page_one["hits"][0]["evidence"][0]["mime_type"] == "text/markdown"
        assert page_one["next_cursor"] == "1"
        page_two = search_response(lib, request | {"cursor": "1"}, trusted_owner_id="owner_a")
        assert page_two["next_cursor"] is None
        assert page_two["hits"][0]["trace_id"] != page_one["hits"][0]["trace_id"]
        structural = search_response(lib, request | {"query": "", "limit": 20},
                                     trusted_owner_id="owner_a")
        assert len(structural["hits"]) == 2
        assert all(hit["channels"] == ["structural"] for hit in structural["hits"])
        with pytest.raises(LibrarianError, match="structural filter"):
            search_response(lib, request | {"query": "", "filters": {
                **request["filters"], "medium": None}}, trusted_owner_id="owner_a")
        lib.db.execute("UPDATE trace_index SET revision=0 WHERE trace_id=?",
                       (page_one["hits"][0]["trace_id"],))
        lib.db.commit()
        assert search_response(lib, request, trusted_owner_id="owner_a")["index_state"] == "lagging"
        with pytest.raises(LibrarianError) as err:
            search_response(lib, request, trusted_owner_id="owner_b")
        assert err.value.code == "UNAUTHORIZED"
        assert search(lib, "owner_b", "Parsons") == []
        assert ingest_export(lib, "owner_a", "weread", "vault/weread/book.md", WEREAD) == weread
        renamed = ingest_export(lib, "owner_a", "weread", "vault/weread/renamed.md", WEREAD)
        assert [trace["id"] for trace in renamed] == [trace["id"] for trace in weread]
        with pytest.raises(LibrarianError) as err:
            ingest_export(lib, "owner_a", "weread", "vault/weread/book.md",
                          WEREAD.replace(b"Parsons?", b"Parsons!"))
        assert err.value.code == "RECONCILIATION_REQUIRED"
        assert len([e for e in lib.pending_events("owner_a") if e["event"] == "reading.trace.created"]) == 4
