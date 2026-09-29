"""Read-only scope of old printed regions extending beyond their OCR source line."""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
from collections import Counter
from pathlib import Path
from typing import Any


def compact(value: str | None) -> str:
    return re.sub(r"\s+", "", value or "")


def audit(root: Path) -> dict[str, Any]:
    root = root.resolve()
    db = sqlite3.connect((root / "librarian.sqlite").as_uri() + "?mode=ro", uri=True)
    try:
        db.execute("PRAGMA query_only=ON")
        scanned = 0
        by_extractor: Counter[str] = Counter()
        flagged: dict[tuple[str, str], dict[str, Any]] = {}
        for (body,) in db.execute("SELECT body FROM records WHERE model='PageObservation'"):
            observation = json.loads(body)
            raw_ref = observation["raw_output_asset"]
            raw = json.loads((root / raw_ref["object_key"]).read_text(encoding="utf-8"))
            lines = {str(line["id"]): line for line in raw.get("lines", []) if "id" in line}
            extractor = observation["extractor"].split(":", 1)[0]
            for region in observation["printed_regions"]:
                if not region["id"].startswith("print_"):
                    continue  # Vision observation IDs do not map to OCR line IDs.
                scanned += 1
                by_extractor[extractor] += 1
                line = lines.get(region["id"][6:])
                text = compact((region.get("text") or {}).get("text"))
                ocr = compact(line.get("ocr_text")) if line else ""
                epub = compact(line.get("epub_text")) if line else ""
                if line is not None and text and (text in ocr or text in epub):
                    continue
                flagged[(observation["id"], region["id"])] = {
                    "capture_id": observation["capture_id"],
                    "observation_id": observation["id"],
                    "region_id": region["id"], "extractor": extractor,
                    "printed_chars": len(text), "ocr_line_chars": len(ocr),
                    "epub_line_chars": len(epub),
                    "line_present": line is not None,
                }

        refs = Counter()
        active = Counter()
        for current, body in db.execute(
                "SELECT current,body FROM records WHERE model='ReadingTrace' "
                "AND json_extract(body,'$.medium')='physical'"):
            trace = json.loads(body)
            observation_id = trace["source"]["observation_id"]
            for identifier in trace["source"]["detection_ids"]:
                key = (observation_id, identifier)
                if key not in flagged:
                    continue
                refs[key] += 1
                if current and trace["status"] == "active":
                    active[key] += 1

        regions = []
        for key, item in sorted(flagged.items()):
            regions.append({**item, "trace_revision_refs": refs[key],
                            "current_active_refs": active[key]})
        return {"ocr_regions_scanned": scanned,
                "regions_by_extractor": dict(sorted(by_extractor.items())),
                "flagged_regions": len(regions),
                "affected_captures": dict(sorted(Counter(
                    item["capture_id"] for item in regions).items())),
                "trace_revision_refs": sum(refs.values()),
                "current_active_refs": sum(active.values()),
                "regions": regions}
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--details", action="store_true", help="include affected IDs and lengths")
    args = parser.parse_args()
    result = audit(args.root)
    if not args.details:
        result.pop("regions")
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
