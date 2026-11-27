#!/usr/bin/env python3
"""Lightweight deterministic gate precheck for PAP scheduler (zero LLM tokens, Section 5.1)."""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Any

import yaml

try:
    from .collectors import (
        AppointCollector,
        CCDICollector,
        DeepMediaCollector,
        Fetcher,
        GovDomSentinel,
        WikiCollector,
        default_http_fetch,
    )
    from .db import AGENT_DIR, connect, migrate
except ImportError:
    from collectors import (  # type: ignore[no-redef]
        AppointCollector,
        CCDICollector,
        DeepMediaCollector,
        Fetcher,
        GovDomSentinel,
        WikiCollector,
        default_http_fetch,
    )
    from db import AGENT_DIR, connect, migrate  # type: ignore[no-redef]

URGENT_SOURCE_TYPES = {"ccdi_investigation", "ccdi_sanction", "gov_dom_diff"}


def load_agent_config(config_path: Path | None = None) -> dict[str, Any]:
    path = config_path or (AGENT_DIR / "profile" / "config.yaml")
    if not path.is_file():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def run_precheck(
    conn: sqlite3.Connection,
    *,
    sources: list[str] | None = None,
    config: dict[str, Any] | None = None,
    fetcher: Fetcher = default_http_fetch,
    captured_date: str | None = None,
    include_existing_pending: bool = False,
) -> dict[str, Any]:
    """Run deterministic collectors and return PAP gate precheck JSON contract."""
    cfg = config if config is not None else load_agent_config()
    src_cfg = cfg.get("sources") or {}
    selected = set(sources or ["ccdi", "appoint", "dom", "media"])
    if "all" in selected:
        selected = {"ccdi", "appoint", "wiki", "media", "dom"}

    newly_captured: list[dict[str, Any]] = []
    errors: list[str] = []

    if "ccdi" in selected and src_cfg.get("ccdi", {}).get("enabled", True):
        endpoints = src_cfg.get("ccdi", {}).get("endpoints") or []
        if endpoints:
            try:
                newly_captured.extend(CCDICollector(fetcher).poll(conn, endpoints))
            except Exception as exc:
                errors.append(f"ccdi: {type(exc).__name__}: {exc}")

    if "appoint" in selected and src_cfg.get("appoint", {}).get("enabled", True):
        endpoints = src_cfg.get("appoint", {}).get("endpoints") or []
        if endpoints:
            try:
                newly_captured.extend(AppointCollector(fetcher).poll(conn, endpoints))
            except Exception as exc:
                errors.append(f"appoint: {type(exc).__name__}: {exc}")

    if "dom" in selected:
        try:
            newly_captured.extend(GovDomSentinel(fetcher).poll(conn, captured_date=captured_date))
        except Exception as exc:
            errors.append(f"dom: {type(exc).__name__}: {exc}")

    if "media" in selected and src_cfg.get("deep_media", {}).get("enabled", True):
        feeds = src_cfg.get("deep_media", {}).get("feeds") or []
        kws = tuple(src_cfg.get("deep_media", {}).get("keywords") or ())
        if feeds:
            try:
                newly_captured.extend(
                    DeepMediaCollector(fetcher).poll(conn, feeds, keywords=kws or None)  # type: ignore[arg-type]
                    if kws
                    else DeepMediaCollector(fetcher).poll(conn, feeds)
                )
            except Exception as exc:
                errors.append(f"media: {type(exc).__name__}: {exc}")

    if "wiki" in selected and src_cfg.get("wiki", {}).get("enabled", True):
        api_url = src_cfg.get("wiki", {}).get("mediawiki_api")
        if api_url:
            try:
                newly_captured.extend(WikiCollector(fetcher).poll_recent_changes(conn, api_url))
            except Exception as exc:
                errors.append(f"wiki: {type(exc).__name__}: {exc}")

    pending_ids = [item["source_id"] for item in newly_captured]
    trigger_reasons: list[str] = []
    priority = "normal"

    for item in newly_captured:
        stype = item.get("source_type", "")
        title = item.get("title", "")
        trigger_reasons.append(f"{stype}: {title}")
        if stype in ("ccdi_investigation", "ccdi_sanction"):
            priority = "urgent"
        elif stype == "gov_dom_diff" and item.get("is_anomaly", False):
            priority = "urgent"

    if include_existing_pending and not pending_ids:
        rows = conn.execute(
            "SELECT source_id, source_type, title FROM raw_sources WHERE ingest_status = 'pending' ORDER BY fetched_at ASC"
        ).fetchall()
        for r in rows:
            pending_ids.append(r["source_id"])
            trigger_reasons.append(f"{r['source_type']}: {r['title']}")
            if r["source_type"] in URGENT_SOURCE_TYPES:
                priority = "urgent"

    if not pending_ids:
        result: dict[str, Any] = {"gate_open": False, "reason": "no_new_sources"}
        if errors:
            result["errors"] = errors
        return result

    result = {
        "gate_open": True,
        "priority": priority,
        "trigger_reasons": trigger_reasons,
        "pending_source_ids": pending_ids,
    }
    if errors:
        result["errors"] = errors
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Cadre Tracker deterministic gate precheck")
    parser.add_argument("--db", type=Path, default=None, help="override SQLite DB path")
    parser.add_argument("--sources", default="ccdi,appoint,dom,media", help="comma-separated sources")
    parser.add_argument("--include-pending", action="store_true", help="include previously pending sources")
    args = parser.parse_args()

    conn = connect(args.db)
    try:
        migrate(conn)
        sources = [s.strip() for s in args.sources.split(",") if s.strip()]
        result = run_precheck(conn, sources=sources, include_existing_pending=args.include_pending)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
