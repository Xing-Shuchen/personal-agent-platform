from __future__ import annotations

import json
import io
from pathlib import Path

import pytest
from PIL import Image

from agents.librarian.runtime.digital import ingest_export
from agents.librarian.runtime.pipeline import bind_fingerprint_context, correct_trace, process_capture, reconcile_extraction, rebuild_index, render_trace_crop, resolve_capture, search, search_response
from agents.librarian.runtime.knowledge import create_candidate, decide_candidate, promote_candidate
from agents.librarian.runtime.review import review_queues
from agents.librarian.runtime.store import Library, LibrarianError, validate


def _detection(identifier: str, kind: str, text: str | None,
               linked: list[str] | None = None) -> dict:
    return {"id": identifier, "page_region_id": "page_left",
            "bbox": [.1, .1, .5, .2] if kind == "printed" else [.1, .18, .5, .21],
            "kind": kind,
            "text": {"text": text, "confidence": .85, "basis": "vision"} if text else None,
            "confidence": .9, "linked_text_region_ids": linked or [],
            "link_confidence": .95 if linked else None}


def _output() -> bytes:
    return json.dumps({
        "image_space": {"width": 1000, "height": 1400,
                        "basis": "exif_oriented_original"},
        "pages": [{"id": "page_left", "bbox": [0, 0, 1, 1], "side": "unknown",
                   "page": {"value": {"label": "171", "number": 171,
                                      "scheme": "arabic"}, "confidence": .9,
                            "basis": "vision", "status": "resolved"}}],
        "printed_regions": [_detection("printed_1", "printed", "Weber and Parsons")],
        "marks": [_detection("mark_1", "underline", None, ["printed_1"])],
        "annotations": [_detection("note_1", "margin_note", "Parsons?")],
        "symbols": [], "links": [], "warnings": []
    }).encode()


def _photo() -> bytes:
    stream = io.BytesIO()
    Image.new("RGB", (1000, 1400), "white").save(stream, format="PNG")
    return stream.getvalue()


def test_vision_page_resolution_revises_only_unknown_page(tmp_path: Path) -> None:
    observation = json.loads(_output())
    observation["pages"][0]["page"] = {"value": None, "confidence": None,
                                         "basis": "unknown", "status": "unresolved"}
    with Library(tmp_path) as lib:
        receipt = lib.ingest("owner_a", transport="gateway", account_id="account",
                             conversation_id="chat", source_event_id="message-1",
                             attachments=[{"source_item_id": "image-1", "mime_type": "image/png",
                                           "data": _photo()}], idempotency_key="command-1")
        capture_id = receipt["capture_ids"][0]
        traces = process_capture(lib, "owner_a", capture_id,
                                 lambda _: json.dumps(observation).encode())
        prior = traces[0]
        resolution = lib.get("owner_a", "CaptureResolution",
                             prior["source"]["resolution_id"])
        pages = json.loads(json.dumps(resolution["pages"]))
        pages[0]["page"] = {"value": {"label": "31", "number": 31,
                                       "scheme": "arabic"}, "confidence": .99,
                            "basis": "vision", "status": "resolved"}
        with pytest.raises(LibrarianError):
            resolve_capture(lib, "owner_a", capture_id, resolution["revision"],
                            pages=pages, session_id="session_fake", _basis="vision")
        revised_resolution = resolve_capture(
            lib, "owner_a", capture_id, resolution["revision"],
            pages=pages, _basis="vision")
        revised = lib.get("owner_a", "ReadingTrace", prior["id"])
        assert revised_resolution["revision"] == resolution["revision"] + 1
        assert revised["revision"] == prior["revision"] + 1
        assert revised["location"]["page"]["number"] == 31
        assert revised["content"] == prior["content"]


def _rotated_photo() -> bytes:
    stream = io.BytesIO()
    exif = Image.Exif()
    exif[274] = 6  # EXIF rotation swaps the display dimensions.
    Image.new("RGB", (1000, 1400), "white").save(stream, format="JPEG", exif=exif)
    return stream.getvalue()


def test_reextract_keeps_promoted_knowledge_source_active(tmp_path: Path) -> None:
    with Library(tmp_path) as lib:
        receipt = lib.ingest("owner_a", transport="gateway", account_id="account",
                             conversation_id="chat", source_event_id="message-1",
                             attachments=[{"source_item_id": "image-1", "mime_type": "image/png",
                                           "data": _photo()}], idempotency_key="command-1")
        capture_id = receipt["capture_ids"][0]
        old = process_capture(lib, "owner_a", capture_id, lambda _: _output(), extractor_version="v1")
        candidate = create_candidate(lib, "owner_a", [{"trace_id": old[0]["id"], "revision": 1}],
                                     candidate_type="concept", correlation_id="test",
                                     content={"text": None, "confidence": None, "basis": "unknown"})
        decide_candidate(lib, "owner_a", candidate["id"], 1, approve=True)
        promote_candidate(lib, "owner_a", candidate["id"], 2, lambda *_: "knowledge_test")
        with pytest.raises(LibrarianError, match="awaits reconciliation"):
            process_capture(lib, "owner_a", capture_id, lambda _: _output(), extractor_version="v2")
        with pytest.raises(LibrarianError) as error:
            reconcile_extraction(lib, "owner_a", capture_id, "v2")
        assert error.value.code == "RECONCILIATION_REQUIRED"
        assert lib.get("owner_a", "ReadingTrace", old[0]["id"])["status"] == "active"
        assert lib.get("owner_a", "KnowledgeCandidate", candidate["id"])["status"] == "promoted"


def test_late_edition_fingerprint_binds_unknown_capture_without_reextracting(tmp_path: Path) -> None:
    from zipfile import ZipFile
    from agents.librarian.runtime.gateway_search import search_inbound
    from agents.librarian.runtime.worker import _catalog

    epub = tmp_path / "9787208171411.epub"
    with ZipFile(epub, "w") as archive:
        archive.writestr("content.opf", "<package xmlns:dc='http://purl.org/dc/elements/1.1/'>"
                         "<metadata><dc:title>Test Work</dc:title></metadata></package>")
    with Library(tmp_path / "state") as lib:
        receipt = lib.ingest("owner_a", transport="feishu", account_id="librarian",
                             conversation_id="chat", source_event_id="message",
                             attachments=[{"source_item_id": "image", "mime_type": "image/png",
                                           "data": _photo()}], idempotency_key="command")
        capture_id = receipt["capture_ids"][0]
        traces = process_capture(lib, "owner_a", capture_id, lambda _: _output())
        assert all(trace["work_id"] is None for trace in traces)
        _catalog(lib, "owner_a", epub.stem, epub,
                 {"capture_ids": [capture_id], "origin": {"transport": "feishu",
                  "account_id": "librarian", "conversation_id": "chat"},
                  "received_at": "2026-09-28T00:00:00+00:00"})
        before = lib.db.execute("SELECT COUNT(*) FROM records WHERE model='PageObservation'").fetchone()[0]
        resolution = bind_fingerprint_context(lib, "owner_a", capture_id)
        assert resolution["work"]["basis"] == "edition_fingerprint"
        assert resolution["session"]["value"] is not None
        current = [lib.get("owner_a", "ReadingTrace", trace["id"]) for trace in traces]
        assert all(trace["revision"] == 2 and trace["context_state"] == "resolved"
                   and trace["work_id"] is not None for trace in current)
        assert lib.db.execute("SELECT COUNT(*) FROM records WHERE model='PageObservation'").fetchone()[0] == before
        assert bind_fingerprint_context(lib, "owner_a", capture_id) is None
        page_hits = search_inbound(lib, {"owner_id": "owner_a", "book": "《Test Work》",
                                         "page": 171})["hits"]
        assert {hit["trace_id"] for hit in page_hits} == {trace["id"] for trace in traces}
        assert all(hit["title"] == "Test Work" for hit in page_hits)

        second = lib.ingest("owner_a", transport="feishu", account_id="librarian",
                            conversation_id="chat", source_event_id="message-2",
                            attachments=[{"source_item_id": "image", "mime_type": "image/png",
                                          "data": _photo()}], idempotency_key="command-2")
        second_id = second["capture_ids"][0]
        second_traces = process_capture(lib, "owner_a", second_id, lambda _: _output())
        corrected = correct_trace(lib, "owner_a", second_traces[0]["id"], 1,
                                  printed_text="user checked", reason="review")
        with lib.transaction():
            lib.db.execute("INSERT INTO capture_context VALUES(?,?,?,?)",
                           ("owner_a", second_id, resolution["session"]["value"],
                            "edition_fingerprint"))
        with pytest.raises(LibrarianError) as error:
            bind_fingerprint_context(lib, "owner_a", second_id)
        assert error.value.code == "RECONCILIATION_REQUIRED"
        assert lib.get("owner_a", "ReadingTrace", corrected["id"])["work_id"] is None


