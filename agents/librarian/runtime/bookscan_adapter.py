"""Run the local bookscan processor and adapt its evidence to PageObservation."""
from __future__ import annotations

import hashlib
import io
import json
import os
import subprocess
import sys
import tempfile
from contextlib import nullcontext
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageOps
import yaml

from .pipeline import ExtractionOutput


REPO = Path(__file__).resolve().parents[3]
SAMPLE_ROOT = REPO / "local-processing"
LOCAL_CONFIG = SAMPLE_ROOT / "config.local.yaml"


@lru_cache(maxsize=1)
def processor_fingerprint() -> str:
    """Bind extraction retries to processing code, config and weights.

    Review-page rendering and evaluation only consume a finished run. Editing
    either must not re-run OCR or create a pending reconciliation.
    """
    digest = hashlib.sha256()
    sources = [*sorted(path for path in (REPO / "bookscan").glob("*.py")
                       if path.name not in {"review.py", "evaluate.py"}),
               SAMPLE_ROOT / "config.yaml", LOCAL_CONFIG, SAMPLE_ROOT / "manifest.json",
               SAMPLE_ROOT / "inputs.sha256"]
    # The adapter's imports and fingerprint implementation do not change the
    # observation; adapt_report and the extractor below do.
    adapter_processing = Path(__file__).read_bytes().split(b"\ndef _box(", 1)[1]
    digest.update(b"def _box(" + adapter_processing)
    for name in ("PP-OCRv5_mobile_det", "PP-OCRv5_mobile_rec"):
        sources += sorted((Path.home() / ".paddlex" / "official_models" / name).rglob("*"))
    for path in sources:
        if path.is_file():
            digest.update(str(path).encode())
            with path.open("rb") as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(chunk)
    core = digest.hexdigest()[:16]
    # 30a517d9be8dd3b7 was minted when an ISBN-only review.py change was
    # included in the old fingerprint. Its processing core is this exact hash.
    # Preserve the run identity for the current deployed core; any processing
    # change still yields a new hash and goes through reconciliation.
    return {"152f23333f2f08f7": "30a517d9be8dd3b7"}.get(core, core)


def _jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()]


def _box(box: list[int], width: int, height: int) -> list[float]:
    x1, y1, x2, y2 = box
    if not (0 <= x1 < x2 <= width and 0 <= y1 < y2 <= height):
        raise ValueError("bookscan returned an invalid source-raster bbox")
    return [round(x1 / width, 6), round(y1 / height, 6),
            round(x2 / width, 6), round(y2 / height, 6)]


def _text(value: str | None, confidence: float | None = None,
          basis: str = "vision") -> dict:
    return {"text": value or None, "confidence": confidence if value else None,
            "basis": basis if value else "unknown"}


def adapt_report(report: dict, width: int, height: int) -> dict:
    """Use Bookscan's accepted EPUB expansion; keep uncertain OCR for review."""
    pages = report["pages"]
    if len(pages) != 1 or pages[0]["processing_status"] != "processed":
        raise ValueError("bookscan must process exactly one page per capture")
    page = pages[0]
    number = page["page_number"]
    observed = number["observed_value"] if number["status"] == "observed" else None
    page_field = ({"value": {"label": str(number["observed_label"]),
                              "number": observed, "scheme": "arabic"},
                   "confidence": None, "basis": "vision", "status": "resolved"}
                  if observed else {"value": None, "confidence": None,
                                    "basis": "unknown", "status": "unresolved"})
    observation = {"image_space": {"width": width, "height": height,
                                    "basis": "exif_oriented_original"},
                   "pages": [{"id": "page_0", "bbox": [0, 0, 1, 1],
                              "side": "unknown", "page": page_field}],
                   "printed_regions": [], "marks": [], "annotations": [],
                   "symbols": [], "links": [], "warnings": list(page.get("issues", []))}
    lines_by_id = {line["line_id"]: line for line in report["lines"]}
    for index, group in enumerate(report["groups"]):
        group_id = f"bookscan_{index}"
        text_id = f"{group_id}_text"
        mark_id = f"{group_id}_mark"
        rows = [lines_by_id[line_id] for line_id in group["line_ids"]]
        ocr = "\n".join(row.get("ocr_raw", "") for row in rows).strip()
        scores = [row.get("ocr_score") for row in rows]
        score = min(scores) if scores and all(x is not None for x in scores) else None
        grounded = (group.get("text_basis") == "epub_punctuation_expansion" and
                    group.get("match_status") in {"matched", "needs_review"} and
                    bool(group.get("text_effective")))
        printed_text = group["text_effective"] if grounded else ocr
        basis = "source_payload" if grounded else "vision"
        if grounded:
            # Confidence describes the chosen text, not OCR's ability to read
            # the photo. The EPUB supplies that text exactly after alignment.
            score = 1.0
        group_box = group.get("group_bbox") or group.get("bbox")
        observation["printed_regions"].append({
            "id": text_id, "page_region_id": "page_0", "bbox": _box(group_box, width, height),
            "kind": "printed", "text": _text(printed_text, score, basis), "confidence": score,
            "linked_text_region_ids": [], "link_confidence": None})
        ink_boxes = group.get("underline_bboxes") or []
        if ink_boxes:
            ink_box = [min(b[0] for b in ink_boxes), min(b[1] for b in ink_boxes),
                       max(b[2] for b in ink_boxes), max(b[3] for b in ink_boxes)]
        else:
            ink_box = group_box
        observation["marks"].append({
            "id": mark_id, "page_region_id": "page_0", "bbox": _box(ink_box, width, height),
            "kind": "bracket" if group["mark_type"] == "corner_bracket" else "underline",
            "text": None, "confidence": None,
            "linked_text_region_ids": [text_id] if ocr else [],
            "link_confidence": .9 if ocr else None})
        if group.get("match_status") != "matched":
            observation["warnings"].append(f"{group_id}:epub_alignment_needs_review")
    for index, note in enumerate(report["annotations"]):
        observation["annotations"].append({
            "id": f"bookscan_note_{index}", "page_region_id": "page_0",
            "bbox": _box(note["bbox"], width, height), "kind": "margin_note",
            "text": _text(note.get("ocr_raw"), note.get("ocr_score")),
            "confidence": None, "linked_text_region_ids": [], "link_confidence": None})
    if report["review_candidates"]:
        observation["warnings"].append("unassigned_ink_candidates")
    if report["failures"]:
        observation["warnings"].append("bookscan_partial_failure")
    return observation


