"""Apply a complete Bookscan web review through versioned Librarian records."""
from __future__ import annotations

import argparse
import hashlib
import json
from copy import deepcopy
from pathlib import Path

from .bookscan_adapter import adapt_report
from .gateway_review import candidate_id
from .pipeline import ExtractionOutput, process_capture, reconcile_extraction, _traces_for_capture
from .store import Library, LibrarianError


MAX_BUNDLE_BYTES = 2_000_000


def _invalid(message: str) -> None:
    raise LibrarianError("VALIDATION_FAILED", message)


def _text(value: object) -> str:
    if not isinstance(value, str) or len(value) > 20_000:
        _invalid("review text must be a bounded string")
    return value.strip()


def _box(value: object, width: int, height: int) -> list[int]:
    if (not isinstance(value, list) or len(value) != 4 or
            any(type(x) is not int for x in value)):
        _invalid("missing mark bbox must have four integer coordinates")
    x1, y1, x2, y2 = value
    if not (0 <= x1 < x2 <= width and 0 <= y1 < y2 <= height):
        _invalid("missing mark bbox must fit the source image")
    return value


def _source_report(lib: Library, owner: str, run_id: str) -> tuple[dict, dict]:
    matches = []
    for row in lib.db.execute("SELECT body FROM records WHERE owner_id=? AND "
                              "model='PageObservation' AND current=1", (owner,)):
        observation = json.loads(row["body"])
        processing = lib.get(owner, "ProcessingRun", observation["processing_run_id"])
        if processing["outcome"] not in {"success", "partial"}:
            continue
        try:
            report = json.loads(lib._read_object(observation["raw_output_asset"]))
        except (ValueError, TypeError):
            continue
        if report.get("run", {}).get("run_id") == run_id:
            matches.append((observation, report))
    if len(matches) != 1:
        _invalid("review run is not one current accepted Bookscan observation")
    return matches[0]


def review_context(lib: Library, owner: str, run_id: str) -> dict:
    observation, _ = _source_report(lib, owner, run_id)
    capture_id = observation["capture_id"]
    current = _traces_for_capture(lib, owner, capture_id)
    rows = [(row["rowid"], json.loads(row["body"])) for row in lib.db.execute(
        "SELECT rowid,body FROM records WHERE owner_id=? AND model='ProcessingRun' AND current=1",
        (owner,))]
    reviewed = [(rowid, run) for rowid, run in rows if run["capture_id"] == capture_id and
                run["extractor_version"].startswith("bookscan-human-review-v1:") and
                run["outcome"] in {"success", "partial"}]
    latest = max(reviewed, key=lambda item: item[0])[1]["id"] if reviewed else None
    return {"capture_id": capture_id,
            "expected_current": sorted(
                ({"trace_id": trace["id"], "revision": trace["revision"]}
                 for trace in current), key=lambda item: item["trace_id"]),
            "latest_review_run_id": latest}