def test_reextract_keeps_pending_candidate_source_active(tmp_path: Path) -> None:
    with Library(tmp_path) as lib:
        receipt = lib.ingest("owner_a", transport="gateway", account_id="account",
                             conversation_id="chat", source_event_id="message-1",
                             attachments=[{"source_item_id": "image-1", "mime_type": "image/png",
                                           "data": _photo()}], idempotency_key="command-1")
        capture_id = receipt["capture_ids"][0]
        old = process_capture(lib, "owner_a", capture_id, lambda _: _output(), extractor_version="v1")
        candidate = create_candidate(lib, "owner_a", [{"trace_id": old[0]["id"], "revision": 1}],
                                     candidate_type="concept", correlation_id="test",
                                     content={"text": None, "confidence": None, "basis": "unknown"})
        with pytest.raises(LibrarianError, match="awaits reconciliation"):
            process_capture(lib, "owner_a", capture_id, lambda _: _output(), extractor_version="v2")
        with pytest.raises(LibrarianError) as error:
            reconcile_extraction(lib, "owner_a", capture_id, "v2")
        assert error.value.code == "RECONCILIATION_REQUIRED"
        assert lib.get("owner_a", "ReadingTrace", old[0]["id"])["status"] == "active"
        assert lib.get("owner_a", "KnowledgeCandidate", candidate["id"])["status"] == "pending"


def test_reextract_with_vocabulary_configuration_requires_review(tmp_path: Path) -> None:
    with Library(tmp_path) as lib:
        receipt = lib.ingest("owner_a", transport="gateway", account_id="account",
                             conversation_id="chat", source_event_id="message-1",
                             attachments=[{"source_item_id": "image-1", "mime_type": "image/png",
                                           "data": _photo()}], idempotency_key="command-1")
        capture_id = receipt["capture_ids"][0]
        old = process_capture(lib, "owner_a", capture_id, lambda _: _output(), extractor_version="v1")
        vocabulary = {"enabled": True, "version": "personal-v1",
                      "mappings": {"!!": "promote_candidate"}}
        with pytest.raises(LibrarianError, match="awaits reconciliation"):
            process_capture(lib, "owner_a", capture_id, lambda _: _output(),
                            extractor_version="v2", vocabulary=vocabulary)
        with pytest.raises(LibrarianError) as error:
            reconcile_extraction(lib, "owner_a", capture_id, "v2")
        assert error.value.code == "RECONCILIATION_REQUIRED"
        assert all(lib.get("owner_a", "ReadingTrace", item["id"])["status"] == "active"
                   for item in old)


def test_vocabulary_snapshot_controls_retry_and_reconciliation(tmp_path: Path) -> None:
    with Library(tmp_path) as lib:
        receipt = lib.ingest("owner_a", transport="gateway", account_id="account",
                             conversation_id="chat", source_event_id="message-1",
                             attachments=[{"source_item_id": "image-1", "mime_type": "image/png",
                                           "data": _photo()}], idempotency_key="command-1")
        capture_id = receipt["capture_ids"][0]
        first_vocab = {"enabled": True, "version": "personal-v1",
                       "mappings": {"!!": "promote_candidate"}}
        old = process_capture(lib, "owner_a", capture_id, lambda _: _output(),
                              extractor_version="same-extractor", vocabulary=first_vocab)
        assert len(process_capture(lib, "owner_a", capture_id,
                                   lambda _: pytest.fail("same config reran extractor"),
                                   extractor_version="same-extractor",
                                   vocabulary=first_vocab)) == len(old)
        first_run = next(json.loads(row[0]) for row in lib.db.execute(
            "SELECT body FROM records WHERE model='ProcessingRun' AND current=1")
            if json.loads(row[0])["outcome"] in {"success", "partial"})
        assert first_run["normalizer_version"] == "physical-v1"
        assert first_run["vocabulary_version"] == "personal-v1"
        assert json.loads(lib._read_object(first_run["vocabulary_config_ref"])) == first_vocab

        changed_vocab = {"enabled": True, "version": "personal-v1",
                         "mappings": {"!!": "unresolved_question"}}
        with pytest.raises(LibrarianError, match="awaits reconciliation"):
            process_capture(lib, "owner_a", capture_id, lambda _: _output(),
                            extractor_version="same-extractor", vocabulary=changed_vocab)
        with pytest.raises(LibrarianError) as error:
            reconcile_extraction(lib, "owner_a", capture_id, "same-extractor")
        assert error.value.code == "RECONCILIATION_REQUIRED"
        assert all(lib.get("owner_a", "ReadingTrace", trace["id"])["status"] == "active"
                   for trace in old)


def test_same_vocabulary_snapshot_survives_new_extractor_version(tmp_path: Path) -> None:
    vocabulary = {"enabled": True, "version": "personal-v1",
                  "mappings": {"!!": "promote_candidate"}}
    with Library(tmp_path) as lib:
        receipt = lib.ingest("owner_a", transport="gateway", account_id="account",
                             conversation_id="chat", source_event_id="message-1",
                             attachments=[{"source_item_id": "image-1", "mime_type": "image/png",
                                           "data": _photo()}], idempotency_key="command-1")
        capture_id = receipt["capture_ids"][0]
        old = process_capture(lib, "owner_a", capture_id, lambda _: _output(),
                              extractor_version="v1", vocabulary=vocabulary)
        with pytest.raises(LibrarianError, match="awaits reconciliation"):
            process_capture(lib, "owner_a", capture_id, lambda _: _output(),
                            extractor_version="v2", vocabulary=vocabulary)
        new = reconcile_extraction(lib, "owner_a", capture_id, "v2")
        assert len(new) == len(old)
        assert all(trace["vocabulary_version"] == "personal-v1" for trace in new)
        relations = [json.loads(row[0]) for row in lib.db.execute(
            "SELECT body FROM records WHERE owner_id='owner_a' AND model='TraceRelation' AND current=1")]
        assert len(relations) == len(old)
        assert {relation["source_trace_ref"]["trace_id"] for relation in relations} == {
            trace["id"] for trace in new}
        assert {relation["target"]["id"] for relation in relations} == {
            trace["id"] for trace in old}
        assert all(relation["relation"] == "supersedes" for relation in relations)


def test_reextract_merge_of_old_mark_groups_requires_review(tmp_path: Path) -> None:
    with Library(tmp_path) as lib:
        receipt = lib.ingest("owner_a", transport="gateway", account_id="account",
                             conversation_id="chat", source_event_id="message-1",
                             attachments=[{"source_item_id": "image-1", "mime_type": "image/png",
                                           "data": _photo()}], idempotency_key="command-1")
        capture_id = receipt["capture_ids"][0]
        old = process_capture(lib, "owner_a", capture_id, lambda _: _output(), extractor_version="v1")
        updated = json.loads(_output())
        updated["links"] = [{"from_id": "mark_1", "to_id": "note_1",
                             "kind": "annotates", "confidence": .95}]
        with pytest.raises(LibrarianError, match="awaits reconciliation"):
            process_capture(lib, "owner_a", capture_id,
                            lambda _: json.dumps(updated).encode(), extractor_version="v2")
        with pytest.raises(LibrarianError) as error:
            reconcile_extraction(lib, "owner_a", capture_id, "v2")
        assert error.value.code == "RECONCILIATION_REQUIRED"
        assert all(lib.get("owner_a", "ReadingTrace", item["id"])["status"] == "active"
                   for item in old)


def test_initial_index_failure_preserves_observation_and_retries_projection(tmp_path: Path,
                                                                             monkeypatch) -> None:
    from agents.librarian.runtime import pipeline

    with Library(tmp_path) as lib:
        receipt = lib.ingest("owner_a", transport="gateway", account_id="account",
                             conversation_id="chat", source_event_id="message-1",
                             attachments=[{"source_item_id": "image-1", "mime_type": "image/png",
                                           "data": _photo()}], idempotency_key="command-1")
        capture_id = receipt["capture_ids"][0]
        calls = []
        def extract(_raw):
            calls.append(1)
            return _output()

        real_index = pipeline._index_trace
        monkeypatch.setattr(pipeline, "_index_trace", lambda *_: (_ for _ in ()).throw(
            RuntimeError("index unavailable")))
        traces = process_capture(lib, "owner_a", capture_id, extract)
        assert len(traces) == 2
        assert lib.db.execute("SELECT COUNT(*) FROM trace_index").fetchone()[0] == 0
        assert lib.db.execute("SELECT COUNT(*) FROM records WHERE model='PageObservation'").fetchone()[0] == 1
        assert lib.db.execute("SELECT COUNT(*) FROM records WHERE model='ProcessingRun'").fetchone()[0] == 1
        monkeypatch.setattr(pipeline, "_index_trace", real_index)
        assert len(process_capture(lib, "owner_a", capture_id, extract)) == 2
        assert len(calls) == 1
        assert lib.db.execute("SELECT COUNT(*) FROM trace_index").fetchone()[0] == 2


