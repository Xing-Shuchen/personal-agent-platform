from __future__ import annotations

import io
import json
from pathlib import Path

import pytest
from PIL import Image

from agents.librarian.runtime.bookscan_adapter import _manifest_entry, adapt_report


def test_review_html_changes_do_not_change_processor_version(tmp_path, monkeypatch):
    from agents.librarian.runtime import bookscan_adapter as adapter
    source = tmp_path / "bookscan"
    source.mkdir()
    (source / "vision.py").write_text("processing-v1")
    review = source / "review.py"
    review.write_text("review-v1")
    evaluation = source / "evaluate.py"
    evaluation.write_text("evaluation-v1")
    config = tmp_path / "local-processing"
    config.mkdir()
    for name in ("config.yaml", "manifest.json", "inputs.sha256"):
        (config / name).write_text("baseline")
    monkeypatch.setattr(adapter, "REPO", tmp_path)
    monkeypatch.setattr(adapter, "SAMPLE_ROOT", config)
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    adapter.processor_fingerprint.cache_clear()
    first = adapter.processor_fingerprint()
    review.write_text("review-v2")
    evaluation.write_text("evaluation-v2")
    adapter.processor_fingerprint.cache_clear()
    assert adapter.processor_fingerprint() == first
    (source / "vision.py").write_text("processing-v2")
    adapter.processor_fingerprint.cache_clear()
    assert adapter.processor_fingerprint() != first
    adapter.processor_fingerprint.cache_clear()
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


def test_reviewable_epub_text_is_used_without_hiding_review_warning():
    source = report()
    source["groups"][1].update({
        "text_basis": "epub_punctuation_expansion",
        "text_effective": "社会学思想的核心部分。",
        "epub_candidate": {"similarity": .72},
        "review_reasons": ["weak_similarity"],
    })
    observed = adapt_report(source, 100, 100)
    assert observed["printed_regions"][1]["text"]["text"] == "社会学思想的核心部分。"
    assert observed["printed_regions"][1]["text"]["basis"] == "source_payload"
    assert observed["printed_regions"][1]["text"]["confidence"] == 1.0
    assert "bookscan_1:epub_alignment_needs_review" in observed["warnings"]


def test_unrecognized_image_uses_full_frame_without_manual_regions():
    stream = io.BytesIO()
    Image.new("RGB", (90, 120), "white").save(stream, format="PNG")
    entry = _manifest_entry(stream.getvalue(), (90, 120))
    assert entry == {"file": "capture.png",
                     "annotation_regions": [], "bracket_regions": []}
