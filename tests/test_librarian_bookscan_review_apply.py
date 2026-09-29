"""A complete local web review must enter the versioned domain path."""
from __future__ import annotations

import io
import json

import pytest
from PIL import Image

from agents.librarian.runtime.bookscan_adapter import adapt_report
from agents.librarian.runtime.bookscan_review_apply import (apply_review,
                                                             prepare_review, review_context)
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