def test_index_failure_recovers_after_reopen_without_reextracting(tmp_path: Path,
                                                                  monkeypatch) -> None:
    from agents.librarian.runtime import pipeline

    with Library(tmp_path) as lib:
        receipt = lib.ingest("owner_a", transport="gateway", account_id="account",
                             conversation_id="chat", source_event_id="message-1",
                             attachments=[{"source_item_id": "image-1", "mime_type": "image/png",
                                           "data": _photo()}], idempotency_key="command-1")
        capture_id = receipt["capture_ids"][0]
        real_index = pipeline._index_trace
        monkeypatch.setattr(pipeline, "_index_trace", lambda *_: (_ for _ in ()).throw(
            RuntimeError("index unavailable")))
        traces = process_capture(lib, "owner_a", capture_id, lambda _: _output())
        event_ids = [row[0] for row in lib.db.execute(
            "SELECT event_id FROM outbox WHERE owner_id='owner_a' ORDER BY rowid")]
        assert len(traces) == 2
        assert len(event_ids) >= 3
    monkeypatch.setattr(pipeline, "_index_trace", real_index)
    with Library(tmp_path) as lib:
        request = {"owner_id": "owner_a", "query": "Weber",
                   "filters": {"work_id": None, "edition_id": None,
                               "book_instance_id": None, "session_id": None,
                               "medium": None, "trace_types": [],
                               "include_unresolved": True},
                   "limit": 10, "cursor": None}
        assert search_response(lib, request, trusted_owner_id="owner_a")["index_state"] == "lagging"
        recovered = process_capture(lib, "owner_a", capture_id,
                                    lambda _: pytest.fail("extractor reran after restart"))
        assert [item["id"] for item in recovered] == [item["id"] for item in traces]
        assert search_response(lib, request, trusted_owner_id="owner_a")["index_state"] == "ready"
        assert [row[0] for row in lib.db.execute(
            "SELECT event_id FROM outbox WHERE owner_id='owner_a' ORDER BY rowid")] == event_ids


def test_index_failure_does_not_rollback_user_correction(tmp_path: Path,
                                                         monkeypatch) -> None:
    from agents.librarian.runtime import pipeline

    with Library(tmp_path) as lib:
        receipt = lib.ingest("owner_a", transport="gateway", account_id="account",
                             conversation_id="chat", source_event_id="message",
                             attachments=[{"source_item_id": "image", "mime_type": "image/png",
                                           "data": _photo()}], idempotency_key="command")
        trace = process_capture(lib, "owner_a", receipt["capture_ids"][0],
                                lambda _: _output())[0]
        real_index = pipeline._index_trace
        monkeypatch.setattr(pipeline, "_index_trace", lambda *_: (_ for _ in ()).throw(
            RuntimeError("index unavailable")))
        corrected = correct_trace(lib, "owner_a", trace["id"], 1,
                                  printed_text="User verified text", reason="checked")
        assert lib.get("owner_a", "ReadingTrace", trace["id"]) == corrected
        assert corrected["revision"] == 2
        assert search(lib, "owner_a", "User verified", include_unresolved=True) == []
        monkeypatch.setattr(pipeline, "_index_trace", real_index)
    with Library(tmp_path) as lib:
        assert lib.get("owner_a", "ReadingTrace", trace["id"])["revision"] == 2
        rebuild_index(lib, "owner_a")
        assert [item["id"] for item in search(lib, "owner_a", "User verified",
                                               include_unresolved=True)] == [trace["id"]]


def test_index_failure_does_not_rollback_page_resolution(tmp_path: Path,
                                                         monkeypatch) -> None:
    from agents.librarian.runtime import pipeline

    with Library(tmp_path) as lib:
        receipt = lib.ingest("owner_a", transport="gateway", account_id="account",
                             conversation_id="chat", source_event_id="message",
                             attachments=[{"source_item_id": "image", "mime_type": "image/png",
                                           "data": _photo()}], idempotency_key="command")
        capture_id = receipt["capture_ids"][0]
        trace = process_capture(lib, "owner_a", capture_id, lambda _: _output())[0]
        prior = lib.get("owner_a", "CaptureResolution", trace["source"]["resolution_id"])
        pages = json.loads(json.dumps(prior["pages"]))
        pages[0]["page"] = {"value": {"label": "172", "number": 172,
                                       "scheme": "arabic"}, "confidence": None,
                            "basis": "user_statement", "status": "resolved"}
        real_index = pipeline._index_trace
        monkeypatch.setattr(pipeline, "_index_trace", lambda *_: (_ for _ in ()).throw(
            RuntimeError("index unavailable")))
        revised = resolve_capture(lib, "owner_a", capture_id, prior["revision"], pages=pages)
        current = lib.get("owner_a", "ReadingTrace", trace["id"])
        assert revised["revision"] == prior["revision"] + 1
        assert current["revision"] == trace["revision"] + 1
        assert current["location"]["page"]["number"] == 172
        monkeypatch.setattr(pipeline, "_index_trace", real_index)
        rebuild_index(lib, "owner_a")
        assert lib.db.execute("SELECT revision FROM trace_index WHERE trace_id=?",
                              (trace["id"],)).fetchone()[0] == current["revision"]


def test_search_response_accepts_corrected_trace_revision(tmp_path: Path) -> None:
    with Library(tmp_path) as lib:
        receipt = lib.ingest("owner_a", transport="gateway", account_id="account",
                             conversation_id="chat", source_event_id="message",
                             attachments=[{"source_item_id": "image", "mime_type": "image/png",
                                           "data": _photo()}], idempotency_key="command")
        trace = process_capture(lib, "owner_a", receipt["capture_ids"][0],
                                lambda _: _output())[0]
        corrected = correct_trace(lib, "owner_a", trace["id"], 1,
                                  printed_text="Corrected Parsons", reason="user checked")
        request = {"owner_id": "owner_a", "query": "Corrected Parsons",
                   "filters": {"work_id": None, "edition_id": None,
                               "book_instance_id": None, "session_id": None,
                               "medium": None, "trace_types": [],
                               "include_unresolved": True},
                   "limit": 10, "cursor": None}
        response = search_response(lib, request, trusted_owner_id="owner_a")
        assert [(hit["trace_id"], hit["revision"]) for hit in response["hits"]] == [
            (trace["id"], corrected["revision"])]


def test_storage_rejects_forged_physical_detection_and_capture_links(tmp_path: Path) -> None:
    with Library(tmp_path) as lib:
        receipt = lib.ingest("owner_a", transport="gateway", account_id="account",
                             conversation_id="chat", source_event_id="message-1",
                             attachments=[{"source_item_id": "image-1", "mime_type": "image/png",
                                           "data": _photo()}], idempotency_key="command-1")
        trace = process_capture(lib, "owner_a", receipt["capture_ids"][0],
                                lambda _: _output())[0]
        another = lib.ingest("owner_a", transport="gateway", account_id="account",
                             conversation_id="chat", source_event_id="message-2",
                             attachments=[{"source_item_id": "image-2", "mime_type": "image/png",
                                           "data": _photo()}], idempotency_key="command-2")
        for suffix, field, value in (
                ("detection", "detection_ids", ["printed_missing", "mark_1"]),
                ("capture", "capture_id", another["capture_ids"][0])):
            forged = json.loads(json.dumps(trace))
            forged["id"] = f"rt_forged_{suffix}"
            forged["source"][field] = value
            with pytest.raises(LibrarianError) as rejected:
                with lib.transaction():
                    lib._put(forged)
            assert rejected.value.code == "VALIDATION_FAILED"
            assert lib.db.execute("SELECT 1 FROM records WHERE id=?",
                                  (forged["id"],)).fetchone() is None


def test_storage_checks_owner_and_historical_trace_versions_in_relations(tmp_path: Path) -> None:
    with Library(tmp_path) as lib:
        receipt = lib.ingest("owner_a", transport="gateway", account_id="account",
                             conversation_id="chat", source_event_id="message",
                             attachments=[{"source_item_id": "image", "mime_type": "image/png",
                                           "data": _photo()}], idempotency_key="command")
        trace = process_capture(lib, "owner_a", receipt["capture_ids"][0],
                                lambda _: _output())[0]
        revised = correct_trace(lib, "owner_a", trace["id"], 1,
                                printed_text="Verified", reason="checked")
        relation = {"object_type": "TraceRelation", "schema_version": "0.1.0",
                    "id": "relation_history", "owner_id": "owner_a",
                    "created_at": revised["created_at"], "revision": 1,
                    "supersedes_revision": None,
                    "source_trace_ref": {"trace_id": trace["id"], "revision": 2},
                    "relation": "supersedes",
                    "target": {"type": "trace", "id": trace["id"], "revision": 1},
                    "provenance": "user correction", "confidence": None}
        with lib.transaction():
            lib._put(relation)
        assert lib.get("owner_a", "TraceRelation", relation["id"]) == relation
        for suffix, target_revision in (("missing", 99), ("null", None)):
            forged = json.loads(json.dumps(relation))
            forged["id"] = f"relation_{suffix}"
            forged["target"]["revision"] = target_revision
            with pytest.raises(LibrarianError) as rejected:
                with lib.transaction():
                    lib._put(forged)
            assert rejected.value.code == "VALIDATION_FAILED"
        wrong_owner = json.loads(json.dumps(relation))
        wrong_owner["id"] = "relation_wrong_owner"
        wrong_owner["owner_id"] = "owner_b"
        with pytest.raises(LibrarianError) as rejected:
            with lib.transaction():
                lib._put(wrong_owner)
        assert rejected.value.code == "VALIDATION_FAILED"


