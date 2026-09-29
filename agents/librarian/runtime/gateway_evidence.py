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


def _pending_crop(lib: Library, owner: str, capture_id: str, candidate_index: int) -> tuple[bytes, dict]:
    detail = pending_extractions(lib, owner, capture_id)
    if isinstance(candidate_index, bool) or not isinstance(candidate_index, int) or not 0 <= candidate_index < len(detail["proposed"]):
        raise LibrarianError("VALIDATION_FAILED", "candidate index out of range")
    candidate = detail["proposed"][candidate_index]
    box = candidate["bbox"]
    capture = lib.get(owner, "PageCapture", capture_id)
    with Image.open(io.BytesIO(lib.read_original(owner, capture_id))) as source:
        image = ImageOps.exif_transpose(source)
        image.load()
        width, height = image.size
        padded = [max(0, box[0] - .02), max(0, box[1] - .02),
                  min(1, box[2] + .02), min(1, box[3] + .02)]
        bounds = (int(padded[0] * width), int(padded[1] * height),
                  int(padded[2] * width), int(padded[3] * height))
        if bounds[0] >= bounds[2] or bounds[1] >= bounds[3]:
            raise LibrarianError("VALIDATION_FAILED", "candidate crop has no pixels")
        output = io.BytesIO()
        image.crop(bounds).save(output, format="PNG")
    return output.getvalue(), {"capture_id": capture["id"],
                                "candidate_index": candidate_index,
                                "page": candidate["page"],
                                "source_status": "pending_review"}


def prepare_evidence(lib: Library, owner: str, trace_id: str | None, directory: Path,
                     *, capture_id: str | None = None, candidate_index: int | None = None) -> dict:
    if not isinstance(owner, str) or not owner or ((trace_id is None) == (capture_id is None)):
        raise LibrarianError("VALIDATION_FAILED", "choose trace or pending capture")
    if trace_id is not None:
        if not isinstance(trace_id, str) or not trace_id.startswith("rt_") or candidate_index is not None:
            raise LibrarianError("VALIDATION_FAILED", "trace ID required")
        trace = lib.get(owner, "ReadingTrace", trace_id)
        if trace.get("medium") != "physical" or trace.get("location", {}).get("kind") != "physical":
            raise LibrarianError("VALIDATION_FAILED", "photo evidence requires a physical trace")
        crop_bytes = render_trace_crop(lib, owner, trace_id, context=.2)
        source = {"trace_id": trace_id, "capture_id": trace["source"]["capture_id"],
                  "source_status": "stored_trace"}
    else:
        if not isinstance(capture_id, str) or not capture_id.startswith("capture_"):
            raise LibrarianError("VALIDATION_FAILED", "capture ID required")
        crop_bytes, source = _pending_crop(lib, owner, capture_id, candidate_index)
    with Image.open(io.BytesIO(crop_bytes)) as image_source:
        crop = image_source.convert("RGB")
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
                                      candidate_index=message.get("candidate_index"))
    except (json.JSONDecodeError, LibrarianError) as error:
        code = error.code if isinstance(error, LibrarianError) else "VALIDATION_FAILED"
        print(json.dumps({"error": {"code": code}}))
        return 2
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
