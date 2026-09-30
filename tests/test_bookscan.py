from __future__ import annotations

import json
from pathlib import Path
from zipfile import ZipFile

import cv2
import numpy as np

from bookscan.align import align_group, align_line
from bookscan.annotations import collect_annotations
from bookscan.brackets import collect_brackets
from bookscan.epub import EpubIndex, normalized
from bookscan.evaluate import evaluate
from bookscan.groups import group_adjacent
from bookscan.inputs import bbox_from_source, bbox_to_source, discover, infer_page_roi
from bookscan.pagenum import interpolate
from bookscan.vision import (associate, curved_underline_candidates,
                             text_lines, underline_candidates)
from agents.librarian.runtime.bookscan_adapter import adapt_report


def test_adapter_uses_accepted_sentence_expansion_only() -> None:
    report = {"pages": [{"processing_status": "processed", "issues": [],
                         "page_number": {"status": "unknown"}}],
              "lines": [{"line_id": "a", "ocr_raw": "句子的中间", "ocr_score": .93},
                        {"line_id": "b", "ocr_raw": "不确定片段", "ocr_score": .7}],
              "groups": [
                  {"line_ids": ["a"], "group_bbox": [10, 10, 80, 20],
                   "underline_bboxes": [], "mark_type": "underline",
                   "match_status": "matched", "text_basis": "epub_punctuation_expansion",
                   "text_effective": "这是句子的中间部分。",
                   "epub_candidate": {"similarity": .91}},
                  {"line_ids": ["b"], "group_bbox": [10, 30, 80, 40],
                   "underline_bboxes": [], "mark_type": "underline",
                   "match_status": "needs_review", "text_basis": "visual_ocr",
                   "text_effective": "不确定片段", "epub_candidate": None}],
              "annotations": [], "review_candidates": [], "failures": []}
    observed = adapt_report(report, 100, 100)
    matched, uncertain = observed["printed_regions"]
    assert matched["text"] == {"text": "这是句子的中间部分。",
                               "confidence": 1.0, "basis": "source_payload"}
    assert uncertain["text"] == {"text": "不确定片段",
                                 "confidence": .7, "basis": "vision"}
    assert "bookscan_1:epub_alignment_needs_review" in observed["warnings"]


def make_epub(path: Path, chapters: list[tuple[str, str]], order: list[str]) -> Path:
    container = '<container><rootfiles><rootfile full-path="OEBPS/content.opf"/></rootfiles></container>'
    items = "".join(f'<item id="i{n}" href="{name}" media-type="application/xhtml+xml"/>'
                    for n, (name, _) in enumerate(chapters))
    refs = "".join(f'<itemref idref="i{next(i for i, c in enumerate(chapters) if c[0] == name)}"/>'
                   for name in order)
    opf = f'<package><manifest>{items}</manifest><spine>{refs}</spine></package>'
    with ZipFile(path, "w") as archive:
        archive.writestr("META-INF/container.xml", container)
        archive.writestr("OEBPS/content.opf", opf)
        for name, text in chapters:
            archive.writestr(f"OEBPS/{name}",
                             f'<html xmlns="http://www.w3.org/1999/xhtml"><body>'
                             f'<p>{text}</p></body></html>')
    return path


def test_epub_spine_offsets_and_normalization_mapping(tmp_path: Path):
    book = make_epub(tmp_path / "book.epub", [
        ("later.xhtml", "第二章不应先出现"),
        ("first.xhtml", "Ａ ﬃ 文字。下一行不该补入")], ["first.xhtml", "later.xhtml"])
    index = EpubIndex(book)
    assert [c["href"] for c in index.chapters] == ["first.xhtml", "later.xhtml"]
    assert normalized("Ａ ﬃ")[0] == "affi"
    assert normalized("Ａ ﬃ")[1] == [0, 2, 2, 2]
    match = index.candidates("A ffi 文字")[0]
    chapter = index.chapters[0]
    assert chapter["text"][match["start"]:match["end"]] == match["exact"]
    assert "下一行" not in match["exact"]


