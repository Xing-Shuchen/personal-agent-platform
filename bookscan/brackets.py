"""Extract text bounded by reader-drawn corner brackets as a separate mark type."""
from __future__ import annotations

from pathlib import Path

import cv2

from .align import align_group
from .inputs import bbox_to_source, point_to_source


def _char_at_x(text: str, box: list[int], x: int) -> int:
    return min(len(text), max(0, round((x - box[0]) / max(1, box[2] - box[0])
                                       * len(text))))


def collect_brackets(working, page: dict, output: Path, geometry: list[dict],
                     ocr, epub_index, alignment_config: dict) -> list[dict]:
    results = []
    height, width = working.shape[:2]
    for index, entry in enumerate(page.get("bracket_regions", [])):
        start, end, box = entry["start"], entry["end"], entry["bbox"]
        if not (0 <= start[0] < width and 0 <= end[0] < width
                and 0 <= start[1] < end[1] < height
                and 0 <= box[0] < box[2] <= width
                and 0 <= box[1] < box[3] <= height):
            raise ValueError(f"invalid bracket region: {page['page_id']}: {entry}")
        identifier = f"{page['page_id']}-bracket-{index:02d}"
        x1, y1, x2, y2 = box
        crop_path = output / "brackets" / f"{identifier}.png"
        crop_path.parent.mkdir(exist_ok=True)
        cv2.imwrite(str(crop_path), working[y1:y2, x1:x2])
        rows = [item for item in geometry
                if start[1] - 25 <= (item["bbox"][1] + item["bbox"][3]) / 2
                <= end[1] + 25]
        rows.sort(key=lambda item: item["reading_order"])
        texts = []
        errors = []
        for row in rows:
            a, b, c, d = row["bbox"]
            try:
                text, _ = ocr.recognize(working[max(0, b - 2):min(height, d + 2),
                                                max(0, a - 2):min(width, c + 2)])
            except Exception as exc:
                text = ""
                errors.append(str(exc))
            texts.append(text)
        query = "".join(texts)
        start_offset = _char_at_x(texts[0], rows[0]["bbox"], start[0]) if rows else 0
        end_offset = (sum(len(text) for text in texts[:-1]) +
                      _char_at_x(texts[-1], rows[-1]["bbox"], end[0])) if rows else 0
        marked_span = [start_offset, end_offset]
        line_ids = [f"{identifier}-line-{row['reading_order']:03d}" for row in rows]
        record = {"schema_version": "0.2", "bracket_id": identifier,
                  "group_id": identifier, "line_ids": line_ids,
                  "page_id": page["page_id"], "source_file": page["source_file"],
                  "scan_index": page["scan_index"],
                  "mark_type": "corner_bracket", "region_source": "manifest_visual_review",
                  "coordinate_space": "source_raster",
                  "bbox": bbox_to_source(box, page),
                  "start_source": point_to_source(*start, page),
                  "end_source": point_to_source(*end, page),
                  "working_bbox": box,
                  "evidence_crop": str(crop_path.relative_to(output)),
                  "line_reading_orders": [row["reading_order"] for row in rows],
                  "reading_orders": [row["reading_order"] for row in rows],
                  "underline_bboxes": [],
                  "ocr_lines": texts, "ocr_raw": "\n".join(texts),
                  "ocr_query": query, "marked_ocr_span": marked_span,
                  "marked_ocr_text": query[start_offset:end_offset],
                  "review_status": "needs_review", "ocr_errors": errors}
        try:
            record.update(align_group(query, epub_index, alignment_config,
                                      marked_span if start_offset < end_offset else None))
        except Exception as exc:
            record.update({"match_status": "needs_review", "text_effective": query,
                           "text_basis": "visual_ocr", "epub_candidate": None,
                           "epub_expanded_text": None,
                           "review_reasons": ["bracket_alignment_error"],
                           "alignment_error": str(exc)})
        if not rows or errors or not (start_offset < end_offset):
            record["match_status"] = "needs_review"
            record.setdefault("review_reasons", []).append("bracket_geometry_or_ocr")
        record["line_records"] = [{"schema_version": "0.2", "line_id": line_id,
            "page_id": page["page_id"], "source_file": page["source_file"],
            "scan_index": page["scan_index"], "reading_order": row["reading_order"],
            "mark_type": "corner_bracket", "selection_status": "selected",
            "coordinate_space": "source_raster",
            "line_bbox": bbox_to_source(row["bbox"], page),
            "ocr_raw": text, "text_effective": text, "text_basis": "visual_ocr",
            "match_status": "grouped", "group_id": identifier,
            "review_status": "needs_review", "evidence_crop": record["evidence_crop"]}
            for line_id, row, text in zip(line_ids, rows, texts)]
        results.append(record)
    return results
