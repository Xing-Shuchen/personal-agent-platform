from __future__ import annotations

import json
from pathlib import Path

import pytest

from agents.librarian.runtime.pipeline import correct_trace, process_capture, rebuild_index, search
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


def test_synthetic_observation_to_provenance_search_and_rebuild(tmp_path: Path):
    with Library(tmp_path) as lib:
        receipt = lib.ingest("owner_a", transport="gateway", account_id="account",
                             conversation_id="chat", source_event_id="message-1",
                             attachments=[{"source_item_id": "image-1",
                                           "mime_type": "image/jpeg", "data": b"fixture photo"}],
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


def test_invalid_extraction_keeps_raw_output_without_trace(tmp_path: Path):
    with Library(tmp_path) as lib:
        receipt = lib.ingest("owner_a", transport="gateway", account_id="a",
                             conversation_id="c", source_event_id="m",
                             attachments=[{"source_item_id": "i", "mime_type": "image/jpeg",
                                           "data": b"photo"}], idempotency_key="k")
        with pytest.raises(LibrarianError) as err:
            process_capture(lib, "owner_a", receipt["capture_ids"][0], lambda _: b"{broken")
        assert err.value.code == "EXTRACTION_SCHEMA_INVALID"
        row = lib.db.execute("SELECT raw_asset,error_code FROM extractor_attempts").fetchone()
        assert row["error_code"] == "EXTRACTION_SCHEMA_INVALID"
        ref = json.loads(row["raw_asset"])
        assert (tmp_path / ref["object_key"]).read_bytes() == b"{broken"
        assert lib.db.execute("SELECT COUNT(*) FROM records WHERE model='ReadingTrace'").fetchone()[0] == 0


def test_invalid_cross_page_link_is_rejected(tmp_path: Path):
    output = json.loads(_output())
    output["marks"][0]["linked_text_region_ids"] = ["missing"]
    with Library(tmp_path) as lib:
        receipt = lib.ingest("owner_a", transport="gateway", account_id="a",
                             conversation_id="c", source_event_id="m",
                             attachments=[{"source_item_id": "i", "mime_type": "image/jpeg",
                                           "data": b"photo"}], idempotency_key="k")
        with pytest.raises(LibrarianError) as err:
            process_capture(lib, "owner_a", receipt["capture_ids"][0],
                            lambda _: json.dumps(output).encode())
        assert err.value.code == "EXTRACTION_SCHEMA_INVALID"


def test_explicit_annotation_link_groups_trace_without_inventing_authorship(tmp_path: Path):
    output = json.loads(_output())
    output["links"] = [{"from_id": "mark_1", "to_id": "note_1",
                        "kind": "annotates", "confidence": .95}]
    with Library(tmp_path) as lib:
        receipt = lib.ingest("owner_a", transport="gateway", account_id="a",
                             conversation_id="c", source_event_id="m",
                             attachments=[{"source_item_id": "i", "mime_type": "image/jpeg",
                                           "data": b"photo"}], idempotency_key="k")
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
                             attachments=[{"source_item_id": "i", "mime_type": "image/jpeg",
                                           "data": b"photo"}], idempotency_key="k")
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
                             attachments=[{"source_item_id": "i", "mime_type": "image/jpeg",
                                           "data": b"photo"}], idempotency_key="k",
                             submitted_context={"session_id": session["id"]})
        traces = process_capture(lib, "owner_a", receipt["capture_ids"][0],
                                 lambda _: _output())
        assert all(t["context_state"] == "resolved" for t in traces)
        assert all(t["work_id"] == "work_one" and t["edition_id"] == "edition_one"
                   and t["book_instance_id"] == "bookinst_one" for t in traces)
        assert len(search(lib, "owner_a", "Parsons")) == 2
        inferred = lib.ingest("owner_a", transport="gateway", account_id="a",
                              conversation_id="c", source_event_id="m2",
                              attachments=[{"source_item_id": "i", "mime_type": "image/jpeg",
                                            "data": b"second photo"}], idempotency_key="k2")
        inferred_traces = process_capture(lib, "owner_a", inferred["capture_ids"][0],
                                          lambda _: _output())
        assert all(t["session_id"] == session["id"] and t["context_state"] == "resolved"
                   for t in inferred_traces)


def test_trace_semantics_reject_fake_resolved_context_and_review(tmp_path: Path):
    with Library(tmp_path) as lib:
        receipt = lib.ingest("owner_a", transport="gateway", account_id="a",
                             conversation_id="c", source_event_id="m",
                             attachments=[{"source_item_id": "i", "mime_type": "image/jpeg",
                                           "data": b"photo"}], idempotency_key="k")
        trace = process_capture(lib, "owner_a", receipt["capture_ids"][0],
                                lambda _: _output())[0]
        false_resolution = dict(trace, context_state="resolved")
        with pytest.raises(LibrarianError, match="full chain"):
            validate("ReadingTrace", false_resolution)
        false_review = json.loads(json.dumps(trace))
        false_review["review"] = {"required": False, "state": "pending", "reason": "unclear"}
        with pytest.raises(LibrarianError, match="pending review"):
            validate("ReadingTrace", false_review)
