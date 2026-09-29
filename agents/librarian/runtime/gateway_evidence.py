"""Prepare a short-lived, owner-scoped photo crop for bound Feishu delivery."""
from __future__ import annotations

import argparse
import io
import json
import os
import sys
import tempfile
import time
from pathlib import Path

from PIL import Image, ImageOps

from .pipeline import render_trace_crop
from .gateway_review import pending_extractions
from .store import Library, LibrarianError

MAX_INPUT_BYTES = 8192


def _analysis_rotation(lib: Library, owner: str, *, observation_id: str | None = None,
                       run_id: str | None = None) -> int:
    """Orient a delivery crop as it appeared to the extractor."""
    if observation_id:
        observation = lib.get(owner, "PageObservation", observation_id)
    elif run_id and hasattr(lib, "db"):
        row = lib.db.execute(
            "SELECT body FROM records WHERE owner_id=? AND model='PageObservation' "
            "AND current=1 AND json_extract(body,'$.processing_run_id')=?",
            (owner, run_id)).fetchone()
        observation = json.loads(row[0]) if row else None
    else:
        observation = None
    if not observation:
        return 0
    return (180 if "Upside-down scan analyzed after 180-degree rotation"
            in observation.get("warnings", []) else 0)


def _pending_crop(lib: Library, owner: str, capture_id: str, candidate_index: int | None,
                  candidate_id: str | None, gap_index: int | None,
                  pending_run_id: str | None) -> tuple[bytes, dict, int]:
    detail = pending_extractions(lib, owner, capture_id)
    if gap_index is not None:
        if pending_run_id != detail["pending_run_id"]:
            raise LibrarianError("REVISION_CONFLICT", "pending gap run changed")
        gaps = detail["ocr_gaps"]
        if isinstance(gap_index, bool) or not isinstance(gap_index, int) or not 0 <= gap_index < len(gaps):
            raise LibrarianError("VALIDATION_FAILED", "gap index out of range")
        gap = gaps[gap_index]
        if not isinstance(gap.get("bbox"), list):
            raise LibrarianError("RECONCILIATION_REQUIRED", "gap has no image location")
        box = gap["bbox"]
        x_context, y_context = .04, .04
        source_info = {"capture_id": capture_id, "pending_run_id": pending_run_id,
                       "gap_index": gap_index, "source_status": "pending_ocr_gap"}
    else:
        if candidate_id is not None:
            matches = [index for index, item in enumerate(detail["proposed"])
                       if item["candidate_id"] == candidate_id]
            if len(matches) != 1:
                raise LibrarianError("OBJECT_NOT_FOUND", "pending candidate not found")
            candidate_index = matches[0]
        if isinstance(candidate_index, bool) or not isinstance(candidate_index, int) or not 0 <= candidate_index < len(detail["proposed"]):
            raise LibrarianError("VALIDATION_FAILED", "candidate index out of range")
        candidate = detail["proposed"][candidate_index]
        box = candidate["bbox"]
        # Handwriting OCR often detects only the bottom lines of a margin
        # note. Give the human reviewer enough context to see its beginning.
        x_context, y_context = ((.08, .10) if candidate.get("annotation") else
                                (.02, .02))
        source_info = {"capture_id": capture_id,
                       "candidate_index": candidate_index,
                       "candidate_id": candidate["candidate_id"],
                       "page": candidate["page"],
                       "source_status": "pending_review"}
    capture = lib.get(owner, "PageCapture", capture_id)
    with Image.open(io.BytesIO(lib.read_original(owner, capture_id))) as source:
        image = ImageOps.exif_transpose(source)
        image.load()
        width, height = image.size
        padded = [max(0, box[0] - x_context), max(0, box[1] - y_context),
                  min(1, box[2] + x_context), min(1, box[3] + y_context)]
        bounds = (int(padded[0] * width), int(padded[1] * height),
                  int(padded[2] * width), int(padded[3] * height))
        if bounds[0] >= bounds[2] or bounds[1] >= bounds[3]:
            raise LibrarianError("VALIDATION_FAILED", "candidate crop has no pixels")
        output = io.BytesIO()
        image.crop(bounds).save(output, format="PNG")
    return output.getvalue(), {**source_info, "capture_id": capture["id"]}, _analysis_rotation(
        lib, owner, run_id=detail.get("pending_run_id"))


