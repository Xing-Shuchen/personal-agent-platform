"""Conservative observed page-number candidates and anchored interpolation."""
from __future__ import annotations

import re

from .inputs import bbox_to_source
from .vision import crop, expand


def detect_page_number(working, detections: list[dict], ocr, page: dict,
                       config: dict) -> dict:
    height, width = working.shape[:2]
    fraction_x = float(config.get("corner_width_fraction", .30))
    fraction_y = float(config.get("corner_height_fraction", .12))
    candidates = []
    corner_width, corner_height = int(width * fraction_x), int(height * fraction_y)
    for vertical in ("top", "bottom"):
        for horizontal in ("left", "right"):
            x0 = 0 if horizontal == "left" else width - corner_width
            y0 = 0 if vertical == "top" else height - corner_height
            area = working[y0:y0 + corner_height, x0:x0 + corner_width]
            # Full-page detection often drops small page numbers. Re-detect only
            # inside bounded corner crops, never by scanning body digits.
            for detection in ocr.detect(area):
                local = detection["bbox"]
                if local[2] - local[0] > corner_width * .35:
                    continue
                text, score = ocr.recognize(crop(area, expand(
                    local, 2, corner_width, corner_height)))
                match = re.fullmatch(r"\s*([0-9]{1,4}|[ivxlcdmIVXLCDM]{1,8})\s*", text)
                if not match:
                    continue
                label = match.group(1)
                value = int(label) if label.isdigit() else None
                box = [local[0] + x0, local[1] + y0,
                       local[2] + x0, local[3] + y0]
                candidates.append({"raw": text, "label": label, "value": value,
                                   "bbox": bbox_to_source(box, page),
                                   "region": f"{vertical}_{horizontal}", "ocr_score": score})
    numeric = [item for item in candidates if item["value"] is not None
               and item["value"] > 0 and (item["ocr_score"] or 0) >= .55]
    unique = {(item["label"], item["value"]) for item in numeric}
    selected = numeric[0] if len(unique) == 1 else None
    return {"observed_label": selected["label"] if selected else None,
            "observed_value": selected["value"] if selected else None,
            "inferred_value": None,
            "resolved_value": selected["value"] if selected else None,
            "status": "observed" if selected else "conflict" if len(unique) > 1 else "unknown",
            "bbox": selected["bbox"] if selected else None,
            "sequence_segment_id": None, "inference_evidence": [],
            "candidates": candidates}


def interpolate(pages: list[dict]) -> None:
    observed = [(i, p["page_number"]["observed_value"]) for i, p in enumerate(pages)
                if p["page_number"]["status"] == "observed"]
    segment = 0
    for (left_index, left_value), (right_index, right_value) in zip(
            observed, observed[1:]):
        scan_gap = pages[right_index]["scan_index"] - pages[left_index]["scan_index"]
        if right_value - left_value != scan_gap:
            pages[right_index]["issues"].append("sequence_conflict")
            segment += 1
            continue
        segment_id = f"segment-{segment:02d}"
        pages[left_index]["page_number"]["sequence_segment_id"] = segment_id
        pages[right_index]["page_number"]["sequence_segment_id"] = segment_id
        for index in range(left_index + 1, right_index):
            info = pages[index]["page_number"]
            if info["status"] != "unknown":
                continue
            value = left_value + pages[index]["scan_index"] - pages[left_index]["scan_index"]
            info.update({"inferred_value": value, "resolved_value": value,
                         "status": "inferred", "bbox": None,
                         "sequence_segment_id": segment_id,
                         "inference_evidence": [
                             {"page_id": pages[left_index]["page_id"],
                              "observed_value": left_value},
                             {"page_id": pages[right_index]["page_id"],
                              "observed_value": right_value}]})
