from pathlib import Path

import pytest

from agents.librarian.runtime.gateway_review_decision import record_review_decision
from agents.librarian.runtime.gateway_review_finalize import (
    auto_reconcile_fully_reviewed, finalize_review)
from agents.librarian.runtime.gateway_review import _reviewable_ocr_gaps, pending_extractions
from agents.librarian.runtime.pipeline import process_capture
from agents.librarian.runtime.store import Library, LibrarianError
import io
import json
from PIL import Image


def test_bookscan_review_candidate_uses_source_coordinates() -> None:
    observation = {"image_space": {"width": 1000, "height": 2000}}
    raw = {"review_candidates": [{"bbox": [200, 600, 700, 700],
                                  "reason": "unassigned_ink"}]}
    gaps = _reviewable_ocr_gaps(raw, observation)
    assert len(gaps) == 1
    assert gaps[0]["bbox"] == [.2, .3, .7, .35]
    assert gaps[0]["reason"] == "unassigned_ink"


def test_review_decision_is_source_linked_idempotent_and_does_not_promote(
        tmp_path: Path, monkeypatch) -> None:
    def detail(_lib, owner, capture):
        assert (owner, capture) == ("owner", "capture_one")
        return {"pending_run_id": "run_current", "proposed": [
            {"candidate_id": "candidate_" + "a" * 24}]}
    monkeypatch.setattr("agents.librarian.runtime.gateway_review_decision.pending_extractions",
                        detail)
    request = {"owner_id": "owner", "actor_id": "person",
               "source": {"transport": "feishu", "account_id": "bot",
                          "conversation_id": "chat", "source_event_id": "msg-1"},
               "capture_id": "capture_one", "pending_run_id": "run_current",
               "candidate_id": "candidate_" + "a" * 24, "decision": "accept"}
    with Library(tmp_path) as lib:
        first = record_review_decision(lib, request)
        assert first["status"] == "recorded"
        assert first["trace_status"] == "pending_reconciliation"
        assert record_review_decision(lib, request)["status"] == "unchanged"
        count = lib.db.execute("SELECT count(*) FROM gateway_review_decisions").fetchone()[0]
        assert count == 1
        assert lib.db.execute("SELECT count(*) FROM records WHERE model='ReadingTrace'").fetchone()[0] == 0
        with pytest.raises(LibrarianError) as error:
            record_review_decision(lib, {**request, "decision": "reject"})
        assert error.value.code == "IDEMPOTENCY_CONFLICT"
        with pytest.raises(LibrarianError) as error:
            record_review_decision(lib, {**request, "pending_run_id": "run_old",
                                         "source": {**request["source"],
                                                    "source_event_id": "msg-2"}})
        assert error.value.code == "REVISION_CONFLICT"


def test_complete_review_reconciles_through_versioned_pipeline(tmp_path: Path) -> None:
    image = io.BytesIO()
    Image.new("RGB", (1000, 1400), "white").save(image, "PNG")

    def observation(two: bool) -> bytes:
        prints = []
        marks = []
        for index, top in enumerate(([.1, .5] if two else [.1]), 1):
            box = [.1, top, .7, top + .05]
            prints.append({"id": f"printed_{index}", "page_region_id": "page_1",
                           "bbox": box, "kind": "printed",
                           "text": {"text": f"Printed sentence {index}.",
                                    "confidence": .95, "basis": "vision"},
                           "confidence": .95, "linked_text_region_ids": [],
                           "link_confidence": None})
            marks.append({"id": f"underline_{index}", "page_region_id": "page_1",
                          "bbox": [.1, top + .05, .7, top + .06],
                          "kind": "underline", "text": None, "confidence": .9,
                          "linked_text_region_ids": [f"printed_{index}"],
                          "link_confidence": .95})
        return json.dumps({"image_space": {"width": 1000, "height": 1400,
                                           "basis": "exif_oriented_original"},
                           "pages": [{"id": "page_1", "bbox": [0, 0, 1, 1],
                                      "side": "unknown", "page": {"value": {
                                          "label": "39", "number": 39, "scheme": "arabic"},
                                          "confidence": .95, "basis": "vision",
                                          "status": "resolved"}}],
                           "printed_regions": prints, "marks": marks,
                           "annotations": [], "symbols": [], "links": [],
                           "warnings": []}).encode()

    with Library(tmp_path) as lib:
        receipt = lib.ingest("owner", transport="feishu", account_id="bot",
                             conversation_id="chat", source_event_id="photo",
                             attachments=[{"source_item_id": "photo:0", "mime_type": "image/png",
                                           "data": image.getvalue()}], idempotency_key="photo")
        capture = receipt["capture_ids"][0]
        old = process_capture(lib, "owner", capture, lambda _: observation(False),
                              extractor_version="v1")
        with pytest.raises(LibrarianError) as error:
            process_capture(lib, "owner", capture, lambda _: observation(True),
                            extractor_version="v2")
        assert error.value.code == "RECONCILIATION_REQUIRED"
        detail = pending_extractions(lib, "owner", capture)
        assert len(detail["proposed"]) == 2
        for index, candidate in enumerate(detail["proposed"]):
            record_review_decision(lib, {"owner_id": "owner", "actor_id": "person",
                                    "source": {"transport": "feishu", "account_id": "bot",
                                               "conversation_id": "chat",
                                               "source_event_id": f"review-{index}"},
                                    "capture_id": capture,
                                    "pending_run_id": detail["pending_run_id"],
                                    "candidate_id": candidate["candidate_id"],
                                    "decision": "accept" if index == 0 else "reject",
                                    "corrected_text": "User confirmed sentence." if index == 0 else None})
            if index == 0:
                with pytest.raises(LibrarianError) as error:
                    finalize_review(lib, {"owner_id": "owner", "actor_id": "person",
                                          "source": {"transport": "feishu", "account_id": "bot",
                                                     "conversation_id": "chat",
                                                     "source_event_id": "too-early"},
                                          "capture_id": capture,
                                          "pending_run_id": detail["pending_run_id"],
                                          "expected_current": [{"trace_id": item["trace_id"],
                                                                "revision": item["revision"]}
                                                               for item in detail["current"]],
                                          "replace_all_current": True})
                assert error.value.code == "RECONCILIATION_REQUIRED"
        approval = {"owner_id": "owner", "actor_id": "person",
                    "source": {"transport": "feishu", "account_id": "bot",
                               "conversation_id": "chat", "source_event_id": "replace-all"},
                    "capture_id": capture, "pending_run_id": detail["pending_run_id"],
                    "expected_current": [{"trace_id": item["trace_id"],
                                          "revision": item["revision"]}
                                         for item in detail["current"]],
                    "replace_all_current": True}
        assert auto_reconcile_fully_reviewed(lib, "owner", capture) is None
        result = finalize_review(lib, approval)
        assert (result["accepted"], result["rejected"]) == (1, 1)
        assert finalize_review(lib, approval) == result
        assert lib.get("owner", "ReadingTrace", old[0]["id"])["status"] == "superseded"
        new = lib.get("owner", "ReadingTrace", result["trace_refs"][0]["trace_id"])
        assert new["content"]["printed_text"] == {
            "text": "User confirmed sentence.", "confidence": None,
            "basis": "user_statement"}
        assert pending_extractions(lib, "owner")["pending"] == []


