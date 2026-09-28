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

from PIL import Image

from .pipeline import render_trace_crop
from .store import Library, LibrarianError

MAX_INPUT_BYTES = 8192


def prepare_evidence(lib: Library, owner: str, trace_id: str, directory: Path) -> dict:
    if not isinstance(owner, str) or not owner or not isinstance(trace_id, str) or not trace_id.startswith("rt_"):
        raise LibrarianError("VALIDATION_FAILED", "owner and trace required")
    trace = lib.get(owner, "ReadingTrace", trace_id)
    if trace.get("medium") != "physical" or trace.get("location", {}).get("kind") != "physical":
        raise LibrarianError("VALIDATION_FAILED", "photo evidence requires a physical trace")
    crop_bytes = render_trace_crop(lib, owner, trace_id, context=.2)
    with Image.open(io.BytesIO(crop_bytes)) as source:
        crop = source.convert("RGB")
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
    return {"trace_id": trace_id, "media_path": name, "mime_type": "image/jpeg",
            "capture_id": trace["source"]["capture_id"]}


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
                                      message.get("trace_id"), args.root / "delivery-evidence")
    except (json.JSONDecodeError, LibrarianError) as error:
        code = error.code if isinstance(error, LibrarianError) else "VALIDATION_FAILED"
        print(json.dumps({"error": {"code": code}}))
        return 2
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
