"""Input inventory and reversible source-raster coordinate transforms."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".tif", ".tiff"}


def natural_key(path: Path) -> list[object]:
    return [int(part) if part.isdigit() else part.casefold()
            for part in re.split(r"(\d+)", path.name)]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def discover(root: Path, manifest: Path | None = None) -> list[dict]:
    root = root.resolve()
    if manifest:
        entries = json.loads(manifest.read_text(encoding="utf-8"))
        if isinstance(entries, dict):
            entries = entries["pages"]
        if not isinstance(entries, list):
            raise ValueError("manifest must be a list of pages")
    else:
        entries = [{"file": str(p.relative_to(root))} for p in sorted(
            (p for p in root.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_SUFFIXES),
            key=natural_key)]
    pages = []
    for scan_index, entry in enumerate(entries):
        source = (root / entry["file"]).resolve()
        if not source.is_relative_to(root.resolve()):
            raise ValueError(f"input escapes root: {source}")
        if not source.is_file():
            raise FileNotFoundError(source)
        if source.suffix.lower() not in IMAGE_SUFFIXES:
            raise ValueError(f"unsupported input: {source}")
        input_error = None
        try:
            with Image.open(source) as image:
                frames = getattr(image, "n_frames", 1)
                size = list(image.size)
                exif_orientation = image.getexif().get(274)
        except Exception as exc:
            frames, size, exif_orientation = 1, None, None
            input_error = f"{type(exc).__name__}: {exc}"
        file_hash = sha256(source)
        rotation = int(entry.get("rotation", 0))
        if rotation not in {0, 90, 180, 270}:
            raise ValueError(f"rotation must be 0/90/180/270: {source}")
        deskew = float(entry.get("deskew_degrees", 0))
        if not -8 <= deskew <= 8:
            raise ValueError(f"deskew_degrees must be within ±8: {source}")
        roi = entry.get("valid_page_roi") or ([0, 0, *size] if size else None)
        if size and (len(roi) != 4 or not all(isinstance(x, int) for x in roi)
                     or not (0 <= roi[0] < roi[2] <= size[0]
                                 and 0 <= roi[1] < roi[3] <= size[1])):
            raise ValueError(f"invalid valid_page_roi: {source}: {roi}")
        for frame in range(frames):
            index = len(pages)
            pages.append({
                "schema_version": "0.1", "page_id": f"page-{index:03d}-{file_hash[:10]}",
                "source_file": str(source.relative_to(root)),
                "source_path": str(source), "source_page_index": frame if frames > 1 else None,
                "source_sha256": file_hash, "scan_index": index,
                "source_size": size, "exif_orientation": exif_orientation,
                "input_error": input_error,
                "valid_page_roi": roi, "rotation": rotation,
                "deskew_degrees": deskew,
                "annotation_regions": entry.get("annotation_regions", []),
                "bracket_regions": entry.get("bracket_regions", []),
                "coordinate_space": "source_raster",
                "transform": {"crop": roi, "rotation_clockwise": rotation,
                              "deskew_degrees": deskew,
                              "source_to_working": "crop_then_rotate_then_deskew"},
            })
    return pages


def source_image(page: dict) -> np.ndarray:
    with Image.open(page["source_path"]) as image:
        if page["source_page_index"] is not None:
            image.seek(page["source_page_index"])
        rgb = np.asarray(image.convert("RGB"))
    return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)


def working_image(source: np.ndarray, page: dict) -> np.ndarray:
    x1, y1, x2, y2 = page["valid_page_roi"]
    cropped = source[y1:y2, x1:x2]
    rotation = page["rotation"]
    if rotation:
        cropped = cv2.rotate(cropped, {
            90: cv2.ROTATE_90_CLOCKWISE,
            180: cv2.ROTATE_180,
            270: cv2.ROTATE_90_COUNTERCLOCKWISE,
        }[rotation])
    if page.get("deskew_degrees"):
        height, width = cropped.shape[:2]
        matrix = cv2.getRotationMatrix2D((width / 2, height / 2),
                                         page["deskew_degrees"], 1)
        cropped = cv2.warpAffine(cropped, matrix, (width, height),
                                 flags=cv2.INTER_LINEAR,
                                 borderMode=cv2.BORDER_CONSTANT,
                                 borderValue=(255, 255, 255))
    return cropped


def _deskew_point(x: float, y: float, page: dict, inverse: bool) -> tuple[float, float]:
    angle = page.get("deskew_degrees", 0)
    if not angle:
        return x, y
    x1, y1, x2, y2 = page["valid_page_roi"]
    width, height = x2 - x1, y2 - y1
    if page["rotation"] in {90, 270}:
        width, height = height, width
    matrix = cv2.getRotationMatrix2D((width / 2, height / 2), angle, 1)
    if inverse:
        matrix = cv2.invertAffineTransform(matrix)
    return (float(matrix[0, 0] * x + matrix[0, 1] * y + matrix[0, 2]),
            float(matrix[1, 0] * x + matrix[1, 1] * y + matrix[1, 2]))


def point_to_source(x: float, y: float, page: dict) -> list[float]:
    x, y = _deskew_point(x, y, page, inverse=True)
    x1, y1, x2, y2 = page["valid_page_roi"]
    width, height = x2 - x1, y2 - y1
    rotation = page["rotation"]
    if rotation == 90:
        x, y = y, height - x
    elif rotation == 180:
        x, y = width - x, height - y
    elif rotation == 270:
        x, y = width - y, x
    return [x + x1, y + y1]


def bbox_to_source(box: list[float], page: dict) -> list[int]:
    import math
    points = [point_to_source(x, y, page) for x, y in (
        (box[0], box[1]), (box[2], box[1]), (box[2], box[3]), (box[0], box[3]))]
    width, height = page["source_size"]
    return [max(0, math.floor(min(p[0] for p in points))),
            max(0, math.floor(min(p[1] for p in points))),
            min(width, math.ceil(max(p[0] for p in points))),
            min(height, math.ceil(max(p[1] for p in points)))]


def polygon_to_source(points: list[list[float]], page: dict) -> list[list[float]]:
    return [point_to_source(float(x), float(y), page) for x, y in points]


def point_from_source(x: float, y: float, page: dict) -> list[float]:
    x1, y1, x2, y2 = page["valid_page_roi"]
    x, y = x - x1, y - y1
    width, height = x2 - x1, y2 - y1
    rotation = page["rotation"]
    if rotation == 90:
        x, y = height - y, x
    elif rotation == 180:
        x, y = width - x, height - y
    elif rotation == 270:
        x, y = y, width - x
    return list(_deskew_point(x, y, page, inverse=False))


def bbox_from_source(box: list[int], page: dict) -> list[int]:
    import math
    points = [point_from_source(x, y, page) for x, y in (
        (box[0], box[1]), (box[2], box[1]), (box[2], box[3]), (box[0], box[3]))]
    return [math.floor(min(p[0] for p in points)),
            math.floor(min(p[1] for p in points)),
            math.ceil(max(p[0] for p in points)),
            math.ceil(max(p[1] for p in points))]
