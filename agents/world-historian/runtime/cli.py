#!/usr/bin/env python3
"""Inspectable CLI for World Historian's deterministic SQLite runtime.

Domain writes are validated bundles committed atomically. Threads that a
committed bundle created or modified are exported to the Obsidian vault
(one file per thread); bundles that touch no thread trigger no file writes.
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from db import (
    ChronicleError,
    all_thread_ids,
    connect,
    default_db_path,
    initialize,
    migrate,
    search,
    stats,
    store_bundle,
    thread_detail,
    thread_snapshot,
)
import feeds as feeds_mod
import obsidian


def _print(value: object) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))


def _read_json(path: str) -> object:
    if path == "-":
        return json.load(sys.stdin)
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _index_path(db_path: Path) -> Path:
    return db_path.parent / "obsidian-index.json"


def _sync(conn: sqlite3.Connection, db_path: Path,
          thread_ids: list[str], *, db_overridden: bool = False) -> dict[str, Any]:
    """Export the given threads to the vault. Best-effort, never raises.

    When ``--db`` points somewhere other than the default chronicle and no
    explicit vault override is configured, syncing is skipped: a non-default
    database must never silently project into the real vault.
    """
    vault = obsidian.vault_dir()
    if vault is None or not thread_ids:
        return {"written": [], "removed": [], "errors": [], "skipped": True}
    if db_overridden and os.environ.get("WORLD_HISTORIAN_VAULT_DIR") is None:
        return {"written": [], "removed": [], "errors": [], "skipped": True,
                "reason": "non-default --db without WORLD_HISTORIAN_VAULT_DIR"}
    snapshots = [thread_snapshot(conn, tid) for tid in thread_ids]
    snapshots = [snapshot for snapshot in snapshots if snapshot is not None]
    outcome: dict[str, Any] = obsidian.sync_threads(
        snapshots, vault, _index_path(db_path))
    outcome["skipped"] = False
    return outcome


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="world-historian-runtime")
    parser.add_argument("--db", type=Path, default=None, help="override chronicle.sqlite path")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init", help="create runtime directories and apply migrations")
    sub.add_parser("stats", help="show table counts")
    sub.add_parser("roster", help="print the deterministic follow-update thread roster")
    sub.add_parser("active-thread-titles",
                   help="print active thread titles, newest updated first")

    p_daily_stats = sub.add_parser(
        "daily-stats", help="print World Historian run and Chronicle activity for a local day")
    p_daily_stats.add_argument(
        "--day", help="local calendar day (YYYY-MM-DD; defaults to yesterday)")
    p_daily_stats.add_argument(
        "--runs", type=Path, default=Path(__file__).resolve().parents[3] / "var" / "state" / "runs.jsonl",
        help="override pap runs.jsonl path")

    p_link_exists = sub.add_parser(
        "personal-link-exists", help="print 1 when a world/personal link already exists")
    p_link_exists.add_argument("world_event_id")
    p_link_exists.add_argument("personal_event_id")

    p_lifecycle = sub.add_parser(
        "lifecycle-candidates", help="list stale active threads to demote or close")
    p_lifecycle.add_argument("--high-to-normal-days", type=int, default=3)
    p_lifecycle.add_argument("--normal-to-low-days", type=int, default=7)
    p_lifecycle.add_argument("--low-to-background-days", type=int, default=14)
    p_lifecycle.add_argument("--close-after-days", type=int, default=60)
    p_lifecycle.add_argument("--now", help="ISO-8601 local time (defaults to now)")

    p_store = sub.add_parser("store-bundle", help="atomically validate and persist a JSON bundle")
    p_store.add_argument("--json", required=True, help="JSON file path, or - for stdin")
    p_store.add_argument("--no-sync", action="store_true",
                         help="skip the Obsidian export even if threads were touched")

    p_sync = sub.add_parser("sync", help="rebuild Obsidian thread files from the database")
    p_sync.add_argument("--thread", action="append", default=[],
                        help="limit to these thread ids (repeatable; default all)")

    p_feeds = sub.add_parser("feeds", help="deterministic RSS/Atom ingestion")
    feeds_sub = p_feeds.add_subparsers(dest="feeds_command", required=True)
    p_feeds_update = feeds_sub.add_parser("update",
                                          help="fetch configured RSS sources into sources")
    p_feeds_update.add_argument("--max-entries", type=int, default=30,
                                help="max entries ingested per feed (default 30)")
    p_feeds_recent = feeds_sub.add_parser("recent",
                                          help="list recently ingested RSS entries")
    p_feeds_recent.add_argument("--hours", type=int, default=24)
    p_feeds_recent.add_argument("--limit", type=int, default=50)

    p_search = sub.add_parser("search", help="search thread, event, and entity labels")
    p_search.add_argument("query")
    p_search.add_argument("--limit", type=int, default=20)

    p_thread = sub.add_parser("thread", help="show a thread with questions and events")
    p_thread.add_argument("thread_id")
    return parser


def _readonly_connection(db_path: Path) -> sqlite3.Connection:
    """Open an existing Chronicle database without any write-side effects."""
    return sqlite3.connect(f"{db_path.resolve().as_uri()}?mode=ro", uri=True)


def _daily_stats_day(value: str | None) -> str:
    if value is None:
        return (datetime.now().astimezone().date() - timedelta(days=1)).isoformat()
    # ``fromisoformat`` validates the input while preserving its locale-neutral form.
    return date.fromisoformat(value).isoformat()


def _print_daily_stats(conn: sqlite3.Connection, day: str, run_log: Path) -> None:
    """Print the two former daily-ledger query results in a stable text format."""
    completed: dict[str, dict[str, Any]] = {}
    deliveries: dict[str, str] = {}
    with run_log.open(encoding="utf-8") as handle:
        for line in handle:
            record = json.loads(line)
            if (record.get("event") == "run.completed"
                    and str(record.get("completed_at", "")).startswith(day)):
                completed[str(record["run_id"])] = record
            elif record.get("event") == "run.delivery":
                deliveries[str(record["run_id"])] = str(record.get("delivery", "not-attempted"))

    by_job: dict[str, Counter[str]] = defaultdict(Counter)
    for run_id, record in completed.items():
        if record.get("agent_id") != "world-historian":
            continue
        job = str(record.get("trigger", {}).get("job_id", "unknown"))
        by_job[job][str(record.get("status", "unknown"))] += 1
        by_job[job][f"delivery:{deliveries.get(run_id, 'not-attempted')}"] += 1

    print(f"day {day}")
    print("runs")
    for job in sorted(by_job):
        counts = by_job[job]
        fields = " ".join(f"{key}={counts[key]}" for key in sorted(counts))
        print(f"job {job} {fields}")
    print("chronicle")
    for table in ("threads", "events", "claims"):
        count = conn.execute(
            f"SELECT COUNT(*) FROM {table} WHERE substr(created_at, 1, 10) = ?", (day,)
        ).fetchone()[0]
        print(f"{table} {count}")
    for row in conn.execute(
        "SELECT id, title, priority, status FROM threads "
        "WHERE substr(updated_at, 1, 10) = ? ORDER BY updated_at, id", (day,)
    ):
        print("updated-thread", *row)


def _lifecycle_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    text = value.strip()
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            parsed = datetime.strptime(text, fmt)
            return parsed.replace(tzinfo=None)
        except ValueError:
            continue
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return parsed.replace(tzinfo=None)
    except ValueError:
        pass
    return None


def _print_lifecycle_candidates(conn: sqlite3.Connection, args: argparse.Namespace) -> None:
    thresholds = {
        "high": (args.high_to_normal_days, "normal"),
        "normal": (args.normal_to_low_days, "low"),
        "low": (args.low_to_background_days, "background"),
    }
    if any(days < 0 for days, _ in thresholds.values()) or args.close_after_days < 0:
        raise ValueError("lifecycle thresholds must be non-negative")
    if args.now:
        now = _lifecycle_timestamp(args.now)
        if now is None:
            raise ValueError("--now must be ISO-8601")
    else:
        now = datetime.now()
    close_cutoff = now - timedelta(days=args.close_after_days)
    rows = conn.execute(
        "SELECT t.id, t.title, t.priority, e.occurred_at, e.observed_at, e.reported_at "
        "FROM threads t LEFT JOIN thread_events te ON te.thread_id = t.id "
        "LEFT JOIN events e ON e.id = te.event_id "
        "WHERE t.status = 'active' ORDER BY t.id"
    )
    aggregate: dict[str, dict[str, Any]] = {}
    for thread_id, title, priority, occurred_at, observed_at, reported_at in rows:
        latest = max(
            (parsed for parsed in (_lifecycle_timestamp(occurred_at),
                                   _lifecycle_timestamp(observed_at),
                                   _lifecycle_timestamp(reported_at)) if parsed is not None),
            default=None,
        )
        current = aggregate.setdefault(
            thread_id, {"title": title, "priority": priority, "last": None})
        if latest is not None and (current["last"] is None or latest > current["last"]):
            current["last"] = latest
    for thread_id in sorted(aggregate):
        candidate = aggregate[thread_id]
        latest = candidate["last"]
        if latest is None or latest < close_cutoff:
            print(f"CLOSE\t{thread_id}\t{candidate['title']}")
        elif candidate["priority"] in thresholds:
            days, new_priority = thresholds[candidate["priority"]]
            if latest < now - timedelta(days=days):
                print(f"DEMOTE\t{thread_id}\t{candidate['title']}\t{new_priority}")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    db_path = Path(args.db) if args.db else default_db_path()
    try:
        if args.command == "init":
            path, applied = initialize(db_path)
            _print({"database": str(path), "migrations_applied": applied})
            return 0

        if args.command == "roster":
            # This deliberately bypasses ``connect``: that helper creates parent
            # directories and configures WAL, whereas the delivery roster must be
            # a strictly read-only projection of an existing Chronicle database.
            with _readonly_connection(db_path) as conn:
                rows = conn.execute(
                    "SELECT title, priority FROM threads "
                    "WHERE status = 'active' AND priority IN ('high', 'normal') "
                    "ORDER BY CASE priority WHEN 'high' THEN 0 ELSE 1 END, title"
                )
                for title, priority in rows:
                    emoji = "🟥" if priority == "high" else "🟦"
                    print(f"- {emoji} **{title}**（{priority}）")
            return 0

        if args.command == "active-thread-titles":
            with _readonly_connection(db_path) as conn:
                for (title,) in conn.execute(
                    "SELECT title FROM threads WHERE status = 'active' "
                    "ORDER BY updated_at DESC, id DESC"
                ):
                    print(title)
            return 0

        if args.command == "personal-link-exists":
            with _readonly_connection(db_path) as conn:
                exists = conn.execute(
                    "SELECT 1 FROM personal_links "
                    "WHERE world_event_id = ? AND personal_event_id = ? LIMIT 1",
                    (args.world_event_id, args.personal_event_id),
                ).fetchone()
                if exists is not None:
                    print("1")
            return 0

        if args.command == "daily-stats":
            with _readonly_connection(db_path) as conn:
                _print_daily_stats(conn, _daily_stats_day(args.day), args.runs)
            return 0

        if args.command == "lifecycle-candidates":
            with _readonly_connection(db_path) as conn:
                _print_lifecycle_candidates(conn, args)
            return 0

        with connect(db_path) as conn:
            migrate(conn)
            if args.command == "stats":
                _print(stats(conn))
            elif args.command == "store-bundle":
                bundle = _read_json(args.json)
                result = store_bundle(conn, bundle)  # type: ignore[arg-type]
                result["obsidian"] = (
                    {"skipped": True} if args.no_sync
                    else _sync(conn, db_path, result["touched_threads"],
                               db_overridden=args.db is not None)
                )
                _print(result)
            elif args.command == "sync":
                thread_ids = args.thread or all_thread_ids(conn)
                _print(_sync(conn, db_path, thread_ids,
                             db_overridden=args.db is not None))
            elif args.command == "feeds" and args.feeds_command == "update":
                _print(feeds_mod.ingest_all(conn, max_entries=args.max_entries))
            elif args.command == "feeds" and args.feeds_command == "recent":
                _print({
                    "hours": args.hours,
                    "entries": feeds_mod.recent_sources(conn, hours=args.hours,
                                                        limit=args.limit),
                })
            elif args.command == "search":
                _print(search(conn, args.query, args.limit))
            elif args.command == "thread":
                detail = thread_detail(conn, args.thread_id)
                if detail is None:
                    print(f"thread not found: {args.thread_id}", file=sys.stderr)
                    return 1
                _print(detail)
        return 0
    except (ChronicleError, json.JSONDecodeError, sqlite3.Error, OSError,
            ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
