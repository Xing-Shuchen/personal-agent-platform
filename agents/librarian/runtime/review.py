"""Owner-scoped exception queues for capture resolution and important content."""
from __future__ import annotations

import json
from typing import Any

from .store import Library, LibrarianError


def review_queues(lib: Library, owner_id: str, *, limit: int = 100) -> dict[str, list[dict[str, Any]]]:
    """Return current exceptions, grouped by capture batch and by trace.

    Accepted but unprocessed captures are not review exceptions. A caller can
    use the returned IDs to load owner-scoped records and original evidence.
    """
    if not owner_id or not 1 <= limit <= 1000:
        raise LibrarianError("VALIDATION_FAILED", "owner and limit required")
    rows = lib.db.execute(
        "SELECT model,body FROM records WHERE owner_id=? AND current=1 "
        "AND model IN ('PageCapture','CaptureResolution','ProcessingRun','ReadingTrace') "
        "ORDER BY rowid", (owner_id,)).fetchall()
    captures: dict[str, dict[str, Any]] = {}
    resolutions: dict[str, dict[str, Any]] = {}
    runs: dict[str, dict[str, Any]] = {}
    traces: list[dict[str, Any]] = []
    for row in rows:
        record = json.loads(row["body"])
        match row["model"]:
            case "PageCapture":
                captures[record["id"]] = record
            case "CaptureResolution":
                resolutions[record["capture_id"]] = record
            case "ProcessingRun":
                if record["outcome"] in {"success", "partial"} or "CONTEXT_CONFLICT" in record["issues"]:
                    runs[record["capture_id"]] = record
            case "ReadingTrace":
                traces.append(record)

    by_batch: dict[str, dict[str, Any]] = {}
    for capture_id, run in runs.items():
        capture = captures.get(capture_id)
        if capture is None:
            continue
        resolution = resolutions.get(capture_id)
        missing = ([field for field in ("session", "work", "edition", "book_instance")
                    if resolution[field]["status"] != "resolved"] if resolution else
                   ["session", "work", "edition", "book_instance"])
        conflict = "CONTEXT_CONFLICT" in run["issues"]
        if not missing and not conflict:
            continue
        batch = by_batch.setdefault(capture["batch_id"],
                                    {"batch_id": capture["batch_id"], "captures": []})
        batch["captures"].append({
            "capture_id": capture_id,
            "resolution_id": resolution["id"] if resolution else None,
            "resolution_revision": resolution["revision"] if resolution else None,
            "missing": missing,
            "issues": ["CONTEXT_CONFLICT"] if conflict else ["NEEDS_BOOK_RESOLUTION"],
        })
    content = [
        {"trace_id": trace["id"], "revision": trace["revision"],
         "capture_id": trace["source"]["capture_id"],
         "reason": trace["review"]["reason"],
         "evidence": trace["provenance"]}
        for trace in traces
        if trace["medium"] == "physical" and trace["status"] == "active"
        and trace["review"]["required"] and trace["review"]["state"] == "pending"
    ]
    return {"resolution": list(by_batch.values())[:limit], "content": content[:limit]}
