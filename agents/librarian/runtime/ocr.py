"""Local OCR-first extraction of marked physical pages.

RapidOCR supplies positioned text. A user-supplied EPUB identifies printed
lines without assigning physical page numbers or inventing pen marks. A narrow
image test finds long, dark strokes beneath those lines. The complete OCR
result and stroke scores are retained separately from the normalized
PageObservation.
"""
from __future__ import annotations

import hashlib
import io
import json
import re
import subprocess
import tempfile
from typing import Callable
from difflib import SequenceMatcher
from html.parser import HTMLParser
from pathlib import Path
from zipfile import ZipFile

from PIL import Image, ImageOps

from .pipeline import ExtractionOutput
from .vision import _derivative


class _TextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.skip = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"style", "script"}:
            self.skip += 1
        if tag in {"p", "div", "br", "h1", "h2", "h3"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"style", "script"} and self.skip:
            self.skip -= 1

    def handle_data(self, data: str) -> None:
        if not self.skip:
            self.parts.append(data)


def _compact(value: str) -> str:
    return "".join(char.casefold() for char in value if char.isalnum())


def _display_text(value: str) -> str:
    def space(match: re.Match[str]) -> str:
        before = value[match.start() - 1] if match.start() else ""
        after = value[match.end()] if match.end() < len(value) else ""
        return " " if before.isascii() and before.isalnum() and after.isascii() and after.isalnum() else ""
    return re.sub(r"\s+", space, value)


