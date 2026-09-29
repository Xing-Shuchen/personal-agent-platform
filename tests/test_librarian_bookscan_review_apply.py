"""A complete local web review must enter the versioned domain path."""
from __future__ import annotations

import io
import json

import pytest
from PIL import Image

from agents.librarian.runtime.bookscan_adapter import adapt_report
from agents.librarian.runtime.bookscan_review_apply import (apply_review,
                                                             prepare_review, review_context)
from agents.librarian.runtime.handwriting_review import review_handwriting
from agents.librarian.runtime.pipeline import ExtractionOutput, process_capture
from agents.librarian.runtime.store import Library, LibrarianError


def _setup(lib: Library) -> tuple[str, dict]:
    image = io.BytesIO()
    Image.new("RGB", (100, 100), "white").save(image, format="PNG")
    picture = image.getvalue()
    receipt = lib.ingest("owner", transport="gateway", account_id="account",
                         conversation_id="chat", source_event_id="event",
                         idempotency_key="command", attachments=[
                             {"source_item_id": "one", "mime_type": "image/png",
                              "data": picture}])
    capture_id = receipt["capture_ids"][0]
    page_id = "page-one"
    report = {
        "run": {"run_id": "run-bookscan-one"},
        "pages": [{"page_id": page_id, "source_size": [100, 100],
                   "processing_status": "processed", "issues": [],
                   "page_number": {"status": "unknown", "observed_value": None,
                                   "observed_label": None}}],
        "lines": [
            {"line_id": "line-one", "page_id": page_id, "mark_type": "underline",
             "line_bbox": [10, 10, 90, 25], "ocr_raw": "正是帕森斯", "ocr_score": .8},
            {"line_id": "line-two", "page_id": page_id, "mark_type": "underline",
             "line_bbox": [10, 35, 90, 50], "ocr_raw": "误检", "ocr_score": .7},
        ],
        "groups": [
            {"group_id": "group-one", "page_id": page_id,
             "line_ids": ["line-one"], "group_bbox": [10, 10, 90, 25],
             "underline_bboxes": [[10, 23, 90, 26]], "mark_type": "underline",
             "match_status": "needs_review", "ocr_raw": "正是帕森斯",
             "text_effective": "正是帕森斯"},
            {"group_id": "group-two", "page_id": page_id,
             "line_ids": ["line-two"], "group_bbox": [10, 35, 90, 50],
             "underline_bboxes": [[10, 48, 90, 51]], "mark_type": "underline",
             "match_status": "needs_review", "ocr_raw": "误检",
             "text_effective": "误检"},
        ],
        "annotations": [{"annotation_id": "note-one", "page_id": page_id,
                         "bbox": [5, 55, 45, 72], "ocr_raw": "旁注？",
                         "ocr_score": None}],
        "review_candidates": [], "failures": [],
    }
    observation = adapt_report(report, 100, 100)
    created = process_capture(
        lib, "owner", capture_id,
        lambda _: ExtractionOutput(raw=json.dumps(report).encode(), derivative=picture,
                                   derivative_width=100, derivative_height=100,
                                   operations=("exif_transpose",),
                                   observation=json.dumps(observation).encode()),
        extractor_version="bookscan-test")
    assert len(created) == 3
    bundle = {"run_id": "run-bookscan-one", "pages": {
        page_id: {"complete": True, "pageNumber": "39",
                  "lines": {"line-one": {"decision": "accepted", "text": ""},
                            "line-two": {"decision": "rejected", "text": ""}},
                  "missing": [{"bbox": [10, 78, 90, 90],
                               "text": "新增的完整划线句子。"}]},
        "groups": {"group-one": {"decision": "accepted",
                                 "text": "正是帕森斯，在20世纪30年代。"},
                   "group-two": {"decision": "rejected", "text": ""}},
        "annotations": {"note-one": {"decision": "accepted", "text": "人工旁注"}},
    }}
    return capture_id, bundle


