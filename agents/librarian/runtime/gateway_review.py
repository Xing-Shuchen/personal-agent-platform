"""Owner-scoped, read-only preview of pending physical extraction conflicts."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

from .pipeline import _traces_for_capture, normalize
from .store import Library, LibrarianError
from .gateway_errors import write_error

MAX_INPUT_BYTES = 8192


def intake_failures(root: Path, owner: str) -> list[dict]:
    """Expose only sanitized, owner-scoped hook failures for retry diagnosis."""
    directory = root / "intake-status"
    if not directory.is_dir() or directory.is_symlink():
        return []
    found = []
    try:
        paths = list(directory.iterdir())
    except OSError:
        return []
    for path in paths:
        if not re.fullmatch(r"[0-9a-f]{64}\.json", path.name):
            continue
        try:
            if path.is_symlink() or not path.is_file() or path.stat().st_size > 8192:
                continue
            item = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, ValueError):
            continue
        if (not isinstance(item, dict) or item.get("owner_id") != owner or
                item.get("state") != "failed"):
            continue
        if not all(isinstance(item.get(key), str) for key in
                   ("message_id", "channel_id", "account_id", "code", "stage", "updated_at")):
            continue
        if not isinstance(item.get("retryable"), bool):
            continue
        found.append({key: item[key] for key in
                      ("message_id", "channel_id", "account_id", "code", "stage",
                       "retryable", "updated_at")})
    found.sort(key=lambda item: item["updated_at"], reverse=True)
    return found[:10]


def worker_launch_status(root: Path, owner: str) -> list[dict]:
    """Last launcher outcome per worker mode; never implies batch completion."""
    directory = root / "worker-launch-status"
    if not directory.is_dir() or directory.is_symlink():
        return []
    found = []
    for mode in ("physical", "digital"):
        key = hashlib.sha256(json.dumps([owner, mode], separators=(",", ":")).encode()).hexdigest()
        path = directory / f"{key}.json"
        try:
            if path.is_symlink() or not path.is_file() or path.stat().st_size > 8192:
                continue
            item = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, ValueError):
            continue
        if (not isinstance(item, dict) or item.get("owner_id") != owner or
                item.get("mode") != mode or item.get("state") not in {"spawned", "failed"} or
                not isinstance(item.get("updated_at"), str)):
            continue
        found.append({"mode": mode, "state": item["state"],
                      "code": "WORKER_SPAWN_FAILED" if item["state"] == "failed" else None,
                      "updated_at": item["updated_at"]})
    return found


def candidate_id(capture_id: str, detection_ids: list[str]) -> str:
    """Stable within a capture while the same detected ink group survives reruns."""
    marks = sorted(identifier for identifier in detection_ids
                   if identifier.startswith(("underline_", "highlight_", "note_", "symbol_"))
                   or re.fullmatch(r"bookscan_(?:\d+_mark|note_\d+)", identifier))
    payload = json.dumps([capture_id, marks], separators=(",", ":"))
    return "candidate_" + hashlib.sha256(payload.encode()).hexdigest()[:24]


def _reviewable_ocr_gaps(raw: dict, observation: dict) -> list[dict]:
    """Expose Bookscan ink groups that still need a person's review."""
    width = observation["image_space"]["width"]
    height = observation["image_space"]["height"]
    gaps = []
    for candidate in raw.get("review_candidates", []):
        box = candidate.get("bbox") or candidate.get("group_bbox")
        if isinstance(box, list) and len(box) == 4:
            box = [box[0] / width, box[1] / height,
                   box[2] / width, box[3] / height]
        gaps.append({"bbox": box, "reason": candidate.get("reason", "bookscan_review_candidate"),
                     "candidate": candidate})
    return gaps


