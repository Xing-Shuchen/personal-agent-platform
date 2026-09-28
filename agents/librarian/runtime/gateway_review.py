"""Owner-scoped, read-only preview of pending physical extraction conflicts."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .pipeline import _traces_for_capture, normalize
from .store import Library, LibrarianError

MAX_INPUT_BYTES = 8192


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
        return {"pending": [{"capture_id": run["capture_id"], "run_id": run["id"],
                             "extractor_version": run["extractor_version"]}
                            for run in pending[:30]], "more": len(pending) > 30}
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
    state = "resolved" if all(resolution[key]["value"] for key in
                              ("session", "work", "edition", "book_instance")) else "unresolved"
    vocabulary = None
    if run.get("vocabulary_config_ref"):
        vocabulary = json.loads(lib._read_object(run["vocabulary_config_ref"]))
    proposed = normalize(capture, observation, resolution, state,
                         run["normalizer_version"], vocabulary=vocabulary)

    def brief(trace: dict) -> dict:
        return {"trace_id": trace["id"], "revision": trace["revision"],
                "page": trace["location"]["page"],
                "bbox": trace["location"]["bbox"],
                "types": trace["trace_types"],
                "printed_text": (trace["content"]["printed_text"]["text"] or "")[:500],
                "annotation": (trace["content"]["annotation"]["text"] or "")[:300],
                "detection_ids": trace["source"]["detection_ids"]}

    old = _traces_for_capture(lib, owner, capture_id)
    return {"capture_id": capture_id, "pending_run_id": run["id"],
            "extractor_version": run["extractor_version"],
            "current_count": len(old), "proposed_count": len(proposed),
            "current": [brief(item) for item in old],
            "proposed": [brief(item) for item in proposed],
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
