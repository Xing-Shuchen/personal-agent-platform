#!/usr/bin/env python3
"""Read-only federated lookup from world-historian into cadre-tracker.sqlite3 (Section 9.4).

Strictly opens cadre.sqlite3 with SQLite URI ``?mode=ro`` and a 3-second timeout.
If the cadre-tracker database has not been initialized yet, gracefully returns an
empty context without ever blocking or raising into world-historian workflows.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sqlite3
from pathlib import Path
from typing import Any

ROOT = Path(os.environ.get("PAP_ROOT", str(Path(__file__).resolve().parents[3])))


def default_cadre_db_path() -> Path:
    data_dir = os.environ.get("PAP_DATA_DIR", "").strip()
    if data_dir:
        return Path(data_dir) / "cadre-tracker" / "cadre.sqlite3"
    return ROOT / "var" / "cadre-tracker" / "cadre.sqlite3"


def _load_cadre_db_module() -> Any | None:
    db_py = ROOT / "agents" / "cadre-tracker" / "runtime" / "db.py"
    if not db_py.is_file():
        return None
    spec = importlib.util.spec_from_file_location("cadre_tracker_runtime_db", db_py)
    if spec is None or spec.loader is None:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def lookup_cadre_context(
    entity_names: list[str],
    *,
    db_path: Path | str | None = None,
    reference_year: int = 2026,
    top_shockwave: int = 5,
) -> dict[str, Any]:
    """Read-only federated lookup returning career & shockwave context for named cadres."""
    path = Path(db_path) if db_path is not None else default_cadre_db_path()
    clean_names = [n.strip() for n in entity_names if isinstance(n, str) and n.strip()]
    if not clean_names or not path.is_file():
        return {"db_available": path.is_file(), "entities": []}

    cadre_db = _load_cadre_db_module()
    cutoff_ym = f"{reference_year - 10:04d}-01"

    try:
        uri = f"{path.resolve().as_uri()}?mode=ro"
        with sqlite3.connect(uri, uri=True, timeout=3.0) as conn:
            conn.row_factory = sqlite3.Row
            entities: list[dict[str, Any]] = []
            for name in clean_names:
                prow = conn.execute(
                    """SELECT person_id, name, birth_ym, native_place, current_rank, status, status_updated_at
                       FROM persons WHERE name = ? ORDER BY updated_at DESC LIMIT 1""",
                    (name,),
                ).fetchone()
                if prow is None:
                    continue
                pid = prow["person_id"]
                tenures = conn.execute(
                    """SELECT o.canonical_name AS org, t.role_title, t.role_tier, t.start_ym, t.end_ym
                       FROM tenures t
                       JOIN organizations o ON o.org_id = t.org_id
                       WHERE t.person_id = ?
                         AND (t.end_ym IS NULL OR t.end_ym >= ?)
                       ORDER BY t.start_ym DESC""",
                    (pid, cutoff_ym),
                ).fetchall()

                shockwave_summary: dict[str, Any] = {"already_fallen": [], "active_watch": []}
                if cadre_db is not None:
                    try:
                        sw = cadre_db.query_shockwave(
                            conn, pid, top_k=top_shockwave, reference_year=reference_year
                        )
                        shockwave_summary = {
                            "already_fallen": [
                                {
                                    "name": item["name"],
                                    "status": item["status"],
                                    "closeness_index": item["closeness_index"],
                                    "overlap_months": item["total_unique_overlap_months"],
                                }
                                for item in sw.get("already_fallen_associates", [])[:top_shockwave]
                            ],
                            "active_watch": [
                                {
                                    "name": item["name"],
                                    "current_rank": item["current_rank"],
                                    "closeness_index": item["closeness_index"],
                                    "overlap_months": item["total_unique_overlap_months"],
                                }
                                for item in sw.get("active_watch_list", [])[:top_shockwave]
                            ],
                        }
                    except Exception:
                        pass

                entities.append(
                    {
                        "person_id": pid,
                        "name": prow["name"],
                        "birth_ym": prow["birth_ym"],
                        "native_place": prow["native_place"],
                        "current_rank": prow["current_rank"],
                        "status": prow["status"],
                        "status_updated_at": prow["status_updated_at"],
                        "recent_tenures": [dict(t) for t in tenures],
                        "shockwave_context": shockwave_summary,
                    }
                )
            return {"db_available": True, "entities": entities}
    except sqlite3.Error:
        return {"db_available": False, "entities": []}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only federated cadre lookup for World Historian")
    parser.add_argument("--names", required=True, help="comma-separated cadre names")
    parser.add_argument("--db", type=Path, default=None, help="override cadre.sqlite3 path")
    parser.add_argument("--reference-year", type=int, default=2026)
    args = parser.parse_args(argv)
    names = [n.strip() for n in args.names.split(",") if n.strip()]
    result = lookup_cadre_context(names, db_path=args.db, reference_year=args.reference_year)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