class EpubGroundTruth:
    def __init__(self, path: Path) -> None:
        self.sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
        parts = []
        with ZipFile(path) as archive:
            for name in archive.namelist():
                if name.lower().endswith((".html", ".xhtml", ".htm")):
                    parser = _TextParser()
                    parser.feed(archive.read(name).decode("utf-8", errors="replace"))
                    parts.extend(parser.parts)
                    parts.append("\n")
        self.raw = "".join(parts)
        self.mapping = [index for index, char in enumerate(self.raw) if char.isalnum()]
        self.compact = _compact(self.raw)

    def match(self, ocr_text: str) -> tuple[str | None, float]:
        query = _compact(ocr_text)
        if len(query) < 4:
            return None, 0.0
        if len(query) < 8:
            position = self.compact.find(query)
            return (ocr_text, 1.0) if position >= 0 else (None, 0.0)
        candidates = set()
        for offset in sorted({0, max(0, len(query) // 2 - 4), len(query) - 8}):
            anchor = query[offset:offset + 8]
            start = 0
            for _ in range(12):
                position = self.compact.find(anchor, start)
                if position < 0:
                    break
                candidates.add(position - offset)
                start = position + 1
        best_position, best_ratio = -1, 0.0
        for candidate in candidates:
            for shift in range(-2, 3):
                position = candidate + shift
                if position < 0 or position + len(query) > len(self.compact):
                    continue
                ratio = SequenceMatcher(None, query, self.compact[position:position + len(query)],
                                        autojunk=False).ratio()
                if ratio > best_ratio:
                    best_position, best_ratio = position, ratio
        if best_ratio < .65:
            return None, best_ratio
        if best_ratio < .85:
            return ocr_text, best_ratio
        start = self.mapping[best_position]
        end = self.mapping[best_position + len(query) - 1] + 1
        return _display_text(self.raw[start:end]), best_ratio

    def sentence(self, text: str, through: str | None = None) -> str | None:
        """Expand a matched print line to its full EPUB sentence."""
        query = _compact(text)
        if len(query) < 12:
            return None
        position = self.compact.find(query)
        if position < 0:
            return None
        start = self.mapping[position]
        last = _compact(through) if through else query
        last_position = self.compact.find(last, position)
        if last_position < 0 or last_position - position > 600:
            return None
        end = self.mapping[last_position + len(last) - 1] + 1
        left = max(self.raw.rfind(mark, max(0, start - 220), start) for mark in "。！？") + 1
        right_candidates = [self.raw.find(mark, end, min(len(self.raw), end + 220))
                            for mark in "。！？"]
        right = min((item for item in right_candidates if item >= 0), default=-1)
        if right < 0 or end - left > 700:
            return None
        return _display_text(self.raw[left:right + 1])


def _box(points: list[list[float]], width: int, height: int) -> list[float]:
    xs, ys = [point[0] for point in points], [point[1] for point in points]
    return [round(max(0.0, min(xs) / width), 5), round(max(0.0, min(ys) / height), 5),
            round(min(1.0, max(xs) / width), 5), round(min(1.0, max(ys) / height), 5)]


def _underline_score(gray, points: list[list[float]]) -> float:
    import cv2
    import numpy as np

    quad = np.asarray(points, dtype=np.float32)
    width = int(np.linalg.norm(quad[1] - quad[0]))
    height = int((np.linalg.norm(quad[3] - quad[0]) +
                  np.linalg.norm(quad[2] - quad[1])) / 2)
    if width < 150 or height < 10:
        return 0.0
    lower = quad.copy()
    lower[2] = quad[1] + (quad[2] - quad[1]) * 1.7
    lower[3] = quad[0] + (quad[3] - quad[0]) * 1.7
    target_height = max(1, int(height * 1.7))
    target = np.float32([[0, 0], [width, 0], [width, target_height], [0, target_height]])
    warped = cv2.warpPerspective(gray, cv2.getPerspectiveTransform(lower, target),
                                 (width, target_height))
    ink = (warped < 120).astype(np.uint8)
    best = 0.0
    kernel = np.ones((1, 9), np.uint8)
    for row in range(int(height * .75), min(target_height, int(height * 1.5))):
        band = ink[max(0, row - 2):min(target_height, row + 3)].max(axis=0)
        joined = cv2.morphologyEx(band.reshape(1, -1), cv2.MORPH_CLOSE, kernel)[0]
        changes = np.diff(np.r_[0, joined.astype(int), 0])
        spans = zip(np.flatnonzero(changes == 1), np.flatnonzero(changes == -1))
        best = max(best, max((end - start for start, end in spans), default=0) / width)
    return round(best, 4)


def _detection(identifier: str, box: list[float], kind: str, text: str | None,
               confidence: float | None, *, linked: list[str] | None = None,
               link_confidence: float | None = None,
               basis: str = "vision", page_region_id: str = "page_main") -> dict:
    return {"id": identifier, "page_region_id": page_region_id, "bbox": box,
            "kind": kind,
            "text": ({"text": text, "confidence": confidence, "basis": basis}
                     if text else None),
            "confidence": confidence, "linked_text_region_ids": linked or [],
            "link_confidence": link_confidence}


def openclaw_note_refiner(crop: bytes) -> tuple[str, dict]:
    """Use the configured image model only for a small handwriting crop."""
    with tempfile.TemporaryDirectory(prefix="librarian-note-") as directory:
        path = Path(directory) / "note.jpg"
        path.write_bytes(crop)
        result = subprocess.run(["openclaw", "infer", "model", "run", "--agent", "librarian",
                                 "--model", "zai/glm-5.3-flash", "--file", str(path),
                                 "--prompt", "只转录图片中的手写笔记，忽略印刷体。看不清的字用【?】表示。只输出笔记文字。",
                                 "--json"], capture_output=True, text=True, timeout=90)
    if result.returncode:
        raise RuntimeError("handwriting model unavailable")
    envelope = json.loads(result.stdout)
    outputs = envelope.get("outputs") if isinstance(envelope, dict) else None
    if (envelope.get("ok") is not True or not isinstance(outputs, list)
            or len(outputs) != 1 or not isinstance(outputs[0], dict)
            or not isinstance(outputs[0].get("text"), str)):
        raise RuntimeError("handwriting model response invalid")
    response = outputs[0]["text"].strip()
    if not response or len(response) > 500:
        raise RuntimeError("handwriting model response out of bounds")
    return response, envelope


def ocr_extractor(*, epub: Path, max_edge: int = 2000,
                  max_pixels: int = 2_000_000,
                  note_refiner: Callable[[bytes], tuple[str, dict]] | None = None,
                  preceding_page: int | None = None):
    """Return a reusable local extractor; only evidence on the photo is traced."""
    from rapidocr import RapidOCR
    import cv2
    import numpy as np

    groundtruth = EpubGroundTruth(epub)
    engine = RapidOCR()

    def extract(original: bytes) -> ExtractionOutput:
        derivative, width, height, dw, dh, operations = _derivative(
            original, max_edge=max_edge, max_pixels=max_pixels)
        with Image.open(io.BytesIO(original)) as source:
            image = ImageOps.exif_transpose(source).convert("RGB")
            pixels = np.asarray(image)
        gray = cv2.cvtColor(pixels, cv2.COLOR_RGB2GRAY)
        result = engine(pixels)
        boxes = [] if result.boxes is None else result.boxes
        texts = [] if result.txts is None else result.txts
        scores = [] if result.scores is None else result.scores
        lines = []
        for index, (quad, text, score) in enumerate(zip(boxes, texts, scores)):
            points = [[float(coord) for coord in point] for point in quad]
            box = _box(points, width, height)
            epub_text, match = groundtruth.match(str(text))
            lines.append({"id": index, "bbox": box, "quad": points, "ocr_text": str(text),
                          "ocr_score": round(float(score), 4), "epub_text": epub_text,
                          "epub_match": round(float(match), 4),
                          "underline_score": _underline_score(gray, points)})
        body = [line for line in lines if line["epub_text"] and
                len(_compact(line["ocr_text"])) >= 15 and
                line["bbox"][2] - line["bbox"][0] >= .28]
        observation: dict = {"image_space": {"width": width, "height": height,
                                             "basis": "exif_oriented_original"},
                             "pages": [], "printed_regions": [], "marks": [],
                             "annotations": [], "symbols": [], "links": [], "warnings": []}
        if len(body) >= 5:
            left = sorted(line["bbox"][0] for line in body)[len(body) // 2]
            right = sorted(line["bbox"][2] for line in body)[len(body) // 2]
            top = min(line["bbox"][1] for line in body)
            bottom = max(line["bbox"][3] for line in body)
            page_box = [max(0.0, left - .06), max(0.0, top - .12),
                        min(1.0, right + .13), min(1.0, bottom + .15)]
            markers = []
            for line in lines:
                value = re.fullmatch(r"\s*(\d{1,3})\s*", line["ocr_text"])
                attached = re.match(r"^\s*(\d{1,3})(?=[一-龥])", line["ocr_text"])
                if not value and attached and line["bbox"][0] <= left - .01:
                    value = attached
                if not value or line["bbox"][1] < top + .02:
                    continue
                number = int(value.group(1))
                if 1 <= number <= 999 and page_box[0] <= line["bbox"][0] <= page_box[2]:
                    markers.append({"number": number, "y": line["bbox"][1],
                                    "confidence": line["ocr_score"], "source": "full_ocr"})
            marker_probe = []
            if len(markers) == 1:
                # A second original-book page number is often missed when it
                # sits next to body text. Re-read only that margin at 2x.
                margin_x = left
                if markers[0]["number"] and markers[0]["y"] >= 0:
                    selected = next((line for line in lines if
                                     abs(line["bbox"][1] - markers[0]["y"]) < .002
                                     and line["ocr_text"].lstrip().startswith(str(markers[0]["number"]))), None)
                    margin_x = left if selected is None or selected["bbox"][0] < (left + right) / 2 else right
                x0 = max(0, margin_x - (.06 if margin_x == left else .12))
                x1 = min(1, margin_x + (.13 if margin_x == left else .08))
                spans = [(max(0, top - .03), markers[0]["y"] - .02),
                         (markers[0]["y"] + .02, min(1, bottom + .03))]
                windows = []
                for start, end in spans:
                    while end - start >= .08:
                        stop = min(end, start + .30)
                        windows.append((start, stop))
                        if stop == end:
                            break
                        start = stop - .04
                for y0, y1 in windows:
                    crop = image.crop((int(x0 * width), int(y0 * height),
                                       int(x1 * width), int(y1 * height)))
                    crop = crop.resize((crop.width * 2, crop.height * 2))
                    probe = engine(np.asarray(crop))
                    for quad, value, score in zip(
                            [] if probe.boxes is None else probe.boxes,
                            probe.txts or [], probe.scores or []):
                        match = re.match(r"^\s*(\d{1,3})(?=\s|[一-龥]|$)", str(value))
                        if not match:
                            continue
                        number = int(match.group(1))
                        if abs(number - markers[0]["number"]) > 2:
                            continue
                        points = [[float(point[0]) / 2 + int(x0 * width),
                                   float(point[1]) / 2 + int(y0 * height)] for point in quad]
                        box = _box(points, width, height)
                        marker_probe.append({"text": str(value), "bbox": box,
                                             "confidence": round(float(score), 4)})
                        if all(abs(box[1] - existing["y"]) > .025 for existing in markers):
                            markers.append({"number": number, "y": box[1],
                                            "confidence": round(float(score), 4),
                                            "source": "margin_ocr"})
            markers.sort(key=lambda item: item["y"])
            # Text above the first visible marker belongs to the prior
            # original page only when the preceding capture supplied that
            # exact page number; otherwise its page remains unresolved.
            cuts = [page_box[1]] + [max(page_box[1] + .001, item["y"] - .01)
                                    for item in markers] + [page_box[3]]
            for index in range(len(cuts) - 1):
                number = (markers[index - 1]["number"] if index else
                          preceding_page if markers and preceding_page == markers[0]["number"] - 1
                          else None)
                confidence = (markers[index - 1]["confidence"] if index else
                              .7 if number is not None else None)
                page = ({"value": {"label": str(number), "number": number,
                                   "scheme": "arabic"}, "confidence": confidence,
                         "basis": "vision", "status": "resolved"} if number is not None else
                        {"value": None, "confidence": None, "basis": "unknown",
                         "status": "unresolved"})
                region = [page_box[0], max(page_box[1], cuts[index] - .03),
                          page_box[2], min(page_box[3], cuts[index + 1] + .03)]
                observation["pages"].append({"id": f"page_{index}", "bbox": region,
                                             "side": "unknown", "page": page})

            def region_for(box: list[float]) -> str:
                middle = (box[1] + box[3]) / 2
                for index in range(len(cuts) - 1):
                    if cuts[index] <= middle < cuts[index + 1]:
                        return f"page_{index}"
                return f"page_{len(cuts) - 2}"
            marked = []
            for line in body:
                box = line["bbox"]
                if not (page_box[0] <= box[0] < box[2] <= page_box[2] and
                        page_box[1] <= box[1] < box[3] <= page_box[3]):
                    continue
                if line["underline_score"] < .075:
                    continue
                label = f'print_{line["id"]}'
                region_id = region_for(box)
                observation["printed_regions"].append(_detection(
                    label, box, "printed", line["epub_text"],
                    round(min(line["ocr_score"], line["epub_match"]), 4),
                    basis="source_payload" if line["epub_match"] >= .85 else "vision",
                    page_region_id=region_id))
                ink_box = [box[0], min(box[3] - .006, box[1] + .004),
                           box[2], min(page_box[3], box[3] + .012)]
                mark_id = f'underline_{line["id"]}'
                observation["marks"].append(_detection(
                    mark_id, ink_box, "underline", None,
                    round(min(.95, .5 + line["underline_score"]), 4),
                    linked=[label], link_confidence=.9, page_region_id=region_id))
                marked.append((line, mark_id))
            marked.sort(key=lambda item: item[0]["bbox"][1])
            for (previous, prior_id), (current, current_id) in zip(marked, marked[1:]):
                a, b = previous["bbox"], current["bbox"]
                overlap = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
                if (b[1] - a[1] <= .042 and
                        overlap >= .4 * min(a[2] - a[0], b[2] - b[0]) and
                        region_for(a) == region_for(b)):
                    observation["links"].append({"from_id": prior_id,
                                                 "to_id": current_id,
                                                 "kind": "continues", "confidence": .9})
            # A marked OCR line can end mid-sentence. Keep the photographed
            # stroke as evidence, but use the EPUB to quote a complete sentence.
            linked_to = {link["to_id"] for link in observation["links"]}
            next_mark = {link["from_id"]: link["to_id"] for link in observation["links"]}
            line_by_mark = {mark_id: line for line, mark_id in marked}
            printed_by_id = {item["id"]: item for item in observation["printed_regions"]}
            for line, mark_id in marked:
                if mark_id in linked_to:
                    continue
                last_id = mark_id
                while last_id in next_mark:
                    last_id = next_mark[last_id]
                print_id = f'print_{line["id"]}'
                through = line_by_mark[last_id]["epub_text"] or ""
                boundary = min((through.find(mark) for mark in "。！？"
                                if through.find(mark) >= 0), default=-1)
                if boundary >= 0:
                    through = through[:boundary + 1]
                sentence = groundtruth.sentence(line["epub_text"] or "", through)
                if sentence and print_id in printed_by_id:
                    printed_by_id[print_id]["text"]["text"] = sentence
                elif print_id in printed_by_id:
                    observation["warnings"].append(
                        f"Underline {mark_id} may need sentence boundary review")
            mark_by_id = {item["id"]: item for item in observation["marks"]}
            removed_print_ids = set()
            for link in observation["links"]:
                if link["kind"] == "continues":
                    source = mark_by_id[link["from_id"]]["linked_text_region_ids"][0]
                    target = mark_by_id[link["to_id"]]
                    removed_print_ids.update(target["linked_text_region_ids"])
                    target["linked_text_region_ids"] = [source]
            observation["printed_regions"] = [item for item in observation["printed_regions"]
                                                if item["id"] not in removed_print_ids]
            short_margin = [line for line in lines if
                            3 <= len(_compact(line["ocr_text"])) < 15 and
                            line["bbox"][0] > right - .025 and
                            line["bbox"][2] <= page_box[2] and
                            top + .06 < line["bbox"][1] < bottom - .04 and
                            not line["ocr_text"].strip().isdigit()]
            short_margin.sort(key=lambda line: line["bbox"][1])
            margin_clusters: list[list[dict]] = []
            for line in short_margin:
                if (margin_clusters and line["bbox"][1] -
                        margin_clusters[-1][-1]["bbox"][1] <= .065):
                    margin_clusters[-1].append(line)
                else:
                    margin_clusters.append([line])
            margin_ids = {line["id"] for cluster in margin_clusters if len(cluster) <= 4
                          for line in cluster}
            note_rows = []
            for line in lines:
                box = line["bbox"]
                if not (page_box[0] <= box[0] < box[2] <= page_box[2] and
                        page_box[1] <= box[1] < box[3] <= page_box[3]):
                    continue
                size = len(_compact(line["ocr_text"]))
                if line["id"] in margin_ids or (not line["epub_text"] and
                        size >= 10 and (box[1] < top or box[3] > bottom - .01)):
                    note_rows.append(line)
            note_rows.sort(key=lambda line: line["bbox"][1])
            groups: list[list[dict]] = []
            for line in note_rows:
                if (groups and line["bbox"][1] - groups[-1][-1]["bbox"][1] <= .06 and
                        abs((line["bbox"][0] + line["bbox"][2]) / 2 -
                            (groups[-1][-1]["bbox"][0] + groups[-1][-1]["bbox"][2]) / 2) < .2):
                    groups[-1].append(line)
                else:
                    groups.append([line])
            note_refinements = []
            for group in groups:
                bounds = [min(line["bbox"][0] for line in group),
                          min(line["bbox"][1] for line in group),
                          max(line["bbox"][2] for line in group),
                          max(line["bbox"][3] for line in group)]
                note = "\n".join(line["ocr_text"] for line in group)
                confidence = round(min(.7, min(line["ocr_score"] for line in group)), 4)
                if note_refiner:
                    x0 = max(0, int((bounds[0] - .07) * width))
                    y0 = max(0, int((bounds[1] - .07) * height))
                    x1 = min(width, int((bounds[2] + .07) * width))
                    y1 = min(height, int((bounds[3] + .07) * height))
                    crop = Image.fromarray(pixels).crop((x0, y0, x1, y1))
                    crop.thumbnail((1400, 1400))
                    output = io.BytesIO()
                    crop.save(output, "JPEG", quality=85)
                    try:
                        refined, response = note_refiner(output.getvalue())
                        note_refinements.append({"bbox": bounds, "ocr": note,
                                                 "model": response})
                        note = refined
                        confidence = .7
                    except (RuntimeError, OSError, ValueError, subprocess.TimeoutExpired):
                        observation["warnings"].append("Handwriting refinement unavailable")
                observation["annotations"].append(_detection(
                    f'note_{group[0]["id"]}', bounds, "margin_note", note, confidence,
                    page_region_id=region_for(bounds)))
            if note_rows:
                observation["warnings"].append(
                    "Handwriting transcription is OCR-derived and may need correction")
        else:
            observation["warnings"].append("No marked book page detected")
        raw = {"engine": "RapidOCR", "epub_sha256": groundtruth.sha256,
               "image_space": observation["image_space"], "lines": lines,
               "page_markers": locals().get("markers", []),
               "page_marker_probe": locals().get("marker_probe", []),
               "note_refinements": locals().get("note_refinements", [])}
        return ExtractionOutput(raw=json.dumps(raw, ensure_ascii=False).encode(),
                                observation=json.dumps(observation, ensure_ascii=False).encode(),
                                derivative=derivative, derivative_width=dw,
                                derivative_height=dh, operations=operations)

    return extract
