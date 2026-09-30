"""Apply an explicit trusted-owner request to discard recent unprocessed photos."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from .gateway_errors import write_error
from .store import Library, LibrarianError


def discard_recent(lib: Library, message: dict) -> dict:
    owner = message.get("owner_id")
    source = message.get("source")
    count = message.get("count")
    before = message.get("before")
    if (not isinstance(owner, str) or not owner or not isinstance(source, dict)
            or not isinstance(count, int) or isinstance(count, bool) or not 1 <= count <= 100
            or not isinstance(before, str)):
        raise LibrarianError("VALIDATION_FAILED", "trusted owner, source, count and cutoff required")
    for key in ("transport", "account_id", "conversation_id", "source_event_id"):
        if not isinstance(source.get(key), str) or not source[key]:
            raise LibrarianError("VALIDATION_FAILED", "complete source identity required")
    try:
        cutoff = datetime.fromisoformat(before.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError as error:
        raise LibrarianError("VALIDATION_FAILED", "invalid cutoff") from error
    scope = (source["transport"], source["account_id"], source["conversation_id"])
    with lib.transaction():
        lib.db.execute("CREATE TABLE IF NOT EXISTS gateway_discard_receipts ("
                       "owner_id TEXT NOT NULL, source_event_id TEXT NOT NULL, "
                       "receipt TEXT NOT NULL, PRIMARY KEY(owner_id,source_event_id))")
        prior = lib.db.execute("SELECT receipt FROM gateway_discard_receipts WHERE owner_id=? "
                               "AND source_event_id=?", (owner, source["source_event_id"])).fetchone()
        if prior:
            return json.loads(prior["receipt"])
        batches = []
        for row in lib.db.execute("SELECT body FROM records WHERE owner_id=? AND model='CaptureBatch' "
                                  "AND current=1", (owner,)):
            batch = json.loads(row["body"])
            origin = batch["origin"]
            if (tuple(origin.get(key) for key in ("transport", "account_id", "conversation_id"))
                    != scope or datetime.fromisoformat(batch["received_at"]).astimezone(timezone.utc)
                    >= cutoff):
                continue
            batches.append(batch)
        batches.sort(key=lambda item: (item["received_at"], item["id"]), reverse=True)
        selected = batches[:count]
        capture_ids = [capture_id for batch in selected for capture_id in batch["capture_ids"]]
        if len(capture_ids) != count or any(batch["status"] != "received" for batch in selected):
            raise LibrarianError("CONTEXT_CONFLICT", "requested unprocessed photo count does not match")
        captures = [lib.get(owner, "PageCapture", capture_id) for capture_id in capture_ids]
        for capture in captures:
            capture_id = capture["id"]
            if lib.db.execute("SELECT 1 FROM extractor_attempts WHERE owner_id=? AND capture_id=?",
                              (owner, capture_id)).fetchone():
                raise LibrarianError("CONTEXT_CONFLICT", "a photo has entered extraction")
            if lib.db.execute("SELECT 1 FROM records WHERE owner_id=? AND model='ExtractionRun' "
                              "AND body LIKE ?", (owner, f'%{capture_id}%')).fetchone():
                raise LibrarianError("CONTEXT_CONFLICT", "a photo has extraction results")
            if lib.db.execute("SELECT 1 FROM records WHERE owner_id=? AND model='ReadingTrace' "
                              "AND body LIKE ?", (owner, f'%{capture_id}%')).fetchone():
                raise LibrarianError("CONTEXT_CONFLICT", "a photo has stored traces")
        batch_ids = [batch["id"] for batch in selected]
        for batch in selected:
            lib._put({**batch, "status": "discarded", "revision": batch["revision"] + 1,
                      "supersedes_revision": batch["revision"]})
        receipt = {"status": "discarded", "count": count, "capture_ids": capture_ids,
                   "batch_ids": batch_ids, "source_event_id": source["source_event_id"]}
        lib.db.execute("INSERT INTO gateway_discard_receipts VALUES(?,?,?)",
                       (owner, source["source_event_id"], json.dumps(receipt)))
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    try:
        message = json.load(sys.stdin)
        with Library(args.root) as lib:
            receipt = discard_recent(lib, message)
    except Exception as error:
        return write_error(error, "gateway.discard_captures")
    print(json.dumps(receipt))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