def test_storage_rejects_resolution_with_missing_catalog_context(tmp_path: Path) -> None:
    with Library(tmp_path) as lib:
        receipt = lib.ingest("owner_a", transport="gateway", account_id="account",
                             conversation_id="chat", source_event_id="message",
                             attachments=[{"source_item_id": "image", "mime_type": "image/png",
                                           "data": _photo()}], idempotency_key="command")
        trace = process_capture(lib, "owner_a", receipt["capture_ids"][0],
                                lambda _: _output())[0]
        resolution = lib.get("owner_a", "CaptureResolution",
                             trace["source"]["resolution_id"])
        forged = json.loads(json.dumps(resolution))
        forged["id"] = "resolution_missing_edition"
        forged["edition"] = {"value": "edition_missing", "confidence": None,
                             "basis": "user_confirmation", "status": "resolved"}
        with pytest.raises(LibrarianError) as rejected:
            with lib.transaction():
                lib._put(forged)
        assert rejected.value.code == "VALIDATION_FAILED"
        assert lib.db.execute("SELECT 1 FROM records WHERE id=?",
                              (forged["id"],)).fetchone() is None


def test_reconciliation_index_failure_never_serves_superseded_trace(tmp_path: Path,
                                                                     monkeypatch) -> None:
    from agents.librarian.runtime import pipeline

    with Library(tmp_path) as lib:
        receipt = lib.ingest("owner_a", transport="gateway", account_id="account",
                             conversation_id="chat", source_event_id="message-1",
                             attachments=[{"source_item_id": "image-1", "mime_type": "image/png",
                                           "data": _photo()}], idempotency_key="command-1")
        capture_id = receipt["capture_ids"][0]
        old = process_capture(lib, "owner_a", capture_id, lambda _: _output(),
                              extractor_version="v1")
        with pytest.raises(LibrarianError, match="awaits reconciliation"):
            process_capture(lib, "owner_a", capture_id, lambda _: _output(),
                            extractor_version="v2")
        index = pipeline._index_trace
        monkeypatch.setattr(pipeline, "_index_trace", lambda *_: (_ for _ in ()).throw(
            RuntimeError("index unavailable")))
        new = reconcile_extraction(lib, "owner_a", capture_id, "v2")
        assert len(new) == 2
        assert all(lib.get("owner_a", "ReadingTrace", item["id"])["status"] == "superseded"
                   for item in old)
        assert search(lib, "owner_a", "Weber", include_unresolved=True) == []
        monkeypatch.setattr(pipeline, "_index_trace", index)
        assert len(process_capture(lib, "owner_a", capture_id,
                                   lambda _: pytest.fail("extractor reran"),
                                   extractor_version="v2")) == 2
        assert {item["id"] for item in search(lib, "owner_a", "Weber",
                                               include_unresolved=True)} == {
                                                   item["id"] for item in new if
                                                   item["content"]["printed_text"]["text"]}


def test_synthetic_observation_to_provenance_search_and_rebuild(tmp_path: Path):
    with Library(tmp_path) as lib:
        receipt = lib.ingest("owner_a", transport="gateway", account_id="account",
                             conversation_id="chat", source_event_id="message-1",
                             attachments=[{"source_item_id": "image-1",
                                           "mime_type": "image/png", "data": _photo()}],
                             idempotency_key="command-1")
        capture_id = receipt["capture_ids"][0]
        calls = []
        def extractor(raw: bytes) -> bytes:
            calls.append(raw)
            return _output()
        traces = process_capture(lib, "owner_a", capture_id, extractor)
        assert len(traces) == 2
        assert traces[0]["content"]["printed_text"]["text"] == "Weber and Parsons"
        assert traces[1]["content"]["annotation"]["text"] == "Parsons?"
        assert traces[0]["location"]["page"]["number"] == 171
        assert traces[0]["attribution"]["mark_author"] == "unknown"
        assert lib.read_trace_evidence("owner_a", traces[0]["id"])[0] == _photo()
        assert all(t["source"]["capture_id"] == capture_id for t in traces)
        assert search(lib, "owner_a", "Parsons") == []  # unresolved stays out of default results
        hits = search(lib, "owner_a", "Parsons", include_unresolved=True)
        assert {h["id"] for h in hits} == {t["id"] for t in traces}
        assert search(lib, "owner_b", "Parsons", include_unresolved=True) == []
        assert process_capture(lib, "owner_a", capture_id, extractor) == traces
        assert len(calls) == 1
        lib.db.execute("DELETE FROM trace_index")
        lib.db.commit()
        assert rebuild_index(lib, "owner_a") == 2
        assert len(search(lib, "owner_a", "Parsons", include_unresolved=True)) == 2
        assert [e["event"] for e in lib.pending_events("owner_a")].count("reading.trace.created") == 2


def test_same_query_returns_common_hits_from_all_three_media(tmp_path: Path):
    weread = '''---
bookId: "three-media-weread"
---
> [!abstract] WeRead fixture
# 高亮划线
## One
> 📌 Weber and Parsons
> ⏱ 2026-01-01 12:00:00 ^weread-mark
'''.encode()
    koodo = '''# Koodo Reader - Highlights
## Koodo fixture
### One
> Weber and Parsons
*Date: 2026-01-01 | Color: #FFFF00*
'''.encode()
    with Library(tmp_path) as lib:
        capture = lib.ingest(
            "owner_a", transport="gateway", account_id="account",
            conversation_id="chat", source_event_id="message",
            attachments=[{"source_item_id": "photo", "mime_type": "image/png",
                          "data": _photo()}], idempotency_key="three-media-photo")
        process_capture(lib, "owner_a", capture["capture_ids"][0], lambda _: _output())
        ingest_export(lib, "owner_a", "weread", "weread.md", weread)
        ingest_export(lib, "owner_a", "koodo", "koodo.md", koodo)
        request = {"owner_id": "owner_a", "query": "Weber and Parsons",
                   "filters": {"work_id": None, "edition_id": None,
                               "book_instance_id": None, "session_id": None,
                               "medium": None, "trace_types": [],
                               "include_unresolved": True},
                   "limit": 20, "cursor": None}
        response = search_response(lib, request, trusted_owner_id="owner_a")
        assert response["index_state"] == "ready"
        hits = response["hits"]
        assert {hit["medium"] for hit in hits} == {"physical", "weread", "koodo"}
        assert all(hit["content"]["printed_text"]["text"] == "Weber and Parsons"
                   for hit in hits)
        assert all("source" not in hit and "source_record_id" not in hit for hit in hits)
        assert {hit["evidence"][0]["mime_type"] for hit in hits} == {
            "image/png", "text/markdown"}
        assert search_response(lib, {**request, "owner_id": "owner_b"},
                               trusted_owner_id="owner_b")["hits"] == []


def test_invalid_extraction_keeps_raw_output_without_trace(tmp_path: Path):
    with Library(tmp_path) as lib:
        receipt = lib.ingest("owner_a", transport="gateway", account_id="a",
                             conversation_id="c", source_event_id="m",
                             attachments=[{"source_item_id": "i", "mime_type": "image/png",
                                           "data": _photo()}], idempotency_key="k")
        with pytest.raises(LibrarianError) as err:
            process_capture(lib, "owner_a", receipt["capture_ids"][0], lambda _: b"{broken")
        assert err.value.code == "EXTRACTION_SCHEMA_INVALID"
        assert review_queues(lib, "owner_a") == {"resolution": [], "content": []}
        row = lib.db.execute("SELECT raw_asset,error_code FROM extractor_attempts").fetchone()
        assert row["error_code"] == "EXTRACTION_SCHEMA_INVALID"
        ref = json.loads(row["raw_asset"])
        assert (tmp_path / ref["object_key"]).read_bytes() == b"{broken"
        failed = lib.db.execute("SELECT body FROM records WHERE model='ProcessingRun'").fetchone()[0]
        assert json.loads(failed)["outcome"] == "failed"
        assert lib.db.execute("SELECT COUNT(*) FROM records WHERE model='ReadingTrace'").fetchone()[0] == 0