def prepare_evidence(lib: Library, owner: str, trace_id: str | None, directory: Path,
                     *, capture_id: str | None = None, candidate_index: int | None = None,
                     candidate_id: str | None = None, gap_index: int | None = None,
                     pending_run_id: str | None = None) -> dict:
    if not isinstance(owner, str) or not owner or ((trace_id is None) == (capture_id is None)):
        raise LibrarianError("VALIDATION_FAILED", "choose trace or pending capture")
    if trace_id is not None:
        if (not isinstance(trace_id, str) or not trace_id.startswith("rt_") or
                candidate_index is not None or candidate_id is not None or
                gap_index is not None or pending_run_id is not None):
            raise LibrarianError("VALIDATION_FAILED", "trace ID required")
        trace = lib.get(owner, "ReadingTrace", trace_id)
        if trace.get("medium") != "physical" or trace.get("location", {}).get("kind") != "physical":
            raise LibrarianError("VALIDATION_FAILED", "photo evidence requires a physical trace")
        crop_bytes = render_trace_crop(lib, owner, trace_id, context=.2)
        source = {"trace_id": trace_id, "capture_id": trace["source"]["capture_id"],
                  "source_status": "stored_trace"}
        rotation = _analysis_rotation(
            lib, owner, observation_id=trace["source"].get("observation_id"))
    else:
        if not isinstance(capture_id, str) or not capture_id.startswith("capture_"):
            raise LibrarianError("VALIDATION_FAILED", "capture ID required")
        if sum(value is not None for value in
               (candidate_id, candidate_index, gap_index)) != 1:
            raise LibrarianError("VALIDATION_FAILED", "choose candidate or OCR gap")
        if candidate_id is not None and (not isinstance(candidate_id, str) or
                                         not candidate_id.startswith("candidate_")):
            raise LibrarianError("VALIDATION_FAILED", "candidate ID required")
        if (gap_index is None and pending_run_id is not None or
                gap_index is not None and (not isinstance(pending_run_id, str) or
                                           not pending_run_id.startswith("run_"))):
            raise LibrarianError("VALIDATION_FAILED", "gap needs current run ID")
        crop_bytes, source, rotation = _pending_crop(
            lib, owner, capture_id, candidate_index, candidate_id,
            gap_index, pending_run_id)
    with Image.open(io.BytesIO(crop_bytes)) as image_source:
        crop = image_source.convert("RGB")
        if rotation:
            crop = crop.rotate(rotation, expand=True)
        crop.thumbnail((2200, 2200))
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        for old in directory.glob("evidence-*.jpg"):
            if time.time() - old.stat().st_mtime > 3600:
                old.unlink(missing_ok=True)
        fd, name = tempfile.mkstemp(prefix="evidence-", suffix=".jpg", dir=directory)
        try:
            with os.fdopen(fd, "wb") as output:
                crop.save(output, "JPEG", quality=85, optimize=True)
        except Exception:
            Path(name).unlink(missing_ok=True)
            raise
    return {**source, "media_path": name, "mime_type": "image/jpeg"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    raw = sys.stdin.buffer.read(MAX_INPUT_BYTES + 1)
    if len(raw) > MAX_INPUT_BYTES:
        print(json.dumps({"error": {"code": "VALIDATION_FAILED"}}))
        return 2
    try:
        message = json.loads(raw)
        if not isinstance(message, dict):
            raise LibrarianError("VALIDATION_FAILED", "message must be an object")
        if not (args.root / "librarian.sqlite").is_file():
            raise LibrarianError("OBJECT_STORE_UNAVAILABLE", "Librarian store unavailable")
        with Library(args.root) as lib:
            result = prepare_evidence(lib, message.get("owner_id"),
                                      message.get("trace_id"), args.root / "delivery-evidence",
                                      capture_id=message.get("capture_id"),
                                      candidate_index=message.get("candidate_index"),
                                      candidate_id=message.get("candidate_id"),
                                      gap_index=message.get("gap_index"),
                                      pending_run_id=message.get("pending_run_id"))
    except (json.JSONDecodeError, LibrarianError) as error:
        code = error.code if isinstance(error, LibrarianError) else "VALIDATION_FAILED"
        print(json.dumps({"error": {"code": code}}))
        return 2
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
