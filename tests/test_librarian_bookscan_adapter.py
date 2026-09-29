from __future__ import annotations

import io
import json

import pytest
from PIL import Image

from agents.librarian.runtime.bookscan_adapter import _manifest_entry, adapt_report
from agents.librarian.runtime.pipeline import process_capture
from agents.librarian.runtime.store import Library


def report() -> dict:
    return {
        "pages": [{"processing_status": "processed", "issues": [],
                   "page_number": {"status": "observed", "observed_value": 39,
                                   "observed_label": "39"}}],
        "lines": [{"line_id": "l1", "ocr_raw": "正是帕森斯", "ocr_score": .8},
                  {"line_id": "l2", "ocr_raw": "社会学思想的核心部分", "ocr_score": .7}],
        "groups": [{"group_id": "g1", "line_ids": ["l1"], "group_bbox": [10, 10, 90, 25],
                    "underline_bboxes": [[15, 23, 85, 26]], "mark_type": "underline",
                    "match_status": "matched", "epub_expanded_text": "正是帕森斯，后面还有照片外的词。"},
                   {"group_id": "g2", "line_ids": ["l2"], "group_bbox": [10, 40, 90, 55],
                    "underline_bboxes": [[15, 53, 85, 56]], "mark_type": "underline",
                    "match_status": "needs_review"}],
        "annotations": [{"bbox": [5, 60, 40, 80], "ocr_raw": "旁注？",
                         "ocr_score": None}],
        "review_candidates": [], "failures": [],
    }


def test_bookscan_groups_map_to_separate_traces_without_epub_only_words(tmp_path):
    payload = adapt_report(report(), 100, 100)
    assert len(payload["marks"]) == 2
    assert payload["printed_regions"][0]["text"]["text"] == "正是帕森斯"
    assert payload["marks"][0]["linked_text_region_ids"] == ["bookscan_0_text"]
    assert payload["pages"][0]["page"]["value"]["number"] == 39
    stream = io.BytesIO()
    Image.new("RGB", (100, 100), "white").save(stream, format="PNG")
    with Library(tmp_path) as lib:
        receipt = lib.ingest("owner", transport="gateway", account_id="account",
                             conversation_id="chat", source_event_id="event",
                             idempotency_key="idempotency", attachments=[
                                 {"source_item_id": "one", "mime_type": "image/png",
                                  "data": stream.getvalue()}])
        traces = process_capture(lib, "owner", receipt["capture_ids"][0],
                                 lambda _: json.dumps(payload, ensure_ascii=False).encode(),
                                 extractor_version="bookscan-test")
        assert len(traces) == 3
        assert {trace["content"]["printed_text"]["text"] for trace in traces} == {
            "正是帕森斯", "社会学思想的核心部分", None}


def test_bookscan_unknown_page_and_invalid_source_box():
    source = report()
    source["pages"][0]["page_number"] = {"status": "inferred", "observed_value": None}
    assert adapt_report(source, 100, 100)["pages"][0]["page"]["value"] is None
    source["groups"][0]["group_bbox"] = [10, 10, 101, 25]
    with pytest.raises(ValueError, match="bbox"):
        adapt_report(source, 100, 100)


def test_unrecognized_image_uses_full_frame_without_manual_regions():
    stream = io.BytesIO()
    Image.new("RGB", (90, 120), "white").save(stream, format="PNG")
    entry = _manifest_entry(stream.getvalue(), (90, 120))
    assert entry == {"file": "capture.png", "rotation": 0,
                     "valid_page_roi": [0, 0, 90, 120],
                     "annotation_regions": [], "bracket_regions": []}