def test_unreadable_page_number_keeps_local_trace_and_original(tmp_path: Path):
    output = json.loads(_output())
    output["pages"][0]["page"] = {"value": None, "confidence": None,
                                  "basis": "unknown", "status": "unresolved"}
    with Library(tmp_path) as lib:
        receipt = lib.ingest("owner_a", transport="gateway", account_id="a",
                             conversation_id="c", source_event_id="m",
                             attachments=[{"source_item_id": "i", "mime_type": "image/png",
                                           "data": _photo()}], idempotency_key="k")
        capture_id = receipt["capture_ids"][0]
        traces = process_capture(lib, "owner_a", capture_id,
                                 lambda _: json.dumps(output).encode())
        assert len(traces) == 2
        assert all(trace["location"]["page"] is None for trace in traces)
        assert lib.read_original("owner_a", capture_id) == _photo()
        run = json.loads(lib.db.execute(
            "SELECT body FROM records WHERE model='ProcessingRun'").fetchone()[0])
        assert run["outcome"] == "partial"
        assert "NEEDS_PAGE_RESOLUTION" in run["issues"]


def test_uncertain_ordinary_underline_is_saved_without_content_review(tmp_path: Path):
    output = json.loads(_output())
    output["printed_regions"][0]["text"] = {"text": "Weber and Parson?",
                                            "confidence": .45, "basis": "vision"}
    output["annotations"] = []
    with Library(tmp_path) as lib:
        receipt = lib.ingest("owner_a", transport="gateway", account_id="a",
                             conversation_id="c", source_event_id="m",
                             attachments=[{"source_item_id": "i", "mime_type": "image/png",
                                           "data": _photo()}], idempotency_key="k")
        traces = process_capture(lib, "owner_a", receipt["capture_ids"][0],
                                 lambda _: json.dumps(output).encode())
        assert len(traces) == 1
        assert traces[0]["content"]["printed_text"] == {
            "text": "Weber and Parson?", "confidence": .45, "basis": "vision"}
        assert traces[0]["review"] == {"required": False, "state": "none", "reason": None}
        assert review_queues(lib, "owner_a")["content"] == []


def test_printed_and_margin_punctuation_do_not_trigger_symbol_vocabulary(tmp_path: Path):
    output = json.loads(_output())
    output["printed_regions"][0]["text"]["text"] = "R! Weber and Parsons"
    output["annotations"][0]["text"]["text"] = "Parsons?"
    vocabulary = {"enabled": True, "version": "personal-v1",
                  "mappings": {"R": "reread_target", "?": "question_target",
                               "!": "promote_candidate"}}
    with Library(tmp_path) as lib:
        receipt = lib.ingest("owner_a", transport="gateway", account_id="a",
                             conversation_id="c", source_event_id="m",
                             attachments=[{"source_item_id": "i", "mime_type": "image/png",
                                           "data": _photo()}], idempotency_key="k")
        traces = process_capture(lib, "owner_a", receipt["capture_ids"][0],
                                 lambda _: json.dumps(output).encode(),
                                 vocabulary=vocabulary)
        assert all(trace["intent_signals"] == [] for trace in traces)
        assert lib.db.execute(
            "SELECT COUNT(*) FROM records WHERE model='KnowledgeCandidate'").fetchone()[0] == 0


def test_missing_text_link_target_is_rejected(tmp_path: Path):
    output = json.loads(_output())
    output["marks"][0]["linked_text_region_ids"] = ["missing"]
    with Library(tmp_path) as lib:
        receipt = lib.ingest("owner_a", transport="gateway", account_id="a",
                             conversation_id="c", source_event_id="m",
                             attachments=[{"source_item_id": "i", "mime_type": "image/png",
                                           "data": _photo()}], idempotency_key="k")
        with pytest.raises(LibrarianError) as err:
            process_capture(lib, "owner_a", receipt["capture_ids"][0],
                            lambda _: json.dumps(output).encode())
        assert err.value.code == "EXTRACTION_SCHEMA_INVALID"


def test_cross_page_text_link_is_rejected_and_observation_link_keeps_traces_separate(tmp_path: Path):
    output = json.loads(_output())
    output["pages"][0]["id"] = "left"
    output["pages"][0]["bbox"] = [0, 0, .5, 1]
    output["pages"].append({"id": "right", "bbox": [.5, 0, 1, 1],
                            "side": "right", "page": {"value": None,
                            "confidence": None, "basis": "unknown",
                            "status": "unresolved"}})
    output["printed_regions"] = [{**_detection("right_text", "printed", "Other page"),
                                   "page_region_id": "right", "bbox": [.6, .1, .9, .2]}]
    output["marks"] = [{**_detection("left_mark", "underline", None, ["right_text"]),
                        "page_region_id": "left", "bbox": [.1, .18, .4, .21]}]
    output["annotations"] = []
    output["symbols"] = [{**_detection("right_symbol", "symbol", "R"),
                          "page_region_id": "right", "bbox": [.6, .18, .7, .21]}]
    with Library(tmp_path) as lib:
        receipt = lib.ingest("owner_a", transport="gateway", account_id="a",
                             conversation_id="c", source_event_id="m",
                             attachments=[{"source_item_id": "i", "mime_type": "image/png",
                                           "data": _photo()}], idempotency_key="k")
        capture_id = receipt["capture_ids"][0]
        with pytest.raises(LibrarianError) as error:
            process_capture(lib, "owner_a", capture_id,
                            lambda _: json.dumps(output).encode())
        assert error.value.code == "EXTRACTION_SCHEMA_INVALID"
        assert lib.db.execute(
            "SELECT COUNT(*) FROM records WHERE model='ReadingTrace'").fetchone()[0] == 0

        output["marks"][0]["linked_text_region_ids"] = []
        output["marks"][0]["link_confidence"] = None
        output["links"] = [{"from_id": "left_mark", "to_id": "right_symbol",
                            "kind": "annotates", "confidence": .95}]
        traces = process_capture(lib, "owner_a", capture_id,
                                 lambda _: json.dumps(output).encode())
        assert len(traces) == 2
        assert {trace["location"]["page_region_id"] for trace in traces} == {"left", "right"}
        assert all(trace["content"]["printed_text"]["text"] is None for trace in traces)


def test_extractor_cannot_override_trusted_observation_identity(tmp_path: Path):
    output = json.loads(_output())
    output["owner_id"] = "owner_b"
    output["raw_output_asset"] = {"object_key": "forged"}
    with Library(tmp_path) as lib:
        receipt = lib.ingest("owner_a", transport="gateway", account_id="a",
                             conversation_id="c", source_event_id="m",
                             attachments=[{"source_item_id": "i", "mime_type": "image/png",
                                           "data": _photo()}], idempotency_key="k")
        with pytest.raises(LibrarianError) as error:
            process_capture(lib, "owner_a", receipt["capture_ids"][0],
                            lambda _: json.dumps(output).encode())
        assert error.value.code == "EXTRACTION_SCHEMA_INVALID"
        assert lib.db.execute("SELECT COUNT(*) FROM records WHERE model='PageObservation'").fetchone()[0] == 0
        assert lib.db.execute("SELECT COUNT(*) FROM records WHERE model='ReadingTrace'").fetchone()[0] == 0


def test_structural_search_finds_a_mark_without_recognized_text(tmp_path: Path):
    output = json.loads(_output())
    output["printed_regions"] = []
    output["marks"] = []
    output["annotations"] = []
    output["symbols"] = [_detection("symbol_1", "symbol", None)]
    with Library(tmp_path) as lib:
        receipt = lib.ingest("owner_a", transport="gateway", account_id="a",
                             conversation_id="c", source_event_id="m",
                             attachments=[{"source_item_id": "i", "mime_type": "image/png",
                                           "data": _photo()}], idempotency_key="k")
        trace = process_capture(lib, "owner_a", receipt["capture_ids"][0],
                                lambda _: json.dumps(output).encode())[0]
        assert trace["content"]["printed_text"]["text"] is None
        request = {"owner_id": "owner_a", "query": "",
                   "filters": {"work_id": None, "edition_id": None,
                               "book_instance_id": None, "session_id": None,
                               "medium": None, "trace_types": ["symbol"],
                               "include_unresolved": True},
                   "limit": 20, "cursor": None}
        hit = search_response(lib, request, trusted_owner_id="owner_a")["hits"][0]
        assert hit["trace_id"] == trace["id"]
        assert hit["channels"] == ["structural"]
        assert hit["evidence"][0]["mime_type"] == "image/png"


