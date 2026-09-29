"""Aggregate current Librarian metadata without printing private reading text."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sqlite3


def summarize(database: Path) -> dict:
    with sqlite3.connect(database.resolve().as_uri() + "?mode=ro", uri=True) as db:
        traces = [json.loads(row[0]) for row in db.execute(
            "SELECT body FROM records WHERE model='ReadingTrace' AND current=1")]
        runs = [json.loads(row[0]) for row in db.execute(
            "SELECT body FROM records WHERE model='ProcessingRun' AND current=1")]
    active = [trace for trace in traces if trace["status"] == "active"]
    physical = [trace for trace in active if trace["medium"] == "physical"]
    unknown = [trace for trace in physical if trace["location"]["page"] is None]
    by_medium = {}
    for medium in sorted({trace["medium"] for trace in active}):
        group = [trace for trace in active if trace["medium"] == medium]
        by_medium[medium] = {
            "count": len(group),
            "source_locator_present": sum(bool(trace["location"].get("source_locator"))
                                          for trace in group),
            "marked_at_basis": dict(Counter(trace["marked_at"]["basis"]
                                            for trace in group)),
        }
    return {
        "active_by_medium": by_medium,
        "physical_page_known": len(physical) - len(unknown),
        "physical_page_unknown": len(unknown),
        "physical_unknown_page_captures": len({trace["source"]["capture_id"]
                                                for trace in unknown}),
        "physical_unknown_page_types": dict(Counter(
            kind for trace in unknown for kind in trace["trace_types"])),
        "physical_printed_basis": dict(Counter(
            trace["content"]["printed_text"]["basis"] for trace in physical)),
        "physical_annotation_basis": dict(Counter(
            trace["content"]["annotation"]["basis"] for trace in physical)),
        "physical_author_basis": dict(Counter(
            trace["attribution"]["basis"] for trace in physical)),
        "physical_page_confidence_present": sum(
            trace["confidence"]["page_number"] is not None for trace in physical),
        "physical_bbox_present": sum(trace["location"]["bbox"] is not None
                                     for trace in physical),
        "physical_provenance_asset_counts": dict(Counter(
            len(trace["provenance"]) for trace in physical)),
        "processing_runs": len(runs),
        "vocabulary_config_refs": sum(bool(run.get("vocabulary_config_ref"))
                                      for run in runs),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("database", type=Path)
    args = parser.parse_args()
    print(json.dumps(summarize(args.database), ensure_ascii=False, sort_keys=True, indent=2))
