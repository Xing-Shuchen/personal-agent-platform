"""Apply an explicit authenticated review of every candidate in one scan run."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from .gateway_review import pending_extractions
from .pipeline import reconcile_extraction
from .store import Library, LibrarianError

MAX_INPUT_BYTES = 8192


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