def test_conflicting_explicit_session_keeps_original_and_observation(tmp_path: Path):
    now = "2026-09-28T00:00:00+00:00"
    with Library(tmp_path) as lib:
        for name in ("one", "other"):
            lib.register("owner_a", {"object_type": "Work", "schema_version": "0.1.0",
                         "id": f"work_{name}", "owner_id": "owner_a", "created_at": now,
                         "title": f"Synthetic {name}", "original_title": None,
                         "authors": [], "identifiers": [], "revision": 1,
                         "supersedes_revision": None})
        session = lib.start_session("owner_a")
        # The session is explicitly attached to one work; a submitted different
        # work is retained on the immutable capture rather than reassigned.
        current = lib.get("owner_a", "ReadingSession", session["id"])
        current["work_id"] = "work_one"
        current["revision"] = 2
        current["supersedes_revision"] = 1
        with lib.transaction():
            lib._put(current)
        receipt = lib.ingest("owner_a", transport="gateway", account_id="a",
                             conversation_id="c", source_event_id="m",
                             attachments=[{"source_item_id": "i", "mime_type": "image/png",
                                           "data": _photo()}], idempotency_key="k",
                             submitted_context={"session_id": session["id"],
                                                "work_id": "work_other"})
        capture_id = receipt["capture_ids"][0]
        with pytest.raises(LibrarianError) as error:
            process_capture(lib, "owner_a", capture_id, lambda _: _output())
        assert error.value.code == "CONTEXT_CONFLICT"
        assert lib.read_original("owner_a", capture_id) == _photo()
        run = json.loads(lib.db.execute("SELECT body FROM records WHERE model='ProcessingRun'").fetchone()[0])
        assert run["outcome"] == "failed" and "CONTEXT_CONFLICT" in run["issues"]
        observation = json.loads(lib.db.execute("SELECT body FROM records WHERE model='PageObservation'").fetchone()[0])
        assert observation["capture_id"] == capture_id
        attempt = lib.db.execute("SELECT raw_asset,error_code FROM extractor_attempts").fetchone()
        assert attempt["error_code"] == "CONTEXT_CONFLICT"
        assert (tmp_path / json.loads(attempt["raw_asset"])["object_key"]).read_bytes() == _output()
        assert lib.db.execute("SELECT COUNT(*) FROM records WHERE model='ReadingTrace'").fetchone()[0] == 0
        resolved = resolve_capture(lib, "owner_a", capture_id, None,
                                   session_id=session["id"], work_id="work_one")
        assert resolved["revision"] == 1
        traces = process_capture(lib, "owner_a", capture_id, lambda _: _output())
        assert len(traces) == 2
        assert all(trace["work_id"] == "work_one" for trace in traces)
        assert lib.get("owner_a", "PageObservation", observation["id"]) == observation

        second = lib.ingest("owner_a", transport="gateway", account_id="a",
                            conversation_id="c", source_event_id="m2",
                            attachments=[{"source_item_id": "i2", "mime_type": "image/png",
                                          "data": _photo()}], idempotency_key="k2",
                            submitted_context={"session_id": session["id"]})
        title_output = json.loads(_output())
        title_output["visible_title"] = {"text": "Synthetic other", "confidence": .95,
                                         "basis": "vision"}
        second_id = second["capture_ids"][0]
        with pytest.raises(LibrarianError) as title_error:
            process_capture(lib, "owner_a", second_id,
                            lambda _: json.dumps(title_output).encode())
        assert title_error.value.code == "CONTEXT_CONFLICT"
        assert lib.read_original("owner_a", second_id) == _photo()
        resolve_capture(lib, "owner_a", second_id, None,
                        session_id=session["id"], work_id="work_one")
        confirmed = process_capture(lib, "owner_a", second_id,
                                    lambda _: json.dumps(title_output).encode())
        assert len(confirmed) == 2
        title_output["visible_title"]["confidence"] = .7
        third = lib.ingest("owner_a", transport="gateway", account_id="a",
                           conversation_id="c", source_event_id="m3",
                           attachments=[{"source_item_id": "i3", "mime_type": "image/png",
                                         "data": _photo()}], idempotency_key="k3",
                           submitted_context={"session_id": session["id"]})
        low_confidence = process_capture(lib, "owner_a", third["capture_ids"][0],
                                         lambda _: json.dumps(title_output).encode())
        assert len(low_confidence) == 2


def test_same_title_two_copies_requires_explicit_catalog_resolution(tmp_path: Path):
    now = "2026-09-28T00:00:00+00:00"
    with Library(tmp_path) as lib:
        lib.register("owner_a", {"object_type": "Work", "schema_version": "0.1.0",
                     "id": "work_shared", "owner_id": "owner_a", "created_at": now,
                     "title": "Shared Title", "original_title": None,
                     "authors": [], "identifiers": [], "revision": 1,
                     "supersedes_revision": None})
        for suffix in ("one", "two"):
            lib.register("owner_a", {
                "object_type": "Edition", "schema_version": "0.1.0",
                "id": f"edition_{suffix}", "owner_id": "owner_a", "created_at": now,
                "work_id": "work_shared", "edition_label": suffix, "publisher": None,
                "publication_year": None, "isbn": {"isbn13": None, "isbn10": None},
                "language": None, "page_count": None, "volume_label": None,
                "revision": 1, "supersedes_revision": None})
            lib.register("owner_a", {
                "object_type": "BookInstance", "schema_version": "0.1.0",
                "id": f"bookinst_{suffix}", "owner_id": "owner_a", "created_at": now,
                "edition_id": f"edition_{suffix}", "medium": "physical",
                "acquired_at": {"value": None, "confidence": None, "basis": "unknown"},
                "ownership_status": "owned", "physical": {"qr_id": None, "shelf": None},
                "reading_status": {"state": "unread", "current_page": None,
                                   "progress_evidence_ref": None},
                "revision": 1, "supersedes_revision": None})
        receipt = lib.ingest(
            "owner_a", transport="gateway", account_id="account",
            conversation_id="chat", source_event_id="message-1",
            attachments=[{"source_item_id": "image-1", "mime_type": "image/png",
                          "data": _photo()}], idempotency_key="same-title-1")
        capture_id = receipt["capture_ids"][0]
        output = json.loads(_output())
        output["visible_title"] = {"text": "Shared Title", "confidence": .99,
                                   "basis": "vision"}
        traces = process_capture(lib, "owner_a", capture_id,
                                 lambda _: json.dumps(output).encode())
        assert len(traces) == 2
        assert all(trace["context_state"] == "unresolved" and
                   trace["book_instance_id"] is None and trace["edition_id"] is None
                   for trace in traces)
        assert search(lib, "owner_a", "Parsons") == []
        assert len(search(lib, "owner_a", "Parsons", include_unresolved=True)) == 2
        queue = review_queues(lib, "owner_a")
        assert len(queue["resolution"]) == 1
        assert queue["resolution"][0]["captures"][0]["capture_id"] == capture_id

        session = lib.start_session("owner_a", "bookinst_two")
        resolution = resolve_capture(lib, "owner_a", capture_id, 1,
                                     session_id=session["id"],
                                     book_instance_id="bookinst_two")
        assert resolution["book_instance"]["value"] == "bookinst_two"
        resolved = search(lib, "owner_a", "Parsons")
        assert len(resolved) == 2
        assert all(trace["book_instance_id"] == "bookinst_two" and
                   trace["edition_id"] == "edition_two" for trace in resolved)
        assert lib.get("owner_a", "BookInstance", "bookinst_one")["reading_status"]["state"] == "unread"


def test_explicit_annotation_link_groups_trace_without_inventing_authorship(tmp_path: Path):
    output = json.loads(_output())
    output["links"] = [{"from_id": "mark_1", "to_id": "note_1",
                        "kind": "annotates", "confidence": .95}]
    with Library(tmp_path) as lib:
        receipt = lib.ingest("owner_a", transport="gateway", account_id="a",
                             conversation_id="c", source_event_id="m",
                             attachments=[{"source_item_id": "i", "mime_type": "image/png",
                                           "data": _photo()}], idempotency_key="k")
        traces = process_capture(lib, "owner_a", receipt["capture_ids"][0],
                                 lambda _: json.dumps(output).encode())
        assert len(traces) == 1
        assert traces[0]["trace_types"] == ["underline", "margin_note"]
        assert traces[0]["content"]["annotation"]["text"] == "Parsons?"
        assert traces[0]["attribution"]["mark_author"] == "unknown"


def test_correction_adds_revision_and_keeps_evidence(tmp_path: Path):
    with Library(tmp_path) as lib:
        receipt = lib.ingest("owner_a", transport="gateway", account_id="a",
                             conversation_id="c", source_event_id="m",
                             attachments=[{"source_item_id": "i", "mime_type": "image/png",
                                           "data": _photo()}], idempotency_key="k")
        trace = process_capture(lib, "owner_a", receipt["capture_ids"][0],
                                lambda _: _output())[1]
        old_observation = trace["source"]["observation_id"]
        changed = correct_trace(lib, "owner_a", trace["id"], 1,
                                annotation="Parsons!", reason="user correction")
        assert changed["revision"] == 2
        assert changed["source"]["observation_id"] == old_observation
        assert changed["provenance"] == trace["provenance"]
        assert changed["content"]["annotation"]["basis"] == "user_statement"
        history = lib.db.execute("SELECT body FROM records WHERE model='ReadingTrace' AND id=? ORDER BY revision",
                                 (trace["id"],)).fetchall()
        assert json.loads(history[0]["body"])["content"]["annotation"]["text"] == "Parsons?"
        assert search(lib, "owner_a", "Parsons!", include_unresolved=True)[0]["revision"] == 2
        assert not search(lib, "owner_a", "Parsons?", include_unresolved=True)
        with pytest.raises(LibrarianError) as err:
            correct_trace(lib, "owner_a", trace["id"], 1,
                          annotation="stale", reason="stale request")
        assert err.value.code == "REVISION_CONFLICT"
        assert [e["event"] for e in lib.pending_events("owner_a")].count("reading.trace.corrected") == 1


