#!/usr/bin/env python3
"""Unified CLI for Cadre Tracker (Section 9.2)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

try:
    from .db import (
        CadreError,
        connect,
        migrate,
        query_overlap,
        query_shockwave,
        query_succession,
        search_cadres,
        seed_org_skeleton,
    )
    from .gate_precheck import run_precheck
    from .obsidian import project_person_note, write_shockwave_brief
    from .resolver import decide_review, ingest_bundle, list_review_queue
except ImportError:
    from db import (  # type: ignore[no-redef]
        CadreError,
        connect,
        migrate,
        query_overlap,
        query_shockwave,
        query_succession,
        search_cadres,
        seed_org_skeleton,
    )
    from gate_precheck import run_precheck  # type: ignore[no-redef]
    from obsidian import project_person_note, write_shockwave_brief  # type: ignore[no-redef]
    from resolver import decide_review, ingest_bundle, list_review_queue  # type: ignore[no-redef]


def _emit_paplog(command: str, attributes: dict[str, Any]) -> None:
    """Best-effort paplog v2 telemetry emission; never fails the CLI command."""
    try:
        from paplog import observe

        observe.event(
            f"cadre_tracker.{command}",
            agent={"id": "cadre-tracker"},
            attributes=attributes,
        )
    except Exception:
        pass


def _print_json(data: Any, *, pretty: bool) -> None:
    if pretty:
        print(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=False))
    else:
        print(json.dumps(data, ensure_ascii=False))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cadre-tracker-cli", description="Cadre Tracker deterministic runtime CLI")
    parser.add_argument("--db", type=Path, default=None, help="override SQLite database path")
    parser.add_argument("--pretty", action="store_true", help="pretty-print JSON output")

    sub = parser.add_subparsers(dest="command", required=True)

    p_mig = sub.add_parser("migrate", help="apply SQLite migrations")
    p_mig.add_argument("--seed", action="store_true", help="also run Batch 0 org skeleton & reform lineage seeding")
    p_mig.add_argument("--pretty", action="store_true", default=argparse.SUPPRESS)

    p_seed = sub.add_parser("seed-orgs", help="seed Batch 0 31-province skeleton and 2018/2023 reform lineage")
    p_seed.add_argument("--pretty", action="store_true", default=argparse.SUPPRESS)

    p_poll = sub.add_parser("poll", help="run deterministic source collectors")
    p_poll.add_argument("--source", default="all", choices=("ccdi", "appoint", "wiki", "media", "dom", "all"))
    p_poll.add_argument("--pretty", action="store_true", default=argparse.SUPPRESS)

    p_fp = sub.add_parser("fetch-pending", help="list pending raw_sources awaiting LLM extraction")
    p_fp.add_argument("--limit", type=int, default=20)
    p_fp.add_argument("--pretty", action="store_true", default=argparse.SUPPRESS)

    p_ing = sub.add_parser("ingest-bundle", help="idempotently ingest a cadre-bundle v1.0 JSON file")
    p_ing.add_argument("--file", required=True, help="path to bundle JSON (or '-' for stdin)")
    p_ing.add_argument("--pretty", action="store_true", default=argparse.SUPPRESS)

    p_ov = sub.add_parser("overlap", help="query 4-cluster temporal/org/alumni/clue overlap between two cadres")
    p_ov.add_argument("--a", required=True, help="person A name or person_id")
    p_ov.add_argument("--b", required=True, help="person B name or person_id")
    p_ov.add_argument("--pretty", action="store_true", default=argparse.SUPPRESS)

    p_sw = sub.add_parser("shockwave", help="compute Closeness Index shockwave ranking for a cadre")
    p_sw.add_argument("--person", required=True, help="subject name or person_id")
    p_sw.add_argument("--top", type=int, default=20, help="top K per category")
    p_sw.add_argument("--reference-year", type=int, default=2026)
    p_sw.add_argument("--pretty", action="store_true", default=argparse.SUPPRESS)

    p_suc = sub.add_parser("succession", help="query chronological succession chain across org_lineage")
    p_suc.add_argument("--org", required=True, help="org canonical_name, short_name, alias, or org_id")
    p_suc.add_argument("--role", required=True, help="standardized role_title")
    p_suc.add_argument("--pretty", action="store_true", default=argparse.SUPPRESS)

    p_srch = sub.add_parser("search", help="full-text search cadres via FTS5")
    p_srch.add_argument("--query", required=True, help="space-separated search terms")
    p_srch.add_argument("--status", default=None)
    p_srch.add_argument("--rank", default=None)
    p_srch.add_argument("--limit", type=int, default=20)
    p_srch.add_argument("--pretty", action="store_true", default=argparse.SUPPRESS)

    p_rl = sub.add_parser("review-list", help="list claims awaiting manual disambiguation")
    p_rl.add_argument("--pretty", action="store_true", default=argparse.SUPPRESS)

    p_rd = sub.add_parser("review-decide", help="resolve a disambiguation_conflict claim")
    p_rd.add_argument("--claim-id", required=True)
    p_rd.add_argument("--action", required=True, choices=("bind", "create", "reject"))
    p_rd.add_argument("--person-id", default=None)
    p_rd.add_argument("--pretty", action="store_true", default=argparse.SUPPRESS)

    p_obs = sub.add_parser("project-obsidian", help="project a cadre profile (and optional brief) to Obsidian")
    p_obs.add_argument("--person", required=True)
    p_obs.add_argument("--vault", type=Path, default=None)
    p_obs.add_argument("--brief-title", default=None)
    p_obs.add_argument("--pretty", action="store_true", default=argparse.SUPPRESS)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    pretty = bool(getattr(args, "pretty", False))

    conn = connect(args.db)
    try:
        cmd = args.command
        if cmd == "migrate":
            res = migrate(conn)
            if args.seed:
                res["seed"] = seed_org_skeleton(conn)
            _emit_paplog("migrate", res)
            _print_json(res, pretty=pretty)
            return 0

        # Ensure schema exists for all other commands
        migrate(conn)

        if cmd == "seed-orgs":
            res = seed_org_skeleton(conn)
            _emit_paplog("seed_orgs", res)
            _print_json(res, pretty=pretty)
        elif cmd == "poll":
            res = run_precheck(conn, sources=[args.source])
            _emit_paplog("poll", {"source": args.source, "gate_open": res.get("gate_open")})
            _print_json(res, pretty=pretty)
        elif cmd == "fetch-pending":
            rows = conn.execute(
                """SELECT source_id, source_type, source_name, credibility_tier, url, title, published_at, raw_content
                   FROM raw_sources WHERE ingest_status = 'pending'
                   ORDER BY credibility_tier ASC, fetched_at ASC LIMIT ?""",
                (args.limit,),
            ).fetchall()
            res = {"pending": [dict(r) for r in rows], "count": len(rows)}
            _print_json(res, pretty=pretty)
        elif cmd == "ingest-bundle":
            if args.file == "-":
                bundle = json.load(sys.stdin)
            else:
                bundle = json.loads(Path(args.file).read_text(encoding="utf-8"))
            res = ingest_bundle(conn, bundle)
            _emit_paplog(
                "ingest_bundle",
                {
                    "source_id": res["source_id"],
                    "persons_inserted": res["persons_inserted"],
                    "tenures_inserted": res["tenures_inserted"],
                    "needs_review_count": res["needs_review_count"],
                },
            )
            _print_json(res, pretty=pretty)
        elif cmd == "overlap":
            res = query_overlap(conn, args.a, args.b)
            _emit_paplog("overlap", {"a": args.a, "b": args.b, "work_overlaps": len(res["work_overlaps"])})
            _print_json(res, pretty=pretty)
        elif cmd == "shockwave":
            res = query_shockwave(conn, args.person, top_k=args.top, reference_year=args.reference_year)
            _emit_paplog(
                "shockwave",
                {
                    "person": args.person,
                    "fallen_count": len(res["already_fallen_associates"]),
                    "active_count": len(res["active_watch_list"]),
                },
            )
            _print_json(res, pretty=pretty)
        elif cmd == "succession":
            res = query_succession(conn, args.org, args.role)
            _emit_paplog("succession", {"org": args.org, "role": args.role, "count": len(res["chain"])})
            _print_json(res, pretty=pretty)
        elif cmd == "search":
            rows = search_cadres(conn, args.query, status=args.status, rank=args.rank, limit=args.limit)
            res = {"query": args.query, "results": rows, "count": len(rows)}
            _print_json(res, pretty=pretty)
        elif cmd == "review-list":
            items = list_review_queue(conn)
            res = {"items": items, "count": len(items)}
            _print_json(res, pretty=pretty)
        elif cmd == "review-decide":
            res = decide_review(conn, args.claim_id, args.action, person_id=args.person_id)
            _emit_paplog("review_decide", res)
            _print_json(res, pretty=pretty)
        elif cmd == "project-obsidian":
            res = project_person_note(conn, args.person, vault_dir=args.vault)
            if args.brief_title:
                res["brief"] = write_shockwave_brief(
                    conn, args.person, args.brief_title, vault_dir=args.vault
                )
            _emit_paplog("project_obsidian", {"person": args.person, "skipped": res.get("skipped")})
            _print_json(res, pretty=pretty)
        return 0
    except CadreError as exc:
        _print_json({"error": str(exc)}, pretty=pretty)
        return 1
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
