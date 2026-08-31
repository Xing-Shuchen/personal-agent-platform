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


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    db_path = Path(args.db) if args.db else default_db_path()
    try:
        if args.command == "init":
            path, applied = initialize(db_path)
            _print({"database": str(path), "migrations_applied": applied})
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