def test_new_extractor_preserves_candidate_observation_without_overwriting_correction(tmp_path: Path):
    with Library(tmp_path) as lib:
        receipt = lib.ingest("owner_a", transport="gateway", account_id="a",
                             conversation_id="c", source_event_id="m",
                             attachments=[{"source_item_id": "i", "mime_type": "image/png",
                                           "data": _photo()}], idempotency_key="k")
        capture_id = receipt["capture_ids"][0]
        trace = process_capture(lib, "owner_a", capture_id, lambda _: _output(),
                                extractor_version="vision-v1")[1]
        corrected = correct_trace(lib, "owner_a", trace["id"], 1,
                                  annotation="Parsons!", reason="user correction")
        initial_events = len(lib.pending_events("owner_a"))
        with pytest.raises(LibrarianError) as error:
            process_capture(lib, "owner_a", capture_id, lambda _: _output(),
                            extractor_version="vision-v2")
        assert error.value.code == "RECONCILIATION_REQUIRED"
        pending = [json.loads(row[0]) for row in lib.db.execute(
            "SELECT body FROM records WHERE model='ProcessingRun'")
            if json.loads(row[0])["outcome"] == "pending"]
        assert len(pending) == 1
        assert pending[0]["checkpoint"] == "EXTRACTED"
        assert pending[0]["issues"] == ["RECONCILIATION_REQUIRED"]
        assert lib.db.execute("SELECT COUNT(*) FROM records WHERE model='PageObservation'").fetchone()[0] == 2
        assert lib.get("owner_a", "ReadingTrace", trace["id"]) == corrected
        assert len(lib.pending_events("owner_a")) == initial_events
        def should_not_run(_raw):
            raise AssertionError("already recorded candidate must not be re-extracted")
        with pytest.raises(LibrarianError) as retry:
            process_capture(lib, "owner_a", capture_id, should_not_run,
                            extractor_version="vision-v2")
        assert retry.value.code == "RECONCILIATION_REQUIRED"


def test_explicit_session_yields_resolved_trace_and_default_search(tmp_path: Path):
    created = "2026-09-28T00:00:00+00:00"
    with Library(tmp_path) as lib:
        lib.register("owner_a", {"object_type": "Work", "schema_version": "0.1.0",
                   "id": "work_one", "owner_id": "owner_a", "created_at": created,
                   "title": "Synthetic book", "original_title": None, "authors": [],
                   "identifiers": [], "revision": 1, "supersedes_revision": None})
        lib.register("owner_a", {"object_type": "Edition", "schema_version": "0.1.0",
                   "id": "edition_one", "owner_id": "owner_a", "created_at": created,
                   "work_id": "work_one", "edition_label": None, "publisher": None,
                   "publication_year": None, "isbn": {"isbn13": None, "isbn10": None},
                   "language": None, "page_count": None, "volume_label": None,
                   "revision": 1, "supersedes_revision": None})
        lib.register("owner_a", {"object_type": "BookInstance", "schema_version": "0.1.0",
                   "id": "bookinst_one", "owner_id": "owner_a", "created_at": created,
                   "edition_id": "edition_one", "medium": "physical",
                   "acquired_at": {"value": None, "confidence": None, "basis": "unknown"},
                   "ownership_status": "owned", "physical": {"qr_id": None, "shelf": None},
                   "reading_status": {"state": "reading", "current_page": None,
                                      "progress_evidence_ref": None},
                   "revision": 1, "supersedes_revision": None})
        session = lib.start_session("owner_a", "bookinst_one", scope=("gateway", "a", "c"))
        receipt = lib.ingest("owner_a", transport="gateway", account_id="a",
                             conversation_id="c", source_event_id="m",
                             attachments=[{"source_item_id": "i", "mime_type": "image/png",
                                           "data": _photo()}], idempotency_key="k",
                             submitted_context={"session_id": session["id"]})
        traces = process_capture(lib, "owner_a", receipt["capture_ids"][0],
                                 lambda _: _output())
        assert all(t["context_state"] == "resolved" for t in traces)
        assert all(t["work_id"] == "work_one" and t["edition_id"] == "edition_one"
                   and t["book_instance_id"] == "bookinst_one" for t in traces)
        assert len(search(lib, "owner_a", "Parsons")) == 2
        inferred = lib.ingest("owner_a", transport="gateway", account_id="a",
                              conversation_id="c", source_event_id="m2",
                              attachments=[{"source_item_id": "i", "mime_type": "image/png",
                                            "data": _photo()}], idempotency_key="k2")
        inferred_traces = process_capture(lib, "owner_a", inferred["capture_ids"][0],
                                          lambda _: _output())
        assert all(t["session_id"] == session["id"] and t["context_state"] == "resolved"
                   for t in inferred_traces)
        original_capture = lib.get("owner_a", "PageCapture", inferred["capture_ids"][0])
        original_observation = lib.get("owner_a", "PageObservation",
                                       inferred_traces[0]["source"]["observation_id"])
        old_resolution = lib.get("owner_a", "CaptureResolution",
                                 inferred_traces[0]["source"]["resolution_id"])
        pages = json.loads(json.dumps(old_resolution["pages"]))
        pages[0]["page"] = {"value": {"label": "172", "number": 172,
                                       "scheme": "arabic"}, "confidence": None,
                            "basis": "user_statement", "status": "resolved"}
        resolution = resolve_capture(lib, "owner_a", inferred["capture_ids"][0], 1,
                                     pages=pages)
        assert resolution["revision"] == 2
        revised = lib.get("owner_a", "ReadingTrace", inferred_traces[0]["id"])
        assert revised["revision"] == 2 and revised["location"]["page"]["number"] == 172
        assert revised["source"]["resolution_revision"] == 2
        assert lib.get("owner_a", "PageCapture", inferred["capture_ids"][0]) == original_capture
        assert lib.get("owner_a", "PageObservation", original_observation["id"]) == original_observation
        with pytest.raises(LibrarianError) as error:
            resolve_capture(lib, "owner_a", inferred["capture_ids"][0], 1, pages=pages)
        assert error.value.code == "REVISION_CONFLICT"

        unresolved_receipt = lib.ingest("owner_a", transport="gateway", account_id="a",
                                        conversation_id="different-chat", source_event_id="m3",
                                        attachments=[{"source_item_id": "i", "mime_type": "image/png",
                                                      "data": _photo()}], idempotency_key="k3")
        unresolved_id = unresolved_receipt["capture_ids"][0]
        assert review_queues(lib, "owner_a")["resolution"] == []
        unresolved_trace = process_capture(lib, "owner_a", unresolved_id, lambda _: _output())[0]
        assert unresolved_trace["context_state"] == "unresolved"
        assert review_queues(lib, "owner_a")["resolution"][0]["captures"][0]["capture_id"] == unresolved_id
        resolve_capture(lib, "owner_a", unresolved_id, 1, session_id=session["id"])
        assert lib.get("owner_a", "ReadingTrace", unresolved_trace["id"])["context_state"] == "resolved"
        assert review_queues(lib, "owner_a")["resolution"] == []


def test_trace_semantics_reject_fake_resolved_context_and_review(tmp_path: Path):
    with Library(tmp_path) as lib:
        receipt = lib.ingest("owner_a", transport="gateway", account_id="a",
                             conversation_id="c", source_event_id="m",
                             attachments=[{"source_item_id": "i", "mime_type": "image/png",
                                           "data": _photo()}], idempotency_key="k")
        trace = process_capture(lib, "owner_a", receipt["capture_ids"][0],
                                lambda _: _output())[0]
        false_resolution = dict(trace, context_state="resolved")
        with pytest.raises(LibrarianError, match="full chain"):
            validate("ReadingTrace", false_resolution)
        false_review = json.loads(json.dumps(trace))
        false_review["review"] = {"required": False, "state": "pending", "reason": "unclear"}
        with pytest.raises(LibrarianError, match="pending review"):
            validate("ReadingTrace", false_review)


def test_observation_dimensions_follow_exif_oriented_original(tmp_path: Path):
    with Library(tmp_path) as lib:
        receipt = lib.ingest("owner_a", transport="gateway", account_id="a",
                             conversation_id="c", source_event_id="m",
                             attachments=[{"source_item_id": "i", "mime_type": "image/jpeg",
                                           "data": _rotated_photo()}], idempotency_key="k")
        capture_id = receipt["capture_ids"][0]
        with pytest.raises(LibrarianError, match="EXIF-oriented original"):
            process_capture(lib, "owner_a", capture_id, lambda _: _output())
        raw_ref = json.loads(lib.db.execute("SELECT raw_asset FROM extractor_attempts").fetchone()[0])
        assert (tmp_path / raw_ref["object_key"]).read_bytes() == _output()
        output = json.loads(_output())
        output["image_space"].update(width=1400, height=1000)
        assert len(process_capture(lib, "owner_a", capture_id,
                                   lambda _: json.dumps(output).encode())) == 2


