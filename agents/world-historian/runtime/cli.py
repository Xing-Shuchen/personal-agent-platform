#!/usr/bin/env python3
"""Inspectable CLI for World Historian's deterministic SQLite runtime."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

from db import ChronicleError, connect, initialize, migrate, search, stats, store_bundle, thread_detail


def _print(value: object) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))


def _read_json(path: str) -> object:
    if path == "-":
        return json.load(sys.stdin)
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="world-historian-runtime")
    parser.add_argument("--db", type=Path, default=None, help="override chronicle.sqlite path")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init", help="create runtime directories and apply migrations")
    sub.add_parser("stats", help="show table counts")

    p_store = sub.add_parser("store-bundle", help="atomically validate and persist a JSON bundle")
    p_store.add_argument("--json", required=True, help="JSON file path, or - for stdin")

    p_search = sub.add_parser("search", help="search thread, event, and entity labels")
    p_search.add_argument("query")
    p_search.add_argument("--limit", type=int, default=20)

    p_thread = sub.add_parser("thread", help="show a thread with questions and events")
    p_thread.add_argument("thread_id")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "init":
            path, applied = initialize(args.db)
            _print({"database": str(path), "migrations_applied": applied})
            return 0

        with connect(args.db) as conn:
            migrate(conn)
            if args.command == "stats":
                _print(stats(conn))
            elif args.command == "store-bundle":
                bundle = _read_json(args.json)
                _print(store_bundle(conn, bundle))
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
