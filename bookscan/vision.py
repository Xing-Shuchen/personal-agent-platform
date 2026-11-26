"""Local line geometry, pen-stroke candidates, and independent OCR branches."""
from __future__ import annotations

import hashlib
import math
from pathlib import Path

import cv2
import numpy as np

from .inputs import bbox_to_source, polygon_to_source


def model_hash(directory: Path) -> str:
    digest = hashlib.sha256()
    for file in sorted(p for p in directory.rglob("*") if p.is_file()):
        digest.update(str(file.relative_to(directory)).encode())
        with file.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
    return digest.hexdigest()


class OCR:
    def __new__(cls, config: dict):
        if config.get("models", {}).get("remote_command"):
            from .remote_ocr import RemoteOCR
            return RemoteOCR(config)
        return super().__new__(cls)

    def __init__(self, config: dict):
        from paddleocr import TextDetection, TextRecognition

        models = config["models"]
        self.det_name = models["detection_name"]
        self.rec_name = models["recognition_name"]
        self.det_dir = Path(models["detection_dir"]).expanduser().resolve()
        self.rec_dir = Path(models["recognition_dir"]).expanduser().resolve()
        for directory in (self.det_dir, self.rec_dir):
            if not directory.is_dir() or not all((directory / file).is_file() for file in
                ("inference.json", "inference.yml", "inference.pdiparams")):
                raise FileNotFoundError(f"local OCR model unavailable: {directory}")
        device = models.get("device", "cpu")
        common = {"device": device, "enable_mkldnn": False}
        self.detector = TextDetection(model_name=self.det_name,
                                      model_dir=str(self.det_dir), **common)
        self.recognizer = TextRecognition(model_name=self.rec_name,
                                          model_dir=str(self.rec_dir), **common)
        self.hashes = {"detection": model_hash(self.det_dir),
                       "recognition": model_hash(self.rec_dir)}

    def detect(self, image: np.ndarray) -> list[dict]:
        results = list(self.detector.predict(image))
        if not results:
            return []
        data = results[0].json["res"]
        polys = data.get("dt_polys", [])
        scores = data.get("dt_scores", [None] * len(polys))
        return [{"polygon": np.asarray(p).tolist(),
                 "bbox": _poly_box(p),
                 "score": float(scores[i]) if scores[i] is not None else None}
                for i, p in enumerate(polys)]

    def recognize(self, image: np.ndarray) -> tuple[str, float | None]:
        if image.size == 0:
            return "", None
        results = list(self.recognizer.predict(image))
        if not results:
            return "", None
        data = results[0].json["res"]
        return str(data.get("rec_text") or ""), (float(data["rec_score"])
            if data.get("rec_score") is not None else None)


def infer_page_rotation(image: np.ndarray, ocr: OCR, selection: dict) -> int:
    """Choose reading orientation from line OCR, leaving uncertain pages alone."""
    height, width = image.shape[:2]
    scale = min(1.0, 1800 / max(height, width))
    if scale < 1:
        image = cv2.resize(image, None, fx=scale, fy=scale,
                           interpolation=cv2.INTER_AREA)
    candidates = (0, 180) if height >= width else (0, 180, 90, 270)
    results = []
    for rotation in candidates:
        rotated = (image if rotation == 0 else cv2.rotate(image, {
            90: cv2.ROTATE_90_CLOCKWISE,
            180: cv2.ROTATE_180,
            270: cv2.ROTATE_90_COUNTERCLOCKWISE}[rotation]))
        lines, _ = text_lines(ocr.detect(rotated), selection)
        sample = lines[::max(1, len(lines) // 12)][:12]
        scores = []
        for line in sample:
            x1, y1, x2, y2 = line["bbox"]
            text, confidence = ocr.recognize(rotated[y1:y2, x1:x2])
            if len(text.strip()) >= 4 and confidence is not None and confidence >= .5:
                scores.append(confidence)
        results.append((sum(scores), len(scores), rotation))
        if rotation == 0 and len(scores) >= 7 and sum(scores) / len(scores) >= .90:
            return 0
    results.sort(reverse=True)
    best, runner_up = results[0], results[1]
    if best[1] >= 3 and best[0] >= runner_up[0] * 1.5 and best[0] - runner_up[0] >= 1.5:
        return best[2]
    return 0


def _poly_box(points) -> list[int]:
    array = np.asarray(points)
    return [int(array[:, 0].min()), int(array[:, 1].min()),
            int(array[:, 0].max()) + 1, int(array[:, 1].max()) + 1]


def _union(a: list[int], b: list[int]) -> list[int]:
    return [min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3])]