def test_trace_crop_uses_oriented_original_and_stays_within_page(tmp_path: Path):
    source = Image.new("RGB", (1000, 600), "red")
    source.paste("blue", (0, 300, 1000, 600))
    exif = Image.Exif()
    exif[274] = 6
    stream = io.BytesIO()
    source.save(stream, format="JPEG", exif=exif)
    photo = stream.getvalue()
    output = json.loads(_output())
    output["image_space"].update(width=600, height=1000)
    output["pages"] = [
        {"id": "left", "bbox": [0, 0, .5, 1], "side": "left",
         "page": {"value": None, "confidence": None,
                  "basis": "unknown", "status": "unresolved"}},
        {"id": "right", "bbox": [.5, 0, 1, 1], "side": "right",
         "page": {"value": None, "confidence": None,
                  "basis": "unknown", "status": "unresolved"}},
    ]
    output["printed_regions"] = []
    output["annotations"] = []
    output["marks"] = [
        {**_detection("left_mark", "underline", None),
         "page_region_id": "left", "bbox": [.38, .2, .48, .4]},
        {**_detection("right_mark", "underline", None),
         "page_region_id": "right", "bbox": [.52, .2, .62, .4]},
    ]
    with Library(tmp_path) as lib:
        receipt = lib.ingest("owner_a", transport="gateway", account_id="a",
                             conversation_id="c", source_event_id="m",
                             attachments=[{"source_item_id": "i", "mime_type": "image/jpeg",
                                           "data": photo}], idempotency_key="k")
        traces = process_capture(lib, "owner_a", receipt["capture_ids"][0],
                                 lambda _: json.dumps(output).encode())
        assert len(traces) == 2
        assert {trace["location"]["page_region_id"] for trace in traces} == {"left", "right"}
        by_page = {trace["location"]["page_region_id"]: trace for trace in traces}
        for side, expected in (("left", "blue"), ("right", "red")):
            crop = render_trace_crop(lib, "owner_a", by_page[side]["id"], context=.25)
            with Image.open(io.BytesIO(crop)) as image:
                assert image.format == "PNG"
                pixel = image.getpixel((image.width // 2, image.height // 2))
                if expected == "blue":
                    assert pixel[2] > 200 and pixel[0] < 40
                else:
                    assert pixel[0] > 200 and pixel[2] < 40
                assert image.width <= 300
        with pytest.raises(LibrarianError) as error:
            render_trace_crop(lib, "owner_b", by_page["left"]["id"])
        assert error.value.code == "UNAUTHORIZED"
        with pytest.raises(LibrarianError, match="crop context"):
            render_trace_crop(lib, "owner_a", by_page["left"]["id"], context=float("nan"))


def test_opt_in_symbol_signal_and_important_content_review(tmp_path: Path):
    output = json.loads(_output())
    output["printed_regions"][0]["text"]["confidence"] = .5
    symbol = _detection("symbol_1", "symbol", "!!")
    symbol["text"]["confidence"] = .95
    symbol["confidence"] = .95
    output["symbols"] = [symbol]
    output["links"] = [{"from_id": "mark_1", "to_id": "symbol_1",
                        "kind": "annotates", "confidence": .95}]
    raw = json.dumps(output).encode()
    vocabulary = {"enabled": True, "version": "personal-v1",
                  "mappings": {"!!": "promote_candidate", "R": "reread_target"}}
    with Library(tmp_path) as lib:
        def capture(source: str) -> str:
            return lib.ingest("owner_a", transport="gateway", account_id="a",
                              conversation_id="c", source_event_id=source,
                              attachments=[{"source_item_id": "i", "mime_type": "image/png",
                                            "data": _photo()}], idempotency_key=source)["capture_ids"][0]
        disabled = process_capture(lib, "owner_a", capture("disabled"), lambda _: raw)
        assert all(not trace["intent_signals"] for trace in disabled)
        enabled = process_capture(lib, "owner_a", capture("enabled"), lambda _: raw,
                                  vocabulary=vocabulary)
        important = next(trace for trace in enabled if "symbol" in trace["trace_types"])
        assert important["intent_signals"] == ["promote_candidate"]
        assert important["vocabulary_version"] == "personal-v1"
        assert important["review"]["required"] is True
        assert important["review"]["state"] == "pending"
        assert important["attribution"]["mark_author"] == "unknown"
        assert all("reread_target" not in trace["intent_signals"] for trace in enabled)
        queues = review_queues(lib, "owner_a")
        assert len(queues["resolution"]) == 2
        assert len(queues["content"]) == 1
        assert queues["content"][0]["trace_id"] == important["id"]
        assert queues["content"][0]["evidence"] == important["provenance"]
        assert review_queues(lib, "owner_b") == {"resolution": [], "content": []}
        candidates = [json.loads(row[0]) for row in lib.db.execute(
            "SELECT body FROM records WHERE model='KnowledgeCandidate' AND current=1")]
        assert len(candidates) == 1
        assert candidates[0]["source_trace_refs"] == [{"trace_id": important["id"], "revision": 1}]
        assert candidates[0]["status"] == "pending"
        assert candidates[0]["content"]["text"] is None
        assert [event["event"] for event in lib.pending_events("owner_a")].count(
            "reading.knowledge_candidate.created") == 1
        corrected = correct_trace(lib, "owner_a", important["id"], 1,
                                  printed_text="Weber and Parsons",
                                  reason="user reviewed important content")
        assert corrected["review"]["state"] == "resolved"
        assert review_queues(lib, "owner_a")["content"] == []
        assert lib.get("owner_a", "KnowledgeCandidate", candidates[0]["id"])["status"] == "superseded"
        current_candidates = [json.loads(row[0]) for row in lib.db.execute(
            "SELECT body FROM records WHERE model='KnowledgeCandidate' AND current=1")]
        pending = [candidate for candidate in current_candidates if candidate["status"] == "pending"]
        assert len(pending) == 1
        assert pending[0]["source_trace_refs"] == [{"trace_id": important["id"], "revision": 2}]


def test_content_review_stays_pending_until_all_uncertain_fields_are_checked(tmp_path: Path):
    output = json.loads(_output())
    output["printed_regions"][0]["text"]["confidence"] = .5
    output["annotations"][0]["text"]["confidence"] = .4
    symbol = _detection("symbol_1", "symbol", "!!")
    symbol["text"]["confidence"] = .95
    symbol["confidence"] = .95
    output["symbols"] = [symbol]
    output["links"] = [
        {"from_id": "mark_1", "to_id": "symbol_1", "kind": "annotates", "confidence": .95},
        {"from_id": "mark_1", "to_id": "note_1", "kind": "annotates", "confidence": .95},
    ]
    vocabulary = {"enabled": True, "version": "personal-v1",
                  "mappings": {"!!": "promote_candidate"}}
    with Library(tmp_path) as lib:
        receipt = lib.ingest("owner_a", transport="gateway", account_id="a",
                             conversation_id="c", source_event_id="review",
                             attachments=[{"source_item_id": "i", "mime_type": "image/png",
                                           "data": _photo()}], idempotency_key="review")
        trace = process_capture(lib, "owner_a", receipt["capture_ids"][0],
                                lambda _: json.dumps(output).encode(), vocabulary=vocabulary)[0]
        assert trace["review"]["state"] == "pending"
        first = correct_trace(lib, "owner_a", trace["id"], 1,
                              printed_text="Weber and Parsons", reason="checked print")
        assert first["review"]["state"] == "pending"
        assert review_queues(lib, "owner_a")["content"][0]["revision"] == 2
        second = correct_trace(lib, "owner_a", trace["id"], 2,
                               annotation="Parsons?", reason="checked margin")
        assert second["review"]["state"] == "resolved"
        assert review_queues(lib, "owner_a")["content"] == []


def test_user_resolution_before_extraction_survives_processing(tmp_path: Path):
    with Library(tmp_path) as lib:
        session = lib.start_session("owner_a")
        receipt = lib.ingest("owner_a", transport="gateway", account_id="a",
                             conversation_id="c", source_event_id="m",
                             attachments=[{"source_item_id": "i", "mime_type": "image/png",
                                           "data": _photo()}], idempotency_key="k")
        capture_id = receipt["capture_ids"][0]
        first = resolve_capture(lib, "owner_a", capture_id, None,
                                session_id=session["id"])
        assert first["revision"] == 1
        traces = process_capture(lib, "owner_a", capture_id, lambda _: _output())
        resolution = lib.get("owner_a", "CaptureResolution", first["id"])
        assert resolution["revision"] == 2
        assert resolution["session"]["value"] == session["id"]
        assert resolution["session"]["basis"] == "user_confirmation"
        assert all(trace["source"]["resolution_id"] == first["id"] and
                   trace["source"]["resolution_revision"] == 2 for trace in traces)
        assert lib.get("owner_a", "PageCapture", capture_id)["submitted_context"]["session_id"] is None