def prepare_review(lib: Library, owner: str, bundle: dict) -> dict:
    """Validate every decision and construct a reviewed observation, without writes."""
    if not isinstance(bundle, dict) or not isinstance(bundle.get("run_id"), str):
        _invalid("review bundle needs a run ID")
    observation, original = _source_report(lib, owner, bundle["run_id"])
    if len(original.get("pages", [])) != 1:
        _invalid("reviewed Bookscan run must have exactly one page")
    page = original["pages"][0]
    page_id = page["page_id"]
    saved = bundle.get("pages")
    if not isinstance(saved, dict) or set(saved) != {page_id, "groups", "annotations"}:
        _invalid("review bundle has unexpected page or decision sections")
    state, groups, annotations = saved[page_id], saved["groups"], saved["annotations"]
    if (not isinstance(state, dict) or state.get("complete") is not True or
            not isinstance(groups, dict) or not isinstance(annotations, dict) or
            not isinstance(state.get("lines"), dict) or
            not isinstance(state.get("missing"), list)):
        _invalid("page review is incomplete")
    original_lines = {line["line_id"]: line for line in original["lines"]
                      if line["page_id"] == page_id and
                      line.get("mark_type", "underline") == "underline"}
    original_groups = {group["group_id"]: group for group in original["groups"]}
    original_notes = {note["annotation_id"]: note for note in original["annotations"]}
    if (set(state["lines"]) != set(original_lines) or
            set(groups) != set(original_groups) or
            set(annotations) != set(original_notes)):
        _invalid("review decisions do not cover the immutable Bookscan candidates")
    for decision in state["lines"].values():
        if (not isinstance(decision, dict) or
                decision.get("decision") not in {"accepted", "rejected"}):
            _invalid("every selected line needs a definite decision")
        _text(decision.get("text", ""))
    width, height = page["source_size"]
    if len(state["missing"]) > 100:
        _invalid("too many manually added marks")
    missing = []
    for item in state["missing"]:
        if not isinstance(item, dict):
            _invalid("missing mark must be an object")
        bbox = _box(item.get("bbox"), width, height)
        text = _text(item.get("text"))
        if not text:
            _invalid("missing mark requires a human transcription")
        missing.append((bbox, text))
    page_number = state.get("pageNumber", "")
    if page_number in ("", None):
        page_number = None
    elif (not isinstance(page_number, (int, str)) or
          not str(page_number).isdigit() or int(page_number) <= 0):
        _invalid("printed page number must be a positive integer")
    else:
        page_number = int(page_number)
    revised = deepcopy(original)
    revised["groups"] = []
    revised["annotations"] = []
    corrections = []
    for group in original["groups"]:
        verdict = groups[group["group_id"]]
        if (not isinstance(verdict, dict) or verdict.get("decision") not in
                {"accepted", "wrong_span", "wrong_epub", "rejected"}):
            _invalid("every mark group needs a definite decision")
        correction = _text(verdict.get("text", ""))
        if verdict["decision"] == "rejected":
            continue
        if (not correction and any(
                line_id in original_lines and _text(state["lines"][line_id]["text"])
                for line_id in group["line_ids"])):
            _invalid("edited line transcription needs an approved group quotation")
        kept = [line_id for line_id in group["line_ids"]
                if line_id not in original_lines or
                state["lines"][line_id]["decision"] == "accepted"]
        if not kept:
            _invalid("accepted group has no accepted lines")
        if len(kept) != len(group["line_ids"]) and verdict["decision"] != "wrong_span":
            _invalid("rejected line requires a wrong-span group decision")
        if verdict["decision"] in {"wrong_span", "wrong_epub"} and not correction:
            _invalid("wrong span or EPUB text requires a corrected quotation")
        changed = deepcopy(group)
        if len(kept) != len(group["line_ids"]):
            boxes = [next(line["line_bbox"] for line in original["lines"]
                          if line["line_id"] == identifier) for identifier in kept]
            changed["line_ids"] = kept
            changed["group_bbox"] = [min(box[0] for box in boxes),
                                     min(box[1] for box in boxes),
                                     max(box[2] for box in boxes),
                                     max(box[3] for box in boxes)]
            changed["underline_bboxes"] = [box for box in
                                            group.get("underline_bboxes", [])
                                            if any(box[1] < line[3] and box[3] > line[1]
                                                   for line in boxes)] or [changed["group_bbox"]]
        revised["groups"].append(changed)
        corrections.append(correction or None)
    for index, (bbox, text) in enumerate(missing):
        line_id = f"manual-line-{index}"
        revised["lines"].append({"line_id": line_id, "page_id": page_id,
                                 "line_bbox": bbox, "ocr_raw": text,
                                 "ocr_score": None})
        revised["groups"].append({"group_id": f"manual-group-{index}",
                                  "page_id": page_id, "mark_type": "underline",
                                  "line_ids": [line_id], "group_bbox": bbox,
                                  "underline_bboxes": [bbox], "ocr_raw": text,
                                  "match_status": "needs_review",
                                  "text_basis": "human_review",
                                  "text_effective": text})
        corrections.append(text)
    note_corrections = []
    for note in original["annotations"]:
        verdict = annotations[note["annotation_id"]]
        if (not isinstance(verdict, dict) or verdict.get("decision") not in
                {"accepted", "rejected"}):
            _invalid("every handwritten annotation needs a definite decision")
        if verdict["decision"] == "rejected":
            continue
        text = _text(verdict.get("text"))
        if not text:
            _invalid("accepted handwriting needs a human transcription")
        revised["annotations"].append(note)
        note_corrections.append(text)
    normalized = adapt_report(revised, width, height)
    capture_id = observation["capture_id"]
    reviewed = {candidate_id(capture_id, [f"bookscan_{index}_mark"]): correction
                for index, correction in enumerate(corrections)}
    reviewed.update({candidate_id(capture_id, [f"bookscan_note_{index}"]): text
                     for index, text in enumerate(note_corrections)})
    if len(reviewed) != len(corrections) + len(note_corrections):
        _invalid("reviewed mark identities collide")
    current = _traces_for_capture(lib, owner, capture_id)
    context = review_context(lib, owner, bundle["run_id"])
    supplied = bundle.get("expected_current")
    if supplied is not None:
        if (not isinstance(supplied, list) or supplied != context["expected_current"] or
                bundle.get("latest_review_run_id") != context["latest_review_run_id"]):
            raise LibrarianError("REVISION_CONFLICT", "review snapshot changed")
    elif context["latest_review_run_id"] is not None or any(
            trace["revision"] != 1 or
            trace["content"]["printed_text"]["basis"] == "user_statement" or
            trace["content"]["annotation"]["basis"] == "user_statement"
            for trace in current):
        raise LibrarianError("REVISION_CONFLICT", "review snapshot required after a correction")
    digest = hashlib.sha256(json.dumps(
        {"run_id": bundle["run_id"], "pages": saved,
         "latest_review_run_id": context["latest_review_run_id"]}, ensure_ascii=False,
        sort_keys=True, separators=(",", ":")).encode()).hexdigest()[:16]
    return {"capture_id": capture_id, "source_run_id": bundle["run_id"],
            "extractor_version": f"bookscan-human-review-v1:{digest}",
            "observation": normalized, "reviewed_candidates": reviewed,
            "page_number": page_number,
            "latest_review_run_id": context["latest_review_run_id"],
            "expected_current": {(trace["id"], trace["revision"]) for trace in current}}


