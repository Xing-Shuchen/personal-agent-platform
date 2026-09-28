"""Offline validation of the Librarian schema entries and synthetic examples."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker, RefResolver

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from agents.librarian.runtime.store import LibrarianError, validate


ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = ROOT / "schemas"
EXAMPLES = ROOT / "examples"
REPORT = Path(__file__).with_name("validation-report.json")


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _deny_network(uri: str):
    raise AssertionError(f"unexpected external schema reference: {uri}")


def _domain_links(cases: list[dict]) -> None:
    records = {case["model"]: case["value"] for case in cases
               if case["id"].startswith("model-")}
    work, edition, instance = (records[name] for name in ("Work", "Edition", "BookInstance"))
    session, batch, capture = (records[name] for name in
                               ("ReadingSession", "CaptureBatch", "PageCapture"))
    resolution, run, observation = (records[name] for name in
                                    ("CaptureResolution", "ProcessingRun", "PageObservation"))
    trace, candidate, relation = (records[name] for name in
                                  ("ReadingTrace", "KnowledgeCandidate", "TraceRelation"))
    assert len({record["owner_id"] for record in records.values() if "owner_id" in record}) == 1
    assert edition["work_id"] == work["id"]
    assert instance["edition_id"] == edition["id"]
    assert (session["work_id"], session["edition_id"], session["book_instance_id"]) == (
        work["id"], edition["id"], instance["id"])
    assert capture["batch_id"] == batch["id"] and capture["id"] in batch["capture_ids"]
    assert all(capture["origin"][key] == batch["origin"][key]
               for key in batch["origin"])
    assert resolution["capture_id"] == run["capture_id"] == observation["capture_id"] == capture["id"]
    assert observation["processing_run_id"] == run["id"]
    assert (trace["work_id"], trace["edition_id"], trace["book_instance_id"],
            trace["session_id"]) == (work["id"], edition["id"], instance["id"], session["id"])
    assert trace["source"]["capture_id"] == capture["id"]
    assert trace["source"]["observation_id"] == observation["id"]
    assert trace["source"]["resolution_id"] == resolution["id"]
    assert trace["source"]["resolution_revision"] == resolution["revision"]
    assert trace["location"]["page_region_id"] in {page["id"] for page in observation["pages"]}
    detections = observation["printed_regions"] + observation["marks"] + observation["annotations"] + observation["symbols"]
    assert set(trace["source"]["detection_ids"]) <= {item["id"] for item in detections}
    assert trace["provenance"] == [capture["asset"], observation["raw_output_asset"]]
    assert candidate["source_trace_refs"] == [dict(trace_id=trace["id"], revision=trace["revision"])]
    assert relation["source_trace_ref"] == candidate["source_trace_refs"][0]
    digital = {case["id"]: case["value"] for case in cases if case["id"] in {"trace-weread", "trace-koodo"}}
    assert {value["medium"] for value in digital.values()} == {"weread", "koodo"}
    assert relation["target"]["id"] == digital["trace-weread"]["id"]


def check() -> dict:
    main = _load(SCHEMAS / "contracts.schema.json")
    Draft202012Validator.check_schema(main)
    entries = sorted(path for path in SCHEMAS.glob("*.schema.json")
                     if path.name != "contracts.schema.json")
    positives, negatives = (_load(EXAMPLES / f"{kind}.json") for kind in ("positive", "negative"))
    assert len(entries) == 18
    assert len(positives) == 42 and len(negatives) == 43
    assert len({case["id"] for case in positives + negatives}) == 85
    covered = set()
    for path in entries:
        entry = _load(path)
        Draft202012Validator.check_schema(entry)
        model = path.name.removesuffix(".schema.json")
        assert entry["$ref"] == f"{main['$id']}#/$defs/{model}"
        assert model in main["$defs"]
        baseline = next(case["value"] for case in positives if case["id"] == f"model-{model}")
        resolver = RefResolver.from_schema(entry, store={main["$id"]: main},
                                           handlers={"https": _deny_network})
        Draft202012Validator(entry, resolver=resolver,
                             format_checker=FormatChecker()).validate(baseline)
        covered.add(model)
    for case in positives:
        assert case["model"] in covered
        validate(case["model"], case["value"])
    for case in negatives:
        assert case["model"] in covered
        try:
            validate(case["model"], case["value"])
        except LibrarianError:
            pass
        else:
            raise AssertionError(f"negative fixture was accepted: {case['id']}")
    _domain_links(positives)
    return {"schema_definitions": len(main["$defs"]), "entry_models": len(entries),
            "positive_cases": len(positives), "negative_cases": len(negatives),
            "trace_media_examples": ["physical", "weread", "koodo"],
            "domain_link_checks": "passed", "offline_validation": "passed",
            "draft_definition_target": 77,
            "draft_definition_target_met": len(main["$defs"]) == 77}


if __name__ == "__main__":
    report = check()
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