def test_complete_review_versions_rejections_corrections_and_missing_mark(tmp_path):
    with Library(tmp_path) as lib:
        capture_id, bundle = _setup(lib)
        plan = prepare_review(lib, "owner", bundle)
        assert len(plan["reviewed_candidates"]) == 3
        result = apply_review(lib, "owner", bundle)
        assert result["status"] == "applied"
        assert result["capture_id"] == capture_id
        reviewed_observation = next(json.loads(row[0]) for row in lib.db.execute(
            "SELECT body FROM records WHERE owner_id='owner' AND model='PageObservation' "
            "AND current=1") if json.loads(row[0])["processing_run_id"] == result["run_id"])
        raw = json.loads(lib._read_object(reviewed_observation["raw_output_asset"]))
        assert raw["review_bundle"]["run_id"] == bundle["run_id"]
        assert reviewed_observation.get("derivative") is None
        rows = [json.loads(row[0]) for row in lib.db.execute(
            "SELECT body FROM records WHERE owner_id='owner' AND model='ReadingTrace' "
            "AND current=1")]
        assert len([row for row in rows if row["status"] == "active"]) == 3
        assert len([row for row in rows if row["status"] == "superseded"]) == 3
        active = [row for row in rows if row["status"] == "active"]
        assert all(row["review"]["state"] == "resolved" for row in active)
        assert all(row["location"]["page"]["number"] == 39 for row in active)
        assert {row["content"]["printed_text"]["text"] for row in active} == {
            "正是帕森斯，在20世纪30年代。", "新增的完整划线句子。", None}
        assert any(row["content"]["annotation"]["text"] == "人工旁注" for row in active)
        assert apply_review(lib, "owner", bundle)["status"] == "already_applied"
        context = review_context(lib, "owner", bundle["run_id"])
        revised_bundle = json.loads(json.dumps(bundle))
        revised_bundle.update(context)
        revised_bundle["pages"]["groups"]["group-one"]["text"] = \
            "正是帕森斯，第二次人工校正。"
        second = apply_review(lib, "owner", revised_bundle)
        assert second["status"] == "applied"
        assert second["run_id"] != result["run_id"]
        current = [json.loads(row[0]) for row in lib.db.execute(
            "SELECT body FROM records WHERE owner_id='owner' AND model='ReadingTrace' "
            "AND current=1")]
        assert any(row["content"]["printed_text"]["text"] ==
                   "正是帕森斯，第二次人工校正。" for row in current)
        with pytest.raises(LibrarianError) as stale:
            apply_review(lib, "owner", bundle)
        assert stale.value.code == "REVISION_CONFLICT"


def test_incomplete_review_rejected_without_domain_changes(tmp_path):
    with Library(tmp_path) as lib:
        capture_id, bundle = _setup(lib)
        bundle["pages"]["groups"]["group-one"]["decision"] = ""
        with pytest.raises(LibrarianError) as error:
            apply_review(lib, "owner", bundle)
        assert error.value.code == "VALIDATION_FAILED"
        runs = [json.loads(row[0]) for row in lib.db.execute(
            "SELECT body FROM records WHERE owner_id='owner' AND model='ProcessingRun' "
            "AND current=1")]
        assert len(runs) == 1


def test_line_edit_requires_approved_group_quote(tmp_path):
    with Library(tmp_path) as lib:
        _, bundle = _setup(lib)
        bundle["pages"]["page-one"]["lines"]["line-one"]["text"] = "新行文字"
        bundle["pages"]["groups"]["group-one"]["text"] = ""
        with pytest.raises(LibrarianError) as error:
            prepare_review(lib, "owner", bundle)
        assert error.value.code == "VALIDATION_FAILED"