def test_reviewed_margin_note_correction_stays_an_annotation(tmp_path: Path) -> None:
    image = io.BytesIO()
    Image.new("RGB", (1000, 1400), "white").save(image, "PNG")

    def observation(with_note: bool) -> bytes:
        note = {"id": "note_1", "page_region_id": "page_1",
                "bbox": [.03, .4, .2, .5], "kind": "margin_note",
                "text": {"text": "uncertain handwriting", "confidence": .5,
                         "basis": "vision"}, "confidence": .8,
                "linked_text_region_ids": [], "link_confidence": None}
        return json.dumps({
            "image_space": {"width": 1000, "height": 1400,
                            "basis": "exif_oriented_original"},
            "pages": [{"id": "page_1", "bbox": [0, 0, 1, 1], "side": "unknown",
                       "page": {"value": {"label": "23", "number": 23,
                                          "scheme": "arabic"}, "confidence": .95,
                                "basis": "vision", "status": "resolved"}}],
            "printed_regions": [{"id": "printed_1", "page_region_id": "page_1",
                                 "bbox": [.2, .1, .7, .15], "kind": "printed",
                                 "text": {"text": "A complete printed sentence.",
                                          "confidence": .95, "basis": "vision"},
                                 "confidence": .95, "linked_text_region_ids": [],
                                 "link_confidence": None}],
            "marks": [{"id": "underline_1", "page_region_id": "page_1",
                       "bbox": [.2, .15, .7, .16], "kind": "underline",
                       "text": None, "confidence": .9,
                       "linked_text_region_ids": ["printed_1"],
                       "link_confidence": .95}],
            "annotations": [note] if with_note else [], "symbols": [],
            "links": [], "warnings": []}).encode()

    with Library(tmp_path) as lib:
        receipt = lib.ingest("owner", transport="feishu", account_id="bot",
                             conversation_id="chat", source_event_id="photo",
                             attachments=[{"source_item_id": "photo:0", "mime_type": "image/png",
                                           "data": image.getvalue()}], idempotency_key="photo")
        capture = receipt["capture_ids"][0]
        process_capture(lib, "owner", capture, lambda _: observation(False),
                        extractor_version="v1")
        with pytest.raises(LibrarianError) as error:
            process_capture(lib, "owner", capture, lambda _: observation(True),
                            extractor_version="v2")
        assert error.value.code == "RECONCILIATION_REQUIRED"
        detail = pending_extractions(lib, "owner", capture)
        assert len(detail["proposed"]) == 2
        for index, candidate in enumerate(detail["proposed"]):
            note = candidate["types"] == ["margin_note"]
            record_review_decision(lib, {"owner_id": "owner", "actor_id": "person",
                                    "source": {"transport": "feishu", "account_id": "bot",
                                               "conversation_id": "chat",
                                               "source_event_id": f"review-{index}"},
                                    "capture_id": capture,
                                    "pending_run_id": detail["pending_run_id"],
                                    "candidate_id": candidate["candidate_id"],
                                    "decision": "accept",
                                    "corrected_text": "User confirmed handwriting" if note else None})
        result = finalize_review(lib, {
            "owner_id": "owner", "actor_id": "person",
            "source": {"transport": "feishu", "account_id": "bot",
                       "conversation_id": "chat", "source_event_id": "replace-all"},
            "capture_id": capture, "pending_run_id": detail["pending_run_id"],
            "expected_current": [{"trace_id": item["trace_id"],
                                  "revision": item["revision"]}
                                 for item in detail["current"]],
            "replace_all_current": True})
        assert (result["accepted"], result["rejected"]) == (2, 0)
        traces = [lib.get("owner", "ReadingTrace", ref["trace_id"])
                  for ref in result["trace_refs"]]
        note_trace = next(trace for trace in traces
                          if trace["trace_types"] == ["margin_note"])
        assert note_trace["content"]["annotation"] == {
            "text": "User confirmed handwriting", "confidence": None,
            "basis": "user_statement"}
        assert note_trace["content"]["printed_text"]["text"] is None