def test_epub_alignment_does_not_expand_to_sentence_or_neighbor(tmp_path: Path):
    index = EpubIndex(make_epub(tmp_path / "book.epub", [
        ("one.xhtml", "我们需要保留这一行而不是扩展为整个段落。")], ["one.xhtml"]))
    result = align_line("我们需要保留这一行", index, {})
    assert result["candidate_text"] == "我们需要保留这一行"
    assert result["text_effective"] == "我们需要保留这一行"
    assert "而不是" not in result["text_effective"]


def test_group_epub_expands_outward_to_nearest_punctuation(tmp_path: Path):
    index = EpubIndex(make_epub(tmp_path / "book.epub", [
        ("one.xhtml", "前文。我们需要保留这一行，而不是扩展到下一个分句。后文。")],
        ["one.xhtml"]))
    result = align_group("需要保留这一行", index, {})
    assert result["epub_expanded_text"] == "我们需要保留这一行，而不是扩展到下一个分句。"
    match = result["epub_candidate"]
    assert match["expanded_start"] <= match["start"]
    assert match["expanded_end"] >= match["end"]
    assert "后文" not in result["epub_expanded_text"]


def test_group_clause_fallback_omits_comma(tmp_path: Path):
    index = EpubIndex(make_epub(tmp_path / "book.epub", [
        ("one.xhtml", "前文，我们需要保留这一行，后文")], ["one.xhtml"]))
    result = align_group("需要保留这一行", index, {})
    assert result["epub_expanded_text"] == "我们需要保留这一行"


def test_weak_but_unique_epub_match_keeps_review_and_uses_grounded_text(tmp_path: Path):
    sentence = "帕森斯让大家注意到，在早期基督教时代就蕴含先驱思想。"
    index = EpubIndex(make_epub(tmp_path / "book.epub", [
        ("one.xhtml", sentence)], ["one.xhtml"]))
    result = align_group("帕森斯让家注意到，在早期基督含先数思想。", index, {})
    assert result["match_status"] == "needs_review"
    assert result["review_reasons"] == ["weak_similarity"]
    assert result["text_effective"] == sentence
    assert result["text_basis"] == "epub_punctuation_expansion"


def test_group_expansion_starts_at_marked_ocr_span(tmp_path: Path):
    sentence = ("帕森斯区分了规范秩序和实际秩序。我们先来看实际秩序。"
                "帕森斯所谓的实际秩序，意指最终不是刻意地形成的秩序。"
                "在度假旺季时交通堵塞，是实际秩序的例子。")
    index = EpubIndex(make_epub(tmp_path / "book.epub", [
        ("one.xhtml", sentence)], ["one.xhtml"]))
    ocr = sentence.replace("最终", "最61 终")
    start = ocr.index("帕森斯所谓")
    end = ocr.index("秩序。在度假") + len("秩序")
    result = align_group(ocr, index, {}, [start, end])
    assert result["epub_candidate"]["exact"] == sentence[
        sentence.index("帕森斯所谓"):sentence.index("秩序。在度假") + len("秩序")]
    assert result["epub_expanded_text"] == "帕森斯所谓的实际秩序，意指最终不是刻意地形成的秩序。"


def test_auto_page_roi_excludes_facing_page_and_tabletop():
    image = np.full((1200, 1000, 3), 245, dtype=np.uint8)
    image[900:, :] = 110
    image[:900, 780:830] = 90
    roi = infer_page_roi(image)
    assert 730 < roi[2] < 800
    assert 870 < roi[3] < 920


def test_adjacent_marked_lines_are_one_group_with_one_crop(tmp_path: Path):
    page = {"page_id": "p", "source_file": "one.jpg", "scan_index": 0,
            "source_size": [400, 240], "valid_page_roi": [0, 0, 400, 240],
            "rotation": 0}
    working = np.full((240, 400, 3), 255, dtype=np.uint8)
    selected = [{"reading_order": order, "bbox": [20, y, 350, y + 30],
                 "underlines": [{"bbox": [30, y + 31, 200, y + 34]}]}
                for order, y in ((0, 20), (1, 60), (3, 140))]
    lines = [{"reading_order": item["reading_order"], "line_id": f'l{item["reading_order"]}',
              "underline_bboxes": [[30, item["bbox"][1] + 31, 200,
                                     item["bbox"][1] + 34]],
              "ocr_raw": "需要保留这一行"} for item in selected]
    index = EpubIndex(make_epub(tmp_path / "book.epub", [
        ("one.xhtml", "需要保留这一行需要保留这一行，需要保留这一行。")],
        ["one.xhtml"]))
    (tmp_path / "crops").mkdir()
    groups = group_adjacent(lines, selected, working, page, tmp_path, index, {})
    assert [len(group["line_ids"]) for group in groups] == [2, 1]
    assert all((tmp_path / group["evidence_crop"]).is_file() for group in groups)


