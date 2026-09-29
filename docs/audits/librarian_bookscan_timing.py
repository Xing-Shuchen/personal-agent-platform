"""Summarize persisted first-pass BookScan runs without exposing page text."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from math import ceil
from pathlib import Path
import sqlite3
from statistics import median


def summarize(root: Path) -> dict:
    root = root.resolve()
    with sqlite3.connect((root / "librarian.sqlite").as_uri() + "?mode=ro", uri=True) as db:
        runs = [json.loads(row[0]) for row in db.execute(
            "SELECT body FROM records WHERE model='ProcessingRun' AND current=1")]
        observations = {item["processing_run_id"]: item for row in db.execute(
            "SELECT body FROM records WHERE model='PageObservation' AND current=1")
            if (item := json.loads(row[0]))}
    reports = []
    for run in runs:
        if run["outcome"] not in {"success", "partial"}:
            continue
        observation = observations.get(run["id"])
        if observation is None:
            raise ValueError("first-pass run has no current observation")
        asset = observation["raw_output_asset"]
        path = (root / asset["object_key"]).resolve()
        if not path.is_relative_to(root / "objects"):
            raise ValueError("raw report is outside object store")
        reports.append(json.loads(path.read_text(encoding="utf-8"))["run"])
    if not reports:
        raise ValueError("no first-pass reports found")
    elapsed = sorted(float(report["elapsed_seconds"]) for report in reports)
    return {
        "first_pass_reports": len(reports),
        "elapsed_seconds": {"sum": round(sum(elapsed), 2),
                            "min": round(elapsed[0], 2),
                            "median": round(median(elapsed), 2),
                            "p90_nearest_rank": round(elapsed[ceil(.9 * len(elapsed)) - 1], 2),
                            "max": round(elapsed[-1], 2)},
        "devices": dict(Counter(report["config"]["models"]["device"]
                                for report in reports)),
        "detection_models": dict(Counter(report["models"]["detection_name"]
                                         for report in reports)),
        "recognition_models": dict(Counter(report["models"]["recognition_name"]
                                           for report in reports)),
        "cache_hit_totals": {
            key: sum(int(report["cache_hits"].get(key, 0)) for report in reports)
            for key in ("visual_pages", "ocr_lines")},
        "reported_failures": sum(int(report["failure_count"]) for report in reports),
        "reported_lines": sum(int(report["line_count"]) for report in reports),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    print(json.dumps(summarize(args.root), ensure_ascii=False, sort_keys=True, indent=2))
