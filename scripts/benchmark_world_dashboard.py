"""Generate a disposable synthetic Chronicle and time a dashboard rebuild.

The scale 1 profile is the capacity target in specification_v0.7_dashboards.
No production Chronicle file is opened or modified.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import resource
import sqlite3
import tempfile
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def module(name: str):
    path = ROOT / "agents/world-historian/runtime" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


def populate(path: Path, threads: int, events: int, claims: int, entities: int, relations: int) -> None:
    db = module("db")
    conn = db.connect(path)
    db.migrate(conn)
    now = "2026-09-28T00:00:00Z"
    with conn:
        conn.executemany("INSERT INTO threads(id,title,created_at,updated_at) VALUES (?,?,?,?)",
                         ((f"t{i}", f"Synthetic thread {i}", now, now) for i in range(threads)))
        conn.executemany("INSERT INTO events(id,title,summary,occurred_at,occurred_at_precision,observed_at,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?)",
                         ((f"e{i}", f"Event {i}", f"Synthetic evidence {i}", f"2026-09-{i % 28 + 1:02d}", "day", now, now, now) for i in range(events)))
        conn.executemany("INSERT INTO thread_events(thread_id,event_id,created_at) VALUES (?,?,?)",
                         ((f"t{i % threads}", f"e{i}", now) for i in range(events)))
        conn.executemany("INSERT INTO entities(id,name,kind,aliases_json,created_at) VALUES (?,?,?,?,?)",
                         ((f"n{i}", f"Entity {i}", "organization", "[]", now) for i in range(entities)))
        conn.executemany("INSERT INTO event_entities(event_id,entity_id,role) VALUES (?,?,?)",
                         ((f"e{i}", f"n{i % entities}", "actor") for i in range(events)))
        source_count = max(1, claims // 10)
        conn.executemany("INSERT INTO sources(id,canonical_url,title,source_kind,fetched_at,created_at) VALUES (?,?,?,?,?,?)",
                         ((f"s{i}", f"https://example.test/{i}", f"Source {i}", "synthetic", now, now) for i in range(source_count)))
        conn.executemany("INSERT INTO claims(id,event_id,source_id,statement,asserted_at,confidence,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?)",
                         ((f"c{i}", f"e{i % events}", f"s{i % source_count}", f"Claim {i}", now, 0.7, now, now) for i in range(claims)))
        conn.executemany("INSERT INTO relations(id,src_type,src_id,dst_type,dst_id,relation_type,confidence,evidence_json,status,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                         ((f"r{i}", "event", f"e{i % events}", "event", f"e{(i * 17 + 1) % events}", "related_to", 0.6, "[]", "active", now, now) for i in range(relations)))
    conn.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scale", type=float, default=1.0)
    parser.add_argument("--keep", type=Path, help="keep generated files in this directory")
    args = parser.parse_args()
    if not 0 < args.scale <= 1:
        parser.error("scale must be within (0, 1]")
    sizes = {"threads": max(1, round(1000 * args.scale)),
             "events": max(1, round(100000 * args.scale)),
             "claims": max(1, round(500000 * args.scale)),
             "entities": max(1, round(50000 * args.scale)),
             "relations": max(1, round(1000000 * args.scale))}
    temporary = None
    if args.keep:
        args.keep.mkdir(parents=True, exist_ok=True)
        root = args.keep
    else:
        temporary = tempfile.TemporaryDirectory(prefix="wh-dashboard-benchmark-")
        root = Path(temporary.name)
    try:
        start = time.perf_counter()
        populate(root / "chronicle.sqlite", **sizes)
        setup_seconds = time.perf_counter() - start
        start = time.perf_counter()
        manifest = module("dashboard_projector").publish(root / "chronicle.sqlite", root / "dashboard")
        build_seconds = time.perf_counter() - start
        print(json.dumps({"sizes": sizes, "setup_seconds": round(setup_seconds, 2),
                          "build_seconds": round(build_seconds, 2),
                          "max_rss_mb": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1),
                          "manifest": manifest}, indent=2))
    finally:
        if temporary:
            temporary.cleanup()


if __name__ == "__main__":
    main()