def test_wavy_underline_is_kept_as_a_connected_candidate():
    image = np.full((120, 400, 3), 255, dtype=np.uint8)
    points = np.array([[x, int(63 + 4 * np.sin(x / 14))] for x in range(60, 320)],
                      dtype=np.int32)
    cv2.polylines(image, [points], False, (0, 0, 0), 2)
    line = {"bbox": [40, 20, 350, 60], "reading_order": 0}
    marks = curved_underline_candidates(image, [line], {})
    assert any(mark["length"] > 200 for mark in marks)
    selected, _ = associate([line], marks, {})
    assert len(selected) == 1


def test_ambiguous_epub_location_is_not_accepted(tmp_path: Path):
    index = EpubIndex(make_epub(tmp_path / "book.epub", [
        ("one.xhtml", "重复短句出现在这里"),
        ("two.xhtml", "重复短句出现在这里")], ["one.xhtml", "two.xhtml"]))
    result = align_line("重复短句", index, {})
    assert result["match_status"] == "needs_review"
    assert result["corrected_text"] is None
    assert "epub_ambiguous" in result["review_reasons"]


def test_underline_selection_keeps_only_marked_lines_and_deduplicates():
    image = np.full((220, 500, 3), 255, dtype=np.uint8)
    cv2.line(image, (90, 62), (210, 62), (0, 0, 0), 2)
    cv2.line(image, (260, 63), (390, 63), (0, 0, 0), 2)
    cv2.line(image, (100, 182), (350, 182), (0, 0, 0), 2)
    detections = [{"bbox": [80, y, 400, y + 40],
                   "polygon": [[80, y], [400, y], [400, y + 40], [80, y + 40]],
                   "score": .9} for y in (20, 80, 140)]
    lines, rejected = text_lines(detections, {})
    marks = underline_candidates(image, 40, {})
    selected, review = associate(lines, marks, {})
    assert [s["reading_order"] for s in selected] == [0, 2]
    assert len(selected[0]["underlines"]) == 2
    assert len(selected[1]["underlines"]) == 1


def test_rotation_coordinates_return_to_source_raster():
    page = {"valid_page_roi": [100, 200, 500, 800],
            "rotation": 180, "source_size": [600, 900]}
    assert bbox_to_source([50, 60, 100, 90], page) == [400, 710, 450, 740]
    assert bbox_from_source([400, 710, 450, 740], page) == [50, 60, 100, 90]


def test_deskew_point_round_trip():
    from bookscan.inputs import point_from_source, point_to_source
    page = {"valid_page_roi": [100, 200, 2050, 3210],
            "rotation": 180, "deskew_degrees": -1.3}
    x, y = point_to_source(700, 900, page)
    actual = point_from_source(x, y, page)
    assert np.allclose(actual, [700, 900], atol=1e-8)


def test_annotation_is_independent_of_underlined_lines(tmp_path: Path):
    class FakeOCR:
        def recognize(self, image):
            return "批注", .8
    page = {"page_id": "p", "source_file": "one.jpg", "source_size": [300, 300],
            "valid_page_roi": [0, 0, 300, 300], "rotation": 0,
            "annotation_regions": [{"bbox": [20, 20, 200, 80], "ocr_rotation": 0}]}
    image = np.full((300, 300, 3), 255, dtype=np.uint8)
    cv2.line(image, (30, 40), (160, 40), (0, 0, 0), 3)
    notes = collect_annotations(image, page, tmp_path, FakeOCR())
    assert len(notes) == 1
    assert notes[0]["review_status"] == "needs_review"
    assert (tmp_path / notes[0]["evidence_crop"]).is_file()


