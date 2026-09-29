"""Adjacent marked physical lines become one review and EPUB unit."""
from __future__ import annotations

from pathlib import Path

import cv2

from .align import align_group
from .inputs import bbox_to_source
from .vision import expand


def _union(boxes: list[list[int]]) -> list[int]:
    return [min(b[0] for b in boxes), min(b[1] for b in boxes),
            max(b[2] for b in boxes), max(b[3] for b in boxes)]


def _join_for_match(texts: list[str]) -> str:
    result = ""
    for text in texts:
        if result and text and result[-1].isascii() and result[-1].isalnum() \
                and text[0].isascii() and text[0].isalnum():
            result += " "
        result += text
    return result


def _marked_char_span(text: str, line_box: list[int], marks: list[dict]) -> tuple[int, int]:
    """Estimate OCR character boundaries from the pen's horizontal coverage."""
    if not text or not marks:
        return 0, len(text)
    x1, _, x2, _ = line_box
    width = max(1, x2 - x1)
    start_x = max(x1, min(mark["bbox"][0] for mark in marks))
    end_x = min(x2, max(mark["bbox"][2] for mark in marks))
    start = min(len(text), max(0, round((start_x - x1) / width * len(text))))
    end = min(len(text), max(start + 1, round((end_x - x1) / width * len(text))))
    return start, end


def group_adjacent(lines: list[dict], selected: list[dict],
                   working, page: dict, output: Path, index, config: dict) -> list[dict]:
    selected_by_order = {item["reading_order"]: item for item in selected}
    ordered = sorted(lines, key=lambda item: item["reading_order"])
    clusters: list[list[dict]] = []
    for line in ordered:
        if (clusters and line["reading_order"] == clusters[-1][-1]["reading_order"] + 1):
            clusters[-1].append(line)
        else:
            clusters.append([line])
    result = []
    height, width = working.shape[:2]
    for cluster in clusters:
        geometry = [selected_by_order[line["reading_order"]] for line in cluster]
        boxes = [item["bbox"] for item in geometry]
        boxes += [mark["bbox"] for item in geometry for mark in item["underlines"]]
        content_box = _union(boxes)
        margin = max(8, int((geometry[0]["bbox"][3] - geometry[0]["bbox"][1]) * .18))
        crop_box = expand(content_box, margin, width, height)
        identifier = (f'{page["page_id"]}-group-'
                      f'{cluster[0]["reading_order"]:03d}-'
                      f'{cluster[-1]["reading_order"]:03d}')
        path = output / "crops" / f"{identifier}.png"
        cv2.imwrite(str(path), working[crop_box[1]:crop_box[3],
                                       crop_box[0]:crop_box[2]])
        raw_lines = [line["ocr_raw"] for line in cluster]
        query = _join_for_match(raw_lines)
        marked_spans = []
        offset = 0
        for raw, item in zip(raw_lines, geometry):
            if offset and raw and query[offset:offset + 1] == " ":
                offset += 1
            start, end = _marked_char_span(raw, item["bbox"], item["underlines"])
            marked_spans.append([offset + start, offset + end])
            offset += len(raw)
        marked_span = [min(span[0] for span in marked_spans),
                       max(span[1] for span in marked_spans)]
        group = {"schema_version": "0.2", "group_id": identifier,
                 "mark_type": "underline",
                 "page_id": page["page_id"], "source_file": page["source_file"],
                 "scan_index": page["scan_index"],
                 "line_ids": [line["line_id"] for line in cluster],
                 "reading_orders": [line["reading_order"] for line in cluster],
                 "coordinate_space": "source_raster",
                 "group_bbox": bbox_to_source(content_box, page),
                 "evidence_crop_bbox": bbox_to_source(crop_box, page),
                 "evidence_crop": str(path.relative_to(output)),
                 "crop_rotation_clockwise": page["rotation"],
                 "ocr_lines": raw_lines, "ocr_raw": "\n".join(raw_lines),
                 "ocr_query": query, "marked_ocr_span": marked_span,
                 "marked_ocr_text": query[marked_span[0]:marked_span[1]],
                 "underline_bboxes": [mark for line in cluster
                                      for mark in line["underline_bboxes"]]}
        try:
            if index is None:
                group.update({"epub_candidate": None, "epub_expanded_text": None,
                              "text_effective": query, "text_basis": "visual_ocr",
                              "match_status": "needs_review",
                              "review_reasons": ["epub_unavailable"]})
            else:
                group.update(align_group(query, index, config, marked_span))
            if any(not item.strip() for item in raw_lines):
                group["match_status"] = "needs_review"
                group["text_effective"] = query
                group["text_basis"] = "visual_ocr"
                group["review_reasons"].append("contains_ocr_failure")
        except Exception as exc:
            group.update({"epub_candidate": None, "epub_expanded_text": None,
                          "text_effective": query, "text_basis": "visual_ocr",
                          "match_status": "needs_review",
                          "review_reasons": ["epub_alignment_error"],
                          "alignment_error": str(exc)})
        result.append(group)
    return result