def apply_review(lib: Library, owner: str, bundle: dict) -> dict:
    if not isinstance(bundle, dict) or not isinstance(bundle.get("run_id"), str) or \
            not isinstance(bundle.get("pages"), dict):
        _invalid("review bundle needs run ID and decisions")
    digest = hashlib.sha256(json.dumps(
        {"run_id": bundle["run_id"], "pages": bundle["pages"],
         "latest_review_run_id": bundle.get("latest_review_run_id")}, ensure_ascii=False,
        sort_keys=True, separators=(",", ":")).encode()).hexdigest()[:16]
    version = f"bookscan-human-review-v1:{digest}"
    rows = [json.loads(row["body"]) for row in lib.db.execute(
        "SELECT body FROM records WHERE owner_id=? AND model='ProcessingRun' AND current=1",
        (owner,))]
    completed = next((run for run in rows if run["extractor_version"] == version and
                      run["outcome"] in {"success", "partial"}), None)
    if completed:
        source, _ = _source_report(lib, owner, bundle["run_id"])
        if source["capture_id"] != completed["capture_id"]:
            _invalid("review run and applied capture differ")
        if review_context(lib, owner, bundle["run_id"])["latest_review_run_id"] != completed["id"]:
            raise LibrarianError("REVISION_CONFLICT", "a newer review has replaced this bundle")
        return {"status": "already_applied", "capture_id": completed["capture_id"],
                "run_id": completed["id"],
                "traces": len(_traces_for_capture(lib, owner, completed["capture_id"]))}
    plan = prepare_review(lib, owner, bundle)
    capture_id = plan["capture_id"]
    if {(trace["id"], trace["revision"]) for trace in
            _traces_for_capture(lib, owner, capture_id)} != plan["expected_current"]:
        raise LibrarianError("REVISION_CONFLICT", "traces changed since review preflight")
    pending = next((run for run in rows if run["capture_id"] == capture_id and
                    run["extractor_version"] == version and run["outcome"] == "pending"), None)
    if pending is None:
        observation = json.dumps(plan["observation"], ensure_ascii=False).encode()
        raw = json.dumps({"source_run_id": plan["source_run_id"],
                          "review_bundle": bundle,
                          "expected_current": sorted(plan["expected_current"]),
                          "reviewed_candidates": plan["reviewed_candidates"],
                          "observation": plan["observation"]},
                         ensure_ascii=False).encode()
        try:
            process_capture(lib, owner, capture_id,
                            lambda _original: ExtractionOutput(
                                raw=raw, derivative=None, derivative_width=None,
                                derivative_height=None, operations=(),
                                observation=observation),
                            extractor_version=version)
        except LibrarianError as error:
            if error.code != "RECONCILIATION_REQUIRED":
                raise
        rows = [json.loads(row["body"]) for row in lib.db.execute(
            "SELECT body FROM records WHERE owner_id=? AND model='ProcessingRun' AND current=1",
            (owner,))]
        pending = next((run for run in rows if run["capture_id"] == capture_id and
                        run["extractor_version"] == version and run["outcome"] == "pending"), None)
    if pending is None:
        raise LibrarianError("RECONCILIATION_REQUIRED", "reviewed observation unavailable")
    if {(trace["id"], trace["revision"]) for trace in
            _traces_for_capture(lib, owner, capture_id)} != plan["expected_current"]:
        raise LibrarianError("REVISION_CONFLICT", "traces changed before review reconciliation")
    traces = reconcile_extraction(lib, owner, capture_id, version,
                                  reviewed_candidates=plan["reviewed_candidates"],
                                  reviewed_page_number=plan["page_number"],
                                  expected_current_refs=plan["expected_current"],
                                  expected_run_id=pending["id"])
    return {"status": "applied", "capture_id": capture_id,
            "run_id": pending["id"], "traces": len(traces)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--owner", required=True)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.bundle.stat().st_size > MAX_BUNDLE_BYTES:
        _invalid("review bundle is too large")
    bundle = json.loads(args.bundle.read_text(encoding="utf-8"))
    with Library(args.root) as lib:
        result = prepare_review(lib, args.owner, bundle) if args.dry_run else \
            apply_review(lib, args.owner, bundle)
    if args.dry_run:
        result = {key: value for key, value in result.items()
                  if key not in {"observation", "reviewed_candidates", "expected_current"}}
    print(json.dumps(result, ensure_ascii=False, default=list))


if __name__ == "__main__":
    main()
