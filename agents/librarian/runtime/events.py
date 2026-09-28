"""Stable-ID outbox delivery and transactional local consumer deduplication."""
from __future__ import annotations

import json
from typing import Any, Callable

from .pipeline import _index_trace
from .store import Library, LibrarianError, _now, validate


def publish_pending(lib: Library, owner_id: str,
                    publisher: Callable[[dict[str, Any]], None], *, limit: int = 100) -> int:
    """Publish at least once; a crash retries the exact same event_id."""
    if not owner_id or not 1 <= limit <= 1000:
        raise LibrarianError("VALIDATION_FAILED", "owner and bounded limit required")
    rows = lib.db.execute("SELECT event_id,body FROM outbox WHERE owner_id=? AND delivered_at IS NULL "
                          "ORDER BY rowid LIMIT ?", (owner_id, limit)).fetchall()
    count = 0
    for row in rows:
        event = json.loads(row["body"])
        validate("Event", event)
        publisher(event)
        with lib.transaction():
            lib.db.execute("UPDATE outbox SET delivered_at=? WHERE event_id=? AND owner_id=? "
                           "AND delivered_at IS NULL", (_now(), row["event_id"], owner_id))
        count += 1
    return count


def consume_event(lib: Library, consumer_id: str, event: dict[str, Any], *,
                  trusted_owner_id: str,
                  handler: Callable[[dict[str, Any]], None]) -> bool:
    """Deduplicate one event with a local transactional projection handler."""
    validate("Event", event)
    if event["owner_id"] != trusted_owner_id or not consumer_id:
        raise LibrarianError("UNAUTHORIZED", "consumer owner differs from event owner")
    with lib.transaction():
        exists = lib.db.execute("SELECT 1 FROM consumer_events WHERE consumer_id=? AND event_id=?",
                                (consumer_id, event["event_id"])).fetchone()
        if exists:
            return False
        handler(event)
        lib.db.execute("INSERT INTO consumer_events VALUES(?,?,?,?)",
                       (consumer_id, event["event_id"], trusted_owner_id, _now()))
    return True


def project_trace_event(lib: Library, event: dict[str, Any]) -> None:
    """Apply a trace event without letting a late old revision roll back search."""
    if event["event"] not in {"reading.trace.created", "reading.trace.corrected"}:
        return
    owner_id = event["owner_id"]
    trace_id = event["payload"]["trace_id"]
    trace = lib.get(owner_id, "ReadingTrace", trace_id)
    if trace["revision"] < event["aggregate"]["revision"]:
        raise LibrarianError("REVISION_CONFLICT", "event references a future trace revision")
    indexed = lib.db.execute("SELECT revision FROM trace_index WHERE owner_id=? AND trace_id=?",
                             (owner_id, trace_id)).fetchone()
    if indexed and indexed["revision"] > trace["revision"]:
        return
    if trace["status"] == "active":
        _index_trace(lib, trace)
    else:
        lib.db.execute("DELETE FROM trace_index WHERE owner_id=? AND trace_id=?",
                       (owner_id, trace_id))
