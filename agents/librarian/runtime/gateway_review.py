"""Owner-scoped, read-only preview of pending physical extraction conflicts."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from .pipeline import _traces_for_capture, normalize
from .store import Library, LibrarianError

MAX_INPUT_BYTES = 8192


def candidate_id(capture_id: str, detection_ids: list[str]) -> str:
    """Stable within a capture while the same detected ink group survives reruns."""
    marks = sorted(identifier for identifier in detection_ids
                   if identifier.startswith(("underline_", "highlight_", "note_", "symbol_")))
    payload = json.dumps([capture_id, marks], separators=(",", ":"))
    return "candidate_" + hashlib.sha256(payload.encode()).hexdigest()[:24]


def pending_extractions(lib: Library, owner: str, capture_id: str | None = None) -> dict:
    if not isinstance(owner, str) or not owner or (capture_id is not None and
            (not isinstance(capture_id, str) or not capture_id.startswith("capture_"))):
        raise LibrarianError("VALIDATION_FAILED", "owner and optional capture ID required")
    runs = [json.loads(row[0]) for row in lib.db.execute(
        "SELECT body FROM records WHERE owner_id=? AND model='ProcessingRun' AND current=1",
        (owner,))]
    latest: dict[str, dict] = {}
    for run in runs:
        if capture_id is not None and run["capture_id"] != capture_id:
            continue
        prior = latest.get(run["capture_id"])
        if prior is None or (run["created_at"], run["id"]) > (prior["created_at"], prior["id"]):
            latest[run["capture_id"]] = run
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
        return {"pending": summaries, "more": len(pending) > 10}
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
    ocr_gaps = []
    visual_checks = []
    try:
        raw = json.loads(lib._read_object(observation["raw_output_asset"]))
        for item in raw.get("underline_refinements", []):
            answer = item.get("answer", {})
            visual_checks.append({"mark_ids": item.get("mark_ids", []),
                                  "has_underline": answer.get("has_underline"),
                                  "underlined_text": answer.get("underlined_text", ""),
                                  "uncertain": answer.get("uncertain"),
                                  "epub_match": item.get("epub_match")})
        printed_boxes = [item["bbox"] for item in observation["printed_regions"]]
        for line in raw.get("lines", []):
            if (line.get("underline_score", 0) < .065 or
                    line.get("epub_match", 0) >= .85):
                continue
            box = line.get("bbox")
            if not isinstance(box, list) or len(box) != 4:
                continue
            if box[2] - box[0] < .28:
                continue
            middle = (box[1] + box[3]) / 2
            if not any(page["bbox"][1] <= middle <= page["bbox"][3]
                       for page in observation["pages"]):
                continue
            if any(abs(box[1] - printed[1]) < .012 for printed in printed_boxes):
                continue
            ocr_gaps.append({"bbox": box, "underline_score": line["underline_score"],
                             "reason": "visible_ink_without_reliable_print_text"})
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
            "decision": "human_review_required"}


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
            raise LibrarianError("VALIDATION_FAILED", "request must be an object")
        if not (args.root / "librarian.sqlite").is_file():
            raise LibrarianError("OBJECT_STORE_UNAVAILABLE", "Librarian store unavailable")
        with Library(args.root) as lib:
            result = pending_extractions(lib, message.get("owner_id"),
                                         message.get("capture_id"))
    except (json.JSONDecodeError, LibrarianError) as error:
        code = error.code if isinstance(error, LibrarianError) else "VALIDATION_FAILED"
        print(json.dumps({"error": {"code": code}}))
        return 2
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
