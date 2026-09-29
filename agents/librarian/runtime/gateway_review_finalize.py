"""Apply an explicit authenticated review of every candidate in one scan run."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

from .gateway_review import pending_extractions
from .ocr import EpubGroundTruth, _compact
from .pipeline import reconcile_extraction
from .store import Library, LibrarianError

MAX_INPUT_BYTES = 8192


def _verify_printed_boundaries(lib: Library, owner: str, run: dict,
                               proposed: list[dict], accepted: dict[str, str | None]) -> None:
    """Keep EPUB alignment within the ink-linked photographed OCR lines."""
    rows = lib.db.execute("SELECT body FROM records WHERE owner_id=? AND "
                          "model='PageObservation' AND current=1", (owner,)).fetchall()
    observation = next((item for row in rows if
                        (item := json.loads(row[0]))["processing_run_id"] == run["id"]), None)
    if observation is None:
        raise LibrarianError("RECONCILIATION_REQUIRED", "pending observation missing")
    raw = json.loads(lib._read_object(observation["raw_output_asset"]))
    lines = {line["id"]: line["ocr_text"] for line in raw.get("lines", [])
             if isinstance(line, dict) and isinstance(line.get("id"), int) and
             isinstance(line.get("ocr_text"), str)}
    isbn = re.search(r"^rapidocr-epub-notes-[^:]+:(\d{13}):", run["extractor_version"])
    epub_path = lib.root / "source-books" / f"{isbn.group(1)}.epub" if isbn else None
    groundtruth = EpubGroundTruth(epub_path) if epub_path and epub_path.is_file() else None
    for item in proposed:
        candidate = item["candidate_id"]
        if candidate not in accepted:
            continue
        text = accepted[candidate] or item["printed_text"]
        normalized = _compact(text)
        if len(normalized) < 12:
            raise LibrarianError("RECONCILIATION_REQUIRED", "accepted text incomplete")
        line_ids = sorted({int(identifier.split("_", 1)[1]) for identifier in
                           item["detection_ids"] if re.fullmatch(r"underline_\d+", identifier)})
        if line_ids and all(index in lines for index in line_ids):
            photographed = _compact("".join(lines[index] for index in line_ids))
            if normalized[:6] not in photographed or normalized[-6:] not in photographed:
                raise LibrarianError("RECONCILIATION_REQUIRED", "text boundary absent from photo OCR")
        if groundtruth and groundtruth.match(text)[1] < .95:
            raise LibrarianError("RECONCILIATION_REQUIRED", "accepted text disagrees with EPUB")


def auto_reconcile_fully_reviewed(lib: Library, owner: str, capture_id: str) -> dict | None:
    """Finish a complete authenticated review when it replaces only empty old traces.

    The owner already authorized photo ingestion. This path is limited to
    previously unusable empty-text traces; contentful/corrected traces still
    require the separate explicit replacement operation.
    """
    try:
        detail = pending_extractions(lib, owner, capture_id)
    except LibrarianError as error:
        if error.code == "OBJECT_NOT_FOUND":
            return None
        raise
    candidates = {item["candidate_id"] for item in detail["proposed"]}
    decisions = {item["candidate_id"]: item for item in detail["review_decisions"]}
    if candidates != decisions.keys():
        return None
    if not candidates and (detail["current"] or detail["ocr_gaps"] or
                           not detail["visual_checks"] or any(
                               check["has_underline"] is not False or check["uncertain"]
                               for check in detail["visual_checks"])):
        return None
    if any(item["printed_text"] or item["annotation"] for item in detail["current"]):
        return None
    for item in detail["current"]:
        reasons = [json.loads(row[0])["payload"]["reason"] for row in lib.db.execute(
            "SELECT body FROM outbox WHERE owner_id=? AND event_type='reading.trace.corrected' "
            "AND json_extract(body,'$.payload.trace_id')=?",
            (owner, item["trace_id"]))]
        if len(reasons) != item["revision"] - 1 or any(
                reason != "capture resolution" for reason in reasons):
            return None
    with lib.transaction():
        current = pending_extractions(lib, owner, capture_id)
        if (current["pending_run_id"] != detail["pending_run_id"] or
                {(item["trace_id"], item["revision"]) for item in current["current"]} !=
                {(item["trace_id"], item["revision"]) for item in detail["current"]} or
                {item["candidate_id"]: item for item in current["review_decisions"]} != decisions):
            raise LibrarianError("REVISION_CONFLICT", "review changed during reconciliation")
        run = lib.get(owner, "ProcessingRun", detail["pending_run_id"])
        accepted = {key: item["corrected_text"] for key, item in decisions.items()
                    if item["decision"] == "accept"}
        _verify_printed_boundaries(lib, owner, run, current["proposed"], accepted)
        traces = reconcile_extraction(lib, owner, capture_id, run["extractor_version"],
                                      reviewed_candidates=accepted,
                                      expected_run_id=run["id"])
    return {"capture_id": capture_id, "run_id": run["id"],
            "accepted": len(traces), "rejected": len(candidates) - len(traces),
            "basis": ("complete_authenticated_review" if candidates
                      else "visual_negative_no_marks")}


def finalize_review(lib: Library, message: dict) -> dict:
    owner, actor, source = (message.get(key) for key in
                            ("owner_id", "actor_id", "source"))
    capture_id, run_id = message.get("capture_id"), message.get("pending_run_id")
    current = message.get("expected_current")
    if (not all(isinstance(value, str) and value for value in
                (owner, actor, capture_id, run_id)) or not isinstance(source, dict) or
            message.get("replace_all_current") is not True or not isinstance(current, list)):
        raise LibrarianError("VALIDATION_FAILED", "explicit reviewed replacement required")
    keys = ("transport", "account_id", "conversation_id", "source_event_id")
    if any(not isinstance(source.get(key), str) or not source[key] for key in keys):
        raise LibrarianError("VALIDATION_FAILED", "trusted inbound source required")
    if any(not isinstance(item, dict) or
           not isinstance(item.get("trace_id"), str) or
           not isinstance(item.get("revision"), int) for item in current):
        raise LibrarianError("VALIDATION_FAILED", "expected current trace refs required")
    source_key = hashlib.sha256(json.dumps(
        [owner, actor, *[source[key] for key in keys], capture_id],
        ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
    fingerprint = hashlib.sha256(json.dumps(
        [capture_id, run_id, sorted((item["trace_id"], item["revision"])
                                  for item in current)],
        ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
    lib.db.execute("CREATE TABLE IF NOT EXISTS gateway_review_finalizations ("
                   "owner_id TEXT NOT NULL, source_key TEXT NOT NULL, "
                   "fingerprint TEXT NOT NULL, result TEXT NOT NULL, "
                   "PRIMARY KEY(owner_id,source_key))")
    with lib.transaction():
        prior = lib.db.execute("SELECT fingerprint,result FROM gateway_review_finalizations "
                               "WHERE owner_id=? AND source_key=?", (owner, source_key)).fetchone()
        if prior:
            if prior["fingerprint"] != fingerprint:
                raise LibrarianError("IDEMPOTENCY_CONFLICT", "source review changed")
            return json.loads(prior["result"])
        detail = pending_extractions(lib, owner, capture_id)
        if detail["pending_run_id"] != run_id or {
                (item["trace_id"], item["revision"]) for item in detail["current"]} != {
                (item["trace_id"], item["revision"]) for item in current}:
            raise LibrarianError("REVISION_CONFLICT", "review snapshot changed")
        candidates = {item["candidate_id"] for item in detail["proposed"]}
        decisions = {item["candidate_id"]: item for item in detail["review_decisions"]}
        if candidates != decisions.keys():
            raise LibrarianError("RECONCILIATION_REQUIRED", "every proposed candidate needs review")
        accepted = {key: item["corrected_text"] for key, item in decisions.items()
                    if item["decision"] == "accept"}
        run = lib.get(owner, "ProcessingRun", run_id)
        _verify_printed_boundaries(lib, owner, run, detail["proposed"], accepted)
        traces = reconcile_extraction(lib, owner, capture_id, run["extractor_version"],
                                      reviewed_candidates=accepted,
                                      expected_run_id=run_id)
        result = {"status": "reconciled", "capture_id": capture_id,
                  "run_id": run_id, "accepted": len(traces),
                  "rejected": len(candidates) - len(traces),
                  "trace_refs": [{"trace_id": trace["id"], "revision": trace["revision"]}
                                 for trace in traces],
                  "vault_status": "awaiting_worker_export"}
        lib.db.execute("INSERT INTO gateway_review_finalizations VALUES(?,?,?,?)",
                       (owner, source_key, fingerprint, json.dumps(result, ensure_ascii=False)))
    return result


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
            raise LibrarianError("VALIDATION_FAILED", "review request must be an object")
        if not (args.root / "librarian.sqlite").is_file():
            raise LibrarianError("OBJECT_STORE_UNAVAILABLE", "Librarian store unavailable")
        with Library(args.root) as lib:
            result = finalize_review(lib, message)
    except (json.JSONDecodeError, LibrarianError) as error:
        code = error.code if isinstance(error, LibrarianError) else "VALIDATION_FAILED"
        print(json.dumps({"error": {"code": code}}))
        return 2
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