def text_lines(detections: list[dict], config: dict) -> tuple[list[dict], list[dict]]:
    boxes = [d for d in detections if d["bbox"][2] - d["bbox"][0] >= 20
             and d["bbox"][3] - d["bbox"][1] >= 9]
    if not boxes:
        return [], []
    heights = [d["bbox"][3] - d["bbox"][1] for d in boxes]
    typical = float(np.median(heights))
    candidates = []
    rejected = []
    for d in boxes:
        box = d["bbox"]
        h, w = box[3] - box[1], box[2] - box[0]
        if h < typical * .45 or h > typical * 1.9 or w < max(30, typical * 1.4):
            rejected.append({**d, "reason": "unlikely_textline_geometry"})
        else:
            candidates.append({**d, "fragments": [d["polygon"]]})
    # Paddle sometimes splits one line into separate boxes; join only boxes with
    # near-identical vertical centers. Never join boxes stacked in two rows.
    candidates.sort(key=lambda d: ((d["bbox"][1] + d["bbox"][3]) / 2,
                                   d["bbox"][0]))
    merged = []
    for item in candidates:
        box = item["bbox"]
        center = (box[1] + box[3]) / 2
        target = None
        for existing in reversed(merged):
            other = existing["bbox"]
            other_center = (other[1] + other[3]) / 2
            gap = max(0, box[0] - other[2], other[0] - box[2])
            if (abs(center - other_center) <= typical * .28
                    and gap <= typical * 2.0):
                target = existing
                break
        if target is None:
            merged.append(item.copy())
        else:
            target["bbox"] = _union(target["bbox"], box)
            target["fragments"] += item["fragments"]
    merged.sort(key=lambda d: (d["bbox"][1], d["bbox"][0]))
    for index, item in enumerate(merged):
        item["reading_order"] = index
    return merged, rejected


def _ink_threshold(gray: np.ndarray, config: dict) -> int:
    """Choose a page-adaptive ink cutoff so faint pen strokes still register.

    The configured value is a floor; the adaptive value never exceeds the
    page's paper luminance minus a margin, so clean dark-ink pages keep their
    previous behavior while faint hand-drawn strokes are not erased.
    """
    base = int(config.get("ink_threshold", 145))
    if not config.get("adaptive_ink_threshold", True):
        return base
    paper = float(np.percentile(gray, 90))
    return int(max(base, min(paper - 55, 215)))


def underline_candidates(image: np.ndarray, typical_height: float,
                         config: dict) -> list[dict]:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    # Preserve narrow ink; lift the cutoff toward each page's paper luminance
    # so faint strokes stay connected instead of splitting into 1px fragments.
    dark = np.uint8(gray < _ink_threshold(gray, config)) * 255
    min_length = max(20, int(typical_height * float(config.get("min_length_in_line_heights", 1.0))))
    lines = np.zeros_like(dark)
    for factor in (1.0, 1.8):
        width = max(12, int(min_length * factor))
        opened = cv2.morphologyEx(dark, cv2.MORPH_OPEN,
                                  cv2.getStructuringElement(cv2.MORPH_RECT, (width, 1)))
        lines = cv2.bitwise_or(lines, opened)
    n, _, stats, _ = cv2.connectedComponentsWithStats(lines)
    result = []
    for index in range(1, n):
        x, y, w, h, area = [int(v) for v in stats[index]]
        if w < min_length or h > max(14, typical_height * .35):
            continue
        result.append({"bbox": [x, y, x + w, y + h], "length": w,
                       "thickness": round(area / max(w, 1), 2),
                       "angle_degrees": 0.0,
                       "continuity": round(area / max(w * h, 1), 3),
                       "method": "horizontal_morphology", "reason": None})
    return result