def test_review_reconciliation_event_failure_keeps_old_traces_and_retries(tmp_path,
                                                                          monkeypatch):
    with Library(tmp_path) as lib:
        capture_id, bundle = _setup(lib)
        old = [json.loads(row[0]) for row in lib.db.execute(
            "SELECT body FROM records WHERE owner_id='owner' AND model='ReadingTrace' "
            "AND current=1")]
        old_refs = {(trace["id"], trace["revision"]) for trace in old}
        original_event = lib._event

        def fail_correction(owner_id, kind, *args, **kwargs):
            if kind == "reading.trace.corrected":
                raise RuntimeError("outbox unavailable")
            return original_event(owner_id, kind, *args, **kwargs)

        monkeypatch.setattr(lib, "_event", fail_correction)
        with pytest.raises(RuntimeError, match="outbox unavailable"):
            apply_review(lib, "owner", bundle)
        current = [json.loads(row[0]) for row in lib.db.execute(
            "SELECT body FROM records WHERE owner_id='owner' AND model='ReadingTrace' "
            "AND current=1")]
        assert {(trace["id"], trace["revision"]) for trace in current} == old_refs
        assert all(trace["status"] == "active" for trace in current)
        assert not any(event["event"] == "reading.trace.corrected"
                       for event in lib.pending_events("owner"))

        monkeypatch.setattr(lib, "_event", original_event)
        applied = apply_review(lib, "owner", bundle)
        assert applied["status"] == "applied" and applied["capture_id"] == capture_id
        corrected = [event for event in lib.pending_events("owner")
                     if event["event"] == "reading.trace.corrected"]
        assert len(corrected) == len(old)


def _note_trace(lib: Library) -> dict:
    return next(json.loads(row[0]) for row in lib.db.execute(
        "SELECT body FROM records WHERE owner_id='owner' AND model='ReadingTrace' "
        "AND current=1") if "margin_note" in json.loads(row[0])["trace_types"])


def test_handwriting_only_confirmation_preserves_printed_traces(tmp_path):
    with Library(tmp_path) as lib:
        _setup(lib)
        note = _note_trace(lib)
        printed_before = {json.loads(row[0])["id"]: json.loads(row[0])["revision"]
                          for row in lib.db.execute(
                              "SELECT body FROM records WHERE model='ReadingTrace' AND current=1")
                          if "margin_note" not in json.loads(row[0])["trace_types"]}
        decision = {"trace_id": note["id"], "expected_revision": 1,
                    "decision": "accepted", "text": "人工核对的手写内容"}
        assert review_handwriting(lib, "owner", decision)["status"] == "applied"
        confirmed = lib.get("owner", "ReadingTrace", note["id"])
        assert confirmed["revision"] == 2 and confirmed["review"]["state"] == "resolved"
        assert confirmed["content"]["annotation"] == {
            "text": "人工核对的手写内容", "confidence": None, "basis": "user_statement"}
        assert review_handwriting(lib, "owner", decision)["status"] == "already_applied"
        edited = review_handwriting(lib, "owner", {**decision, "expected_revision": 2,
                                                   "text": "再校正的手写内容"})
        assert edited["revision"] == 3
        printed_after = {json.loads(row[0])["id"]: json.loads(row[0])["revision"]
                         for row in lib.db.execute(
                             "SELECT body FROM records WHERE model='ReadingTrace' AND current=1")
                         if "margin_note" not in json.loads(row[0])["trace_types"]}
        assert printed_after == printed_before


def test_handwriting_only_rejection_removes_note_without_touching_printed_marks(tmp_path):
    with Library(tmp_path) as lib:
        _setup(lib)
        note = _note_trace(lib)
        decision = {"trace_id": note["id"], "expected_revision": 1,
                    "decision": "rejected", "text": ""}
        review_handwriting(lib, "owner", decision)
        rejected = lib.get("owner", "ReadingTrace", note["id"])
        assert rejected["status"] == "superseded"
        assert rejected["review"]["state"] == "resolved"
        assert review_handwriting(lib, "owner", decision)["status"] == "already_applied"
        with pytest.raises(LibrarianError) as conflict:
            review_handwriting(lib, "owner", {**decision, "decision": "accepted", "text": "反悔"})
        assert conflict.value.code == "REVISION_CONFLICT"
        active = [json.loads(row[0]) for row in lib.db.execute(
            "SELECT body FROM records WHERE model='ReadingTrace' AND current=1")
                  if json.loads(row[0])["status"] == "active"]
        assert len(active) == 2 and all("margin_note" not in row["trace_types"] for row in active)
        restored = review_handwriting(lib, "owner", {"trace_id": note["id"],
            "expected_revision": 2, "decision": "accepted", "text": "重新确认的手写笔记"})
        assert restored["revision"] == 3
        assert lib.get("owner", "ReadingTrace", note["id"])["status"] == "active"