def _manifest_entry(original: bytes, oriented_size: tuple[int, int]) -> dict:
    """Reuse hand reviewed regions only for the exact sample bytes."""
    manifest_path = SAMPLE_ROOT / "manifest.json"
    hashes_path = SAMPLE_ROOT / "inputs.sha256"
    if not manifest_path.is_file() or not hashes_path.is_file():
        return {"file": "capture.png", "annotation_regions": [], "bracket_regions": []}
    sample_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    digest = hashlib.sha256(original).hexdigest()
    known = dict(line.strip().split(maxsplit=1) for line in
                 hashes_path.read_text(encoding="utf-8").splitlines()
                 if line.strip())
    for entry in sample_manifest["pages"]:
        if known.get(digest) == entry["file"]:
            with Image.open(io.BytesIO(original)) as image:
                if image.getexif().get(274) not in (None, 1):
                    break
            return {**entry, "file": "capture.png"}
    return {"file": "capture.png", "annotation_regions": [],
            "bracket_regions": []}


def bookscan_extractor(epub: Path | None, *, python: Path | None = None,
                       work_root: Path | None = None):
    """Return an extractor that invokes the isolated PaddleOCR environment."""
    interpreter = str(python or os.environ.get("LIBRARIAN_BOOKSCAN_PYTHON") or sys.executable)
    config_path = LOCAL_CONFIG if LOCAL_CONFIG.is_file() else SAMPLE_ROOT / "config.yaml"
    template = yaml.safe_load(config_path.read_text(encoding="utf-8"))

    def extract(original: bytes) -> ExtractionOutput:
        with Image.open(io.BytesIO(original)) as image:
            oriented = ImageOps.exif_transpose(image).convert("RGB")
        width, height = oriented.size
        derivative = io.BytesIO()
        oriented.save(derivative, format="PNG")
        if work_root is None:
            workspace = tempfile.TemporaryDirectory(prefix="librarian-bookscan-")
        else:
            runs_root = work_root.resolve()
            runs_root.mkdir(parents=True, exist_ok=True)
            workspace = nullcontext(tempfile.mkdtemp(prefix="run-", dir=runs_root))
        with workspace as temporary:
            root = Path(temporary)
            (root / "capture.png").write_bytes(derivative.getvalue())
            (root / "manifest.json").write_text(json.dumps({"pages": [
                _manifest_entry(original, (width, height))]}, ensure_ascii=False),
                encoding="utf-8")
            config = {**template, "root": str(root), "epub": str(epub.resolve()) if epub else None}
            (root / "config.yaml").write_text(json.dumps(config, ensure_ascii=False),
                                               encoding="utf-8")
            result = subprocess.run([interpreter, "-m", "bookscan", "run", "--config",
                                     str(root / "config.yaml")], cwd=REPO,
                                    env={**os.environ, "PYTHONPATH": str(REPO)},
                                    capture_output=True, text=True, timeout=900, check=False)
            if result.returncode not in (0, 1):
                raise RuntimeError(f"bookscan failed with exit code {result.returncode}: "
                                   f"{result.stderr[-500:]}")
            output = Path(result.stdout.strip().splitlines()[-1])
            if not output.is_relative_to(root) or not output.is_dir():
                raise RuntimeError("bookscan did not return a run directory")
            report = {key: _jsonl(output / f"{key}.jsonl") for key in
                      ("pages", "lines", "groups", "annotations", "brackets",
                       "review_candidates", "failures")}
            report["run"] = json.loads((output / "run.json").read_text(encoding="utf-8"))
            observation = adapt_report(report, width, height)
            return ExtractionOutput(raw=json.dumps(report, ensure_ascii=False).encode(),
                                    derivative=derivative.getvalue(),
                                    derivative_width=width, derivative_height=height,
                                    operations=("exif_transpose",),
                                    observation=json.dumps(observation,
                                                           ensure_ascii=False).encode())

    return extract