def curved_underline_candidates(image: np.ndarray, textlines: list[dict],
                                config: dict) -> list[dict]:
    """Trace connected ink in a narrow band under each text line.

    Unlike a horizontal opening, this keeps slow vertical changes along a
    hand-drawn wave. The association stage still decides whether a component
    belongs to the text line; geometry alone is not proof of author intent.
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    dark = np.uint8(gray < _ink_threshold(gray, config)) * 255
    height, width = dark.shape
    marks = []
    for line in textlines:
        x1, y1, x2, y2 = line["bbox"]
        line_height = y2 - y1
        top = max(0, int(y2 - line_height * .08))
        bottom = min(height, int(y2 + line_height * .48))
        if bottom <= top or x2 <= x1:
            continue
        band = dark[top:bottom, x1:x2]
        connected = cv2.morphologyEx(
            band, cv2.MORPH_CLOSE,
            cv2.getStructuringElement(cv2.MORPH_RECT, (7, 3)))
        n, _, stats, _ = cv2.connectedComponentsWithStats(connected)
        for component in range(1, n):
            x, y, w, h, _ = [int(v) for v in stats[component]]
            min_width = max(28, int(line_height * .7))
            if w < min_width or h > max(18, line_height * .65):
                continue
            # Original ink density distinguishes a thin pen path from a large
            # printed glyph cluster linked only by the closing operation.
            area = int(np.count_nonzero(band[y:y + h, x:x + w]))
            thickness = area / max(w, 1)
            if thickness > 6.5:
                continue
            box = [x + x1, y + top, x + x1 + w, y + top + h]
            marks.append({"bbox": box, "length": w,
                          "thickness": round(thickness, 2),
                          "angle_degrees": None,
                          "continuity": round(area / max(w * h, 1), 3),
                          "method": "curved_component", "reason": None})
    return marks


def merge_mark_candidates(marks: list[dict],
                          typical_height: float | None = None) -> list[dict]:
    merged: list[dict] = []
    for mark in sorted(marks, key=lambda item: (item["bbox"][1], item["bbox"][0])):
        box = mark["bbox"]
        target = None
        for other in merged:
            prior = other["bbox"]
            vertical_gap = max(0, box[1] - prior[3], prior[1] - box[3])
            horizontal_overlap = max(0, min(box[2], prior[2]) - max(box[0], prior[0]))
            horizontal_gap = max(0, max(box[0], prior[0]) - min(box[2], prior[2]))
            if vertical_gap <= 5 and horizontal_overlap >= min(
                    box[2] - box[0], prior[2] - prior[0]) * .55:
                target = other
                break
            # A faint hand-drawn line breaks into dashes; bridge fragments that
            # share a baseline so the association length test sees one stroke.
            if (typical_height
                    and vertical_gap <= max(5, int(typical_height * .06))
                    and horizontal_gap <= max(36, int(typical_height * 2.4))):
                target = other
                break
        if target is None:
            merged.append({**mark, "methods": [mark["method"]]})
        else:
            target["bbox"] = _union(target["bbox"], box)
            target["length"] = target["bbox"][2] - target["bbox"][0]
            target["thickness"] = min(target["thickness"], mark["thickness"])
            if mark["method"] not in target["methods"]:
                target["methods"].append(mark["method"])
    return merged


def associate(lines: list[dict], marks: list[dict], config: dict
              ) -> tuple[list[dict], list[dict]]:
    selected = {}
    review = []
    for mark in marks:
        m = mark["bbox"]
        scores = []
        for index, line in enumerate(lines):
            b = line["bbox"]
            h = b[3] - b[1]
            overlap = max(0, min(m[2], b[2]) - max(m[0], b[0]))
            fraction = overlap / max(1, m[2] - m[0])
            dy = (m[1] - b[3]) / max(h, 1)
            if fraction < .5 or not (-.18 <= dy <= .65):
                continue
            score = fraction - abs(dy - .12) * .45
            scores.append((score, index, round(dy, 3), round(fraction, 3)))
        scores.sort(reverse=True)
        if not scores:
            review.append({"reason": "underline_without_textline", "mark": mark,
                           "candidate_lines": []})
            continue
        if len(scores) > 1 and scores[0][0] - scores[1][0] < .12:
            review.append({"reason": "ambiguous_line_association", "mark": mark,
                           "candidate_lines": [s[1] for s in scores[:2]]})
            continue
        _, index, dy, overlap = scores[0]
        b = lines[index]["bbox"]
        if mark["length"] < max(100, int((b[3] - b[1]) * 2.5)):
            review.append({"reason": "short_ink_ambiguous", "mark": mark,
                           "candidate_lines": [index]})
            continue
        # Do not promote a likely printed rule or long decoration solely because
        # it sits near a box. Keep it visible for manual review.
        if mark["length"] > (b[2] - b[0]) * 1.15 or mark["thickness"] > 7:
            review.append({"reason": "possible_printed_rule", "mark": mark,
                           "candidate_lines": [index]})
            continue
        selected.setdefault(index, []).append({**mark, "association": {
            "vertical_offset_in_line_heights": dy,
            "horizontal_overlap": overlap}})
    return [{**lines[index], "underlines": items} for index, items in
            sorted(selected.items())], review


def expand(box: list[int], margin: int, width: int, height: int) -> list[int]:
    return [max(0, box[0] - margin), max(0, box[1] - margin),
            min(width, box[2] + margin), min(height, box[3] + margin)]


def crop(image: np.ndarray, box: list[int]) -> np.ndarray:
    return image[box[1]:box[3], box[0]:box[2]]


def to_source_line(line: dict, page: dict, working: np.ndarray,
                   source: np.ndarray, output: Path) -> dict:
    box = line["bbox"]
    h, w = working.shape[:2]
    text_box = expand(box, 2, w, h)
    evidence_box = expand(_union(box, _union_many([m["bbox"] for m in line["underlines"]])),
                          max(8, int((box[3] - box[1]) * .2)), w, h)
    line_id = f'{page["page_id"]}-line-{line["reading_order"]:03d}'
    crop_dir = output / "crops"
    crop_dir.mkdir(exist_ok=True)
    text_path = crop_dir / f"{line_id}-text.png"
    evidence_path = crop_dir / f"{line_id}-evidence.png"
    cv2.imwrite(str(text_path), crop(working, text_box))
    cv2.imwrite(str(evidence_path), crop(working, evidence_box))
    return {
        "schema_version": "0.1", "line_id": line_id, "page_id": page["page_id"],
        "source_file": page["source_file"], "scan_index": page["scan_index"],
        "reading_order": line["reading_order"], "mark_type": "underline",
        "selection_status": "selected", "coordinate_space": "source_raster",
        "line_bbox": bbox_to_source(box, page),
        "line_polygon": polygon_to_source([
            [box[0], box[1]], [box[2], box[1]], [box[2], box[3]], [box[0], box[3]]], page),
        "underline_bboxes": [bbox_to_source(m["bbox"], page) for m in line["underlines"]],
        "underline_evidence": [
            {**mark, "bbox": bbox_to_source(mark["bbox"], page)}
            for mark in line["underlines"]],
        "text_crop_bbox": bbox_to_source(text_box, page),
        "evidence_crop_bbox": bbox_to_source(evidence_box, page),
        "text_crop": str(text_path.relative_to(output)),
        "evidence_crop": str(evidence_path.relative_to(output)),
        "crop_rotation_clockwise": page["rotation"],
        "_text_crop_working": crop(working, text_box),
    }


def _union_many(boxes: list[list[int]]) -> list[int]:
    result = boxes[0]
    for box in boxes[1:]:
        result = _union(result, box)
    return result