def test_corner_bracket_creates_separate_mark_record(tmp_path: Path):
    class FakeOCR:
        def recognize(self, image):
            return "测试文字", .8
    page = {"page_id": "p", "source_file": "one.jpg", "scan_index": 0,
            "source_size": [300, 300],
            "valid_page_roi": [0, 0, 300, 300], "rotation": 0,
            "bracket_regions": [{"start": [40, 50], "end": [160, 130],
                                  "bbox": [20, 25, 280, 160]}]}
    image = np.full((300, 300, 3), 255, dtype=np.uint8)
    geometry = [{"reading_order": 0, "bbox": [20, 35, 280, 75]},
                {"reading_order": 1, "bbox": [20, 105, 280, 145]}]
    index = EpubIndex(make_epub(tmp_path / "book.epub", [
        ("one.xhtml", "测试文字测试文字。")], ["one.xhtml"]))
    notes = collect_brackets(image, page, tmp_path, geometry, FakeOCR(), index, {})
    assert len(notes) == 1
    assert notes[0]["mark_type"] == "corner_bracket"
    assert notes[0]["line_reading_orders"] == [0, 1]
    assert (tmp_path / notes[0]["evidence_crop"]).is_file()


def test_page_number_inference_needs_two_consistent_anchors():
    pages = [{"scan_index": i, "page_id": f"p{i}", "issues": [],
              "page_number": {"status": "observed" if value else "unknown",
                              "observed_value": value, "inferred_value": None,
                              "resolved_value": value, "bbox": [1, 1, 2, 2] if value else None,
                              "sequence_segment_id": None, "inference_evidence": []}}
             for i, value in enumerate((128, None, 130))]
    interpolate(pages)
    assert pages[1]["page_number"]["status"] == "inferred"
    assert pages[1]["page_number"]["resolved_value"] == 129
    assert pages[1]["page_number"]["bbox"] is None
    pages[2]["page_number"].update(status="unknown", observed_value=None,
                                   resolved_value=None)
    pages[1]["page_number"].update(status="unknown", inferred_value=None,
                                   resolved_value=None)
    interpolate(pages)
    assert pages[1]["page_number"]["status"] == "unknown"


def test_multiframe_tiff_inventory_and_natural_order(tmp_path: Path):
    from PIL import Image
    image = Image.new("RGB", (20, 30), "white")
    image.save(tmp_path / "scan10.tiff", save_all=True, append_images=[image])
    image.save(tmp_path / "scan2.png")
    pages = discover(tmp_path)
    assert [p["source_file"] for p in pages] == ["scan2.png", "scan10.tiff", "scan10.tiff"]
    assert [p["source_page_index"] for p in pages] == [None, 0, 1]


def test_evaluation_is_one_to_one_and_denominator_zero_is_null(tmp_path: Path):
    run = tmp_path / "run"
    run.mkdir()
    (run / "pages.jsonl").write_text(json.dumps({"page_id": "p",
        "page_number": {"status": "unknown", "resolved_value": None}}) + "\n")
    lines = [{"page_id": "p", "line_id": f"l{i}", "line_bbox": [0, 0, 100, 20],
              "ocr_raw": "甲", "text_effective": "甲", "corrected_text": None}
             for i in range(2)]
    (run / "lines.jsonl").write_text("".join(json.dumps(x) + "\n" for x in lines))
    truth = tmp_path / "truth.jsonl"
    truth.write_text(json.dumps({"page_id": "p", "lines": [
        {"bbox": [0, 0, 100, 20], "text": "甲"}]}) + "\n")
    metrics = evaluate(run, truth)
    assert metrics["line_selection"]["tp"] == 1
    assert metrics["line_selection"]["fp"] == 1
    assert metrics["line_selection"]["precision"] == .5
    assert metrics["page_number"]["observed_accuracy"] is None


def test_evaluation_excludes_corner_brackets_from_underline_precision(tmp_path: Path):
    run = tmp_path / "run"
    run.mkdir()
    (run / "pages.jsonl").write_text(json.dumps({"page_id": "p",
        "page_number": {"status": "unknown", "resolved_value": None}}) + "\n")
    (run / "lines.jsonl").write_text(json.dumps({"page_id": "p", "line_id": "b",
        "mark_type": "corner_bracket", "line_bbox": [0, 0, 100, 20],
        "ocr_raw": "甲", "text_effective": "甲", "corrected_text": None}) + "\n")
    truth = tmp_path / "truth.jsonl"
    truth.write_text(json.dumps({"page_id": "p", "lines": []}) + "\n")
    metrics = evaluate(run, truth)
    assert metrics["line_selection"]["fp"] == 0
    assert metrics["line_selection"]["precision"] is None


