#!/usr/bin/env python3
"""Prepare read-only evidence for the nightly updated-thread relation review."""
from __future__ import annotations

import argparse
from datetime import date, datetime, time, timedelta, timezone
import itertools
import json
from pathlib import Path
import sqlite3
from zoneinfo import ZoneInfo

import db


def updated_threads(conn: sqlite3.Connection, day: date) -> list[dict]:
    """Use ingestion/update clocks, not the dates on which old news happened."""
    start = datetime.combine(day, time.min, ZoneInfo("Asia/Shanghai"))
    end = start + timedelta(days=1)
    rows = conn.execute("""
        WITH changes(thread_id, changed_at, reason) AS (
          SELECT id, created_at, 'thread_created' FROM threads
          UNION ALL
          SELECT id, updated_at, 'thread_metadata' FROM threads
            WHERE last_checked_at IS NULL OR julianday(updated_at) != julianday(last_checked_at)
          UNION ALL
          SELECT thread_id, created_at, 'event_membership' FROM thread_events
          UNION ALL
          SELECT te.thread_id, e.updated_at, 'event' FROM thread_events te JOIN events e ON e.id=te.event_id
          UNION ALL
          SELECT te.thread_id, c.updated_at, 'claim' FROM thread_events te JOIN claims c ON c.event_id=te.event_id
          UNION ALL
          SELECT te.thread_id, q.updated_at, 'quote' FROM thread_events te JOIN quotes q ON q.event_id=te.event_id
          UNION ALL
          SELECT thread_id, updated_at, 'current_state' FROM thread_current_states
          UNION ALL
          SELECT thread_id, updated_at, 'question' FROM open_questions
          UNION ALL
          SELECT te.thread_id, i.updated_at, 'interpretation' FROM interpretations i
            JOIN thread_events te ON te.event_id=i.earlier_event_id OR te.event_id=i.later_event_id
        )
        SELECT DISTINCT t.id, t.title, c.reason FROM changes c JOIN threads t ON t.id=c.thread_id
          WHERE julianday(c.changed_at) >= julianday(?) AND julianday(c.changed_at) < julianday(?)
          ORDER BY t.id, c.reason
        """, (start.astimezone(timezone.utc).isoformat(), end.astimezone(timezone.utc).isoformat()))
    selected = {}
    for row in rows:
        item = selected.setdefault(row["id"], {"id": row["id"], "title": row["title"], "update_reasons": []})
        item["update_reasons"].append(row["reason"])
    return list(selected.values())


def prepare(conn: sqlite3.Connection, day: date, output: Path) -> dict:
    selected = updated_threads(conn, day)
    output.mkdir(parents=True, exist_ok=True)
    snapshots = {item["id"]: db.thread_snapshot(conn, item["id"]) for item in selected}
    relations = [dict(row) for row in conn.execute("SELECT * FROM relations")]
    simple = [dict(row) for row in conn.execute("SELECT * FROM thread_relations")]
    for index, item in enumerate(selected):
        snapshot = snapshots[item["id"]]
        source_ids = {c["source_id"] for e in snapshot["events"] for c in e["claims"]}
        source_ids.update(q["source_id"] for e in snapshot["events"] for q in e["quotes"] if q.get("source_id"))
        snapshot["sources"] = [dict(row) for sid in sorted(source_ids)
                               for row in conn.execute("SELECT * FROM sources WHERE id=?", (sid,))]
        # Numeric filenames avoid treating an arbitrary database ID as a path.
        item["evidence_file"] = f"thread-{index:03d}.json"
        (output / item["evidence_file"]).write_text(json.dumps(snapshot, ensure_ascii=False, indent=2))
    event_ids = {tid: {e["id"] for e in s["events"]} for tid, s in snapshots.items()}
    pairs = []
    for a, b in itertools.combinations(snapshots, 2):
        pairs.append({
            "a": a, "b": b,
            "shared_events": sorted(event_ids[a] & event_ids[b]),
            "existing_thread_relations": [r for r in relations if r["src_type"] == r["dst_type"] == "thread"
                                          and {r["src_id"], r["dst_id"]} == {a, b}],
            "existing_simple_links": [r for r in simple if {r["thread_id_a"], r["thread_id_b"]} == {a, b}],
            "cross_event_relations": [r for r in relations if r["src_type"] == r["dst_type"] == "event"
                                      and ((r["src_id"] in event_ids[a] and r["dst_id"] in event_ids[b])
                                           or (r["src_id"] in event_ids[b] and r["dst_id"] in event_ids[a]))],
        })
    manifest = {"day": day.isoformat(), "timezone": "Asia/Shanghai",
                "prepared_at": datetime.now(timezone.utc).isoformat(),
                "threads": selected, "thread_count": len(selected), "pair_count": len(pairs),
                "pairs_file": "pairs.json"}
    (output / "pairs.json").write_text(json.dumps(pairs, ensure_ascii=False, indent=2))
    (output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=db.default_db_path())
    parser.add_argument("--day", type=date.fromisoformat,
                        default=datetime.now(ZoneInfo("Asia/Shanghai")).date())
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    conn = sqlite3.connect(f"{args.db.resolve().as_uri()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("BEGIN")  # One consistent snapshot across all evidence files.
        result = prepare(conn, args.day, args.output)
    finally:
        conn.close()
    print(json.dumps({"manifest": str(args.output / "manifest.json"),
                      "day": result["day"], "thread_count": result["thread_count"],
                      "pair_count": result["pair_count"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
