"""Preserve handwritten marginalia as independent, reviewable image evidence."""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from .inputs import bbox_to_source


def _line_crops(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    dark = np.uint8(gray < 125)
    counts = np.count_nonzero(dark, axis=1)
    active = np.uint8(counts >= max(5, image.shape[1] * .008)) * 255
    active = cv2.morphologyEx(active.reshape(-1, 1), cv2.MORPH_CLOSE,
                              np.ones((11, 1), np.uint8)).ravel()
    edges = np.diff(np.pad(active > 0, (1, 1)).astype(np.int8))
    starts = np.flatnonzero(edges == 1)
    ends = np.flatnonzero(edges == -1)
    for top, bottom in zip(starts, ends):
        if bottom - top < 14:
            continue
        top, bottom = max(0, top - 6), min(image.shape[0], bottom + 6)
        yield image[top:bottom], [int(top), int(bottom)]


def collect_annotations(working, page: dict, output: Path, ocr) -> list[dict]:
    height, width = working.shape[:2]
    records = []
    for index, entry in enumerate(page.get("annotation_regions", [])):
        box = entry["bbox"]
        if not (len(box) == 4 and 0 <= box[0] < box[2] <= width
                and 0 <= box[1] < box[3] <= height):
            raise ValueError(f"invalid annotation bbox on {page['page_id']}: {box}")
        x1, y1, x2, y2 = box
        crop = working[y1:y2, x1:x2].copy()
        rotation = int(entry.get("ocr_rotation", 0))
        if rotation not in {0, 90, 180, 270}:
            raise ValueError(f"invalid annotation OCR rotation: {rotation}")
        path = output / "annotations" / f"{page['page_id']}-note-{index:02d}.png"
        path.parent.mkdir(exist_ok=True)
        recognition = crop
        if rotation:
            recognition = cv2.rotate(crop, {
                90: cv2.ROTATE_90_CLOCKWISE,
                180: cv2.ROTATE_180,
                270: cv2.ROTATE_90_COUNTERCLOCKWISE,
            }[rotation])
        cv2.imwrite(str(path), recognition)
        attempts = []
        issue = None
        for line_crop, vertical_span in _line_crops(recognition):
            try:
                text, score = ocr.recognize(line_crop)
                attempts.append({"text": text, "score": score,
                                 "vertical_span": vertical_span})
            except Exception as exc:
                issue = str(exc)
                attempts.append({"text": "", "score": None,
                                 "vertical_span": vertical_span, "error": issue})
        text = "\n".join(item["text"] for item in attempts if item["text"])
        scores = [item["score"] for item in attempts if item["score"] is not None]
        score = round(sum(scores) / len(scores), 4) if scores else None
        records.append({
            "schema_version": "0.1", "annotation_id": f"{page['page_id']}-note-{index:02d}",
            "page_id": page["page_id"], "source_file": page["source_file"],
            "region_source": "manifest_visual_review", "coordinate_space": "source_raster",
            "bbox": bbox_to_source(box, page), "working_bbox": box,
            "evidence_crop": str(path.relative_to(output)),
            "ocr_rotation": rotation, "ocr_raw": text, "ocr_score": score,
            "ocr_attempts": attempts,
            "transcription": None, "review_status": "needs_review",
            "review_reason": "handwriting_ocr_unverified" if issue is None else "ocr_error",
            "ocr_error": issue,
        })
    return records