def test_ambiguous_truth_does_not_make_overlapping_prediction_false_positive(tmp_path: Path):
    run = tmp_path / "run"
    run.mkdir()
    (run / "pages.jsonl").write_text(json.dumps({"page_id": "p",
        "page_number": {"status": "unknown", "resolved_value": None}}) + "\n")
    (run / "lines.jsonl").write_text(json.dumps({"page_id": "p", "line_id": "l",
        "line_bbox": [0, 0, 100, 20], "ocr_raw": "甲",
        "text_effective": "甲", "corrected_text": None}) + "\n")
    truth = tmp_path / "truth.jsonl"
    truth.write_text(json.dumps({"page_id": "p", "lines": [
        {"bbox": [0, 0, 100, 20], "ambiguous": True}]}) + "\n")
    metrics = evaluate(run, truth)
    assert metrics["ambiguous_lines_excluded"] == 1
    assert metrics["line_selection"]["fp"] == 0


def test_review_contains_full_page_adjudication_and_export(tmp_path: Path):
    from bookscan.review import build_review
    run = tmp_path / "run"
    run.mkdir()
    epub = tmp_path / "9787208171411.epub"
    epub.touch()
    epub.with_suffix(".metadata.json").write_text(json.dumps({
        "isbn13": "9787208171411", "title": "社会理论二十讲",
        "authors": ["汉斯·约阿斯"], "translator": "郑作彧",
        "publisher": "上海人民出版社", "publication_date": "2021-09-01",
        "original_title": "Sozialtheorie", "source_name": "豆瓣读书 ISBN 书目",
        "source_url": "https://book.douban.com/subject/35596074/",
    }, ensure_ascii=False), encoding="utf-8")
    for folder in ("pages", "overlays"):
        (run / folder).mkdir()
    (run / "run.json").write_text(json.dumps({"run_id": "sample", "config": {
        "root": str(tmp_path), "epub": str(epub)},
        "epub": {"epub_sha256": "x"}, "models": {
        "detection_name": "det", "recognition_name": "rec"},
        "elapsed_seconds": 1}))
    page = {"page_id": "p", "scan_index": 0, "source_file": "one.jpg",
            "source_size": [200, 300], "processing_status": "processed",
            "selected_line_count": 0, "rotation": 0,
            "valid_page_roi": [0, 0, 200, 300], "issues": [],
            "page_number": {"status": "unknown", "observed_label": None,
                            "inferred_value": None, "resolved_value": None,
                            "candidates": [], "inference_evidence": []}}
    (run / "pages.jsonl").write_text(json.dumps(page) + "\n")
    for name in ("lines", "groups", "annotations", "brackets", "review_candidates",
                 "failures"):
        (run / f"{name}.jsonl").write_text("")
    build_review(run)
    html = (run / "review.html").read_text()
    assert "逐页人工核验" in html
    assert "ground-truth.jsonl" in html
    assert "data-source-width='200'" in html
    assert "导入核验草稿" in html
    assert "下载完成审核包" in html
    assert "missingAnnotation" in html
    assert "社会理论二十讲" in html
    assert "ISBN：9787208171411" in html
    assert "出版社：上海人民出版社" in html


def test_review_shows_sourced_isbn_metadata(tmp_path: Path):
    from bookscan.review import _isbn_metadata
    epub = tmp_path / "9787208171411.epub"
    epub.touch()
    epub.with_suffix(".metadata.json").write_text(json.dumps({
        "isbn13": "9787208171411", "authors": ["汉斯·约阿斯"],
        "source_url": "https://book.douban.com/subject/35596074/",
    }, ensure_ascii=False), encoding="utf-8")
    assert _isbn_metadata({"config": {"epub": str(epub)}})["authors"] == ["汉斯·约阿斯"]
    assert _isbn_metadata({"config": {"epub": str(tmp_path / "other.epub")}}) == {}