def pending_extractions(lib: Library, owner: str, capture_id: str | None = None) -> dict:
    if not isinstance(owner, str) or not owner or (capture_id is not None and
            (not isinstance(capture_id, str) or not capture_id.startswith("capture_"))):
        raise LibrarianError("VALIDATION_FAILED", "owner and optional capture ID required")
    runs = [(row[0], json.loads(row[1])) for row in lib.db.execute(
        "SELECT rowid,body FROM records WHERE owner_id=? AND model='ProcessingRun' "
        "AND current=1", (owner,))]
    latest: dict[str, dict] = {}
    latest_rowid: dict[str, int] = {}
    for rowid, run in runs:
        if capture_id is not None and run["capture_id"] != capture_id:
            continue
        if rowid > latest_rowid.get(run["capture_id"], -1):
            latest[run["capture_id"]] = run
            latest_rowid[run["capture_id"]] = rowid
    pending = [run for run in latest.values() if run["outcome"] == "pending" and
               "RECONCILIATION_REQUIRED" in run["issues"]]
    if capture_id is None:
        summaries = []
        for run in sorted(pending, key=lambda item: item["created_at"], reverse=True)[:10]:
            item = {"capture_id": run["capture_id"], "run_id": run["id"],
                    "extractor_version": run["extractor_version"]}
            try:
                detail = pending_extractions(lib, owner, run["capture_id"])
                item.update({"current_count": detail["current_count"],
                             "proposed_count": detail["proposed_count"],
                             "book_title": detail["book_title"],
                             "pages": sorted({str(trace["page"]["label"]) if trace["page"]
                                              else "unknown" for trace in detail["proposed"]}),
                             "ocr_gap_count": len(detail["ocr_gaps"])})
            except LibrarianError:
                item["summary_unavailable"] = True
            summaries.append(item)
        return {"pending": summaries, "more": len(pending) > 10,
                "intake_failures": intake_failures(lib.root, owner),
                "worker_launch_status": worker_launch_status(lib.root, owner)}
    if not pending:
        raise LibrarianError("OBJECT_NOT_FOUND", "no pending extraction for capture")
    run = pending[0]
    capture = lib.get(owner, "PageCapture", capture_id)
    observations = [json.loads(row[0]) for row in lib.db.execute(
        "SELECT body FROM records WHERE owner_id=? AND model='PageObservation' AND current=1",
        (owner,))]
    matching = [item for item in observations if item["processing_run_id"] == run["id"]]
    if len(matching) != 1:
        raise LibrarianError("RECONCILIATION_REQUIRED", "pending observation missing")
    observation = matching[0]
    row = lib.db.execute("SELECT body FROM records WHERE owner_id=? AND model='CaptureResolution' "
                         "AND current=1 AND json_extract(body,'$.capture_id')=?",
                         (owner, capture_id)).fetchone()
    if row is None:
        raise LibrarianError("RECONCILIATION_REQUIRED", "capture resolution missing")
    resolution = json.loads(row[0])
    resolution["pages"] = observation["pages"]
    book_title = None
    if resolution["work"]["value"]:
        book_title = lib.get(owner, "Work", resolution["work"]["value"])["title"]
    state = "resolved" if all(resolution[key]["value"] for key in
                              ("session", "work", "edition", "book_instance")) else "unresolved"
    vocabulary = None
    if run.get("vocabulary_config_ref"):
        vocabulary = json.loads(lib._read_object(run["vocabulary_config_ref"]))
    proposed = normalize(capture, observation, resolution, state,
                         run["normalizer_version"], vocabulary=vocabulary)

    def brief(trace: dict) -> dict:
        return {"trace_id": trace["id"], "candidate_id": candidate_id(capture_id, trace["source"]["detection_ids"]),
                "revision": trace["revision"],
                "page": trace["location"]["page"],
                "bbox": trace["location"]["bbox"],
                "types": trace["trace_types"],
                "printed_text": (trace["content"]["printed_text"]["text"] or "")[:500],
                "annotation": (trace["content"]["annotation"]["text"] or "")[:300],
                "detection_ids": trace["source"]["detection_ids"]}

    old = _traces_for_capture(lib, owner, capture_id)
    review_decisions = []
    if lib.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' "
                      "AND name='gateway_review_decisions'").fetchone():
        rows = lib.db.execute("SELECT candidate_id,decision,corrected_text,created_at "
                              "FROM gateway_review_decisions WHERE owner_id=? AND "
                              "capture_id=? AND pending_run_id=? ORDER BY rowid",
                              (owner, capture_id, run["id"])).fetchall()
        latest_decisions = {row["candidate_id"]: dict(row) for row in rows}
        review_decisions = list(latest_decisions.values())
    ocr_gaps = []
    visual_checks = []
    try:
        raw = json.loads(lib._read_object(observation["raw_output_asset"]))
        ocr_gaps = _reviewable_ocr_gaps(raw, observation)
    except (ValueError, TypeError, LibrarianError):
        ocr_gaps.append({"reason": "raw_ocr_unavailable"})
    return {"capture_id": capture_id, "pending_run_id": run["id"],
            "book_title": book_title,
            "extractor_version": run["extractor_version"],
            "current_count": len(old), "proposed_count": len(proposed),
            "current": [brief(item) for item in old],
            "proposed": [brief(item) for item in proposed],
            "ocr_gaps": ocr_gaps[:20],
            "visual_checks": visual_checks[:20],
            "review_decisions": review_decisions,
            "decision": "human_review_required"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    raw = sys.stdin.buffer.read(MAX_INPUT_BYTES + 1)
    if len(raw) > MAX_INPUT_BYTES:
        return write_error(LibrarianError("VALIDATION_FAILED", "input too large"), "gateway.review")
    try:
        message = json.loads(raw)
        if not isinstance(message, dict):
            raise LibrarianError("VALIDATION_FAILED", "request must be an object")
        if not (args.root / "librarian.sqlite").is_file():
            raise LibrarianError("OBJECT_STORE_UNAVAILABLE", "Librarian store unavailable")
        with Library(args.root) as lib:
            result = pending_extractions(lib, message.get("owner_id"),
                                         message.get("capture_id"))
    except Exception as error:
        return write_error(error, "gateway.review")
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
