"""Adversarial owner references across read, search, and mutation ports."""
from __future__ import annotations

import pytest

from agents.librarian.runtime.digital import ingest_export
from agents.librarian.runtime.knowledge import create_candidate, promote_candidate
from agents.librarian.runtime.pipeline import correct_trace, search, search_response
from agents.librarian.runtime.review import review_queues
from agents.librarian.runtime.store import Library, LibrarianError


EXPORT = '''---
bookId: "synthetic-owner-book"
---
> [!abstract] Synthetic Owner Book
# 高亮划线
## Chapter
> 📌 Private passage
> ⏱ 2026-01-01 12:00:00 ^private-mark
'''.encode()


def test_foreign_ids_cannot_read_or_mutate_owner_records(tmp_path):
    with Library(tmp_path) as lib:
        trace = ingest_export(lib, "owner_a", "weread", "owner_a.md", EXPORT)[0]
        receipt = lib.ingest(
            "owner_a", transport="test", account_id="account", conversation_id="conversation",
            source_event_id="message", idempotency_key="owner-a-message",
            attachments=[{"source_item_id": "photo", "mime_type": "image/jpeg",
                          "data": b"private synthetic photo"}])
        capture_id = receipt["capture_ids"][0]
        candidate = create_candidate(
            lib, "owner_a", [{"trace_id": trace["id"], "revision": 1}],
            candidate_type="question",
            content={"text": "A private question", "confidence": None,
                     "basis": "model_inference"}, correlation_id="owner-a-review")

        denied = [
            lambda: lib.get("owner_b", "ReadingTrace", trace["id"]),
            lambda: lib.get("owner_b", "PageCapture", capture_id),
            lambda: lib.get("owner_b", "KnowledgeCandidate", candidate["id"]),
            lambda: lib.read_trace_evidence("owner_b", trace["id"]),
            lambda: lib.read_original("owner_b", capture_id),
            lambda: correct_trace(lib, "owner_b", trace["id"], 1,
                                  printed_text="overwrite", reason="attack"),
            lambda: promote_candidate(lib, "owner_b", candidate["id"], 1,
                                      lambda *_: "should-not-write"),
        ]
        for operation in denied:
            with pytest.raises(LibrarianError) as error:
                operation()
            assert error.value.code == "UNAUTHORIZED"

        assert search(lib, "owner_b", "Private passage") == []
        assert review_queues(lib, "owner_b") == {"resolution": [], "content": []}
        assert lib.pending_events("owner_b") == []
        request = {"owner_id": "owner_a", "query": "Private passage",
                   "filters": {"work_id": None, "edition_id": None,
                               "book_instance_id": None, "session_id": None,
                               "medium": None, "trace_types": [],
                               "include_unresolved": False},
                   "limit": 20, "cursor": None}
        with pytest.raises(LibrarianError) as error:
            search_response(lib, request, trusted_owner_id="owner_b")
        assert error.value.code == "UNAUTHORIZED"
        assert search_response(lib, {**request, "owner_id": "owner_b"},
                               trusted_owner_id="owner_b")["hits"] == []
        assert lib.get("owner_a", "ReadingTrace", trace["id"])["revision"] == 1
