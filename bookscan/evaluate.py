"""One-to-one line evaluation against explicitly supplied human truth."""
from __future__ import annotations

import json
from pathlib import Path

from rapidfuzz.distance import Levenshtein


def _read(path: Path) -> list[dict]:
    return [json.loads(s) for s in path.read_text(encoding="utf-8").splitlines() if s]


def iou(a: list[int], b: list[int]) -> float:
    width = max(0, min(a[2], b[2]) - max(a[0], b[0]))
    height = max(0, min(a[3], b[3]) - max(a[1], b[1]))
    intersection = width * height
    area_a = max(0, a[2] - a[0]) * max(0, a[3] - a[1])
    area_b = max(0, b[2] - b[0]) * max(0, b[3] - b[1])
    return intersection / (area_a + area_b - intersection) if area_a + area_b > intersection else 0


def ratio(numerator: int | float, denominator: int | float) -> float | None:
    return round(numerator / denominator, 4) if denominator else None


def evaluate(run: Path, ground_truth: Path) -> dict:
    run = run.resolve()
    truth_pages = _read(ground_truth)
    page_ids = [p["page_id"] for p in truth_pages]
    if len(page_ids) != len(set(page_ids)):
        raise ValueError("duplicate truth page_id")
    machine_pages = _read(run / "pages.jsonl")
    expected_ids = {p["page_id"] for p in machine_pages}
    if set(page_ids) != expected_ids:
        raise ValueError("ground truth must cover every page in this run")
    # Corner brackets are a separate reading mark; this metric measures underlines.
    machine_lines = [line for line in _read(run / "lines.jsonl")
                     if line.get("mark_type", "underline") == "underline"]
    tp = fp = fn = ambiguous = 0
    ocr_edits = corrected_edits = truth_chars = 0
    corrected_count = correct_corrections = 0
    page_observed = page_observed_correct = page_inferred = page_inferred_correct = 0
    cases = []
    by_page = {p["page_id"]: [x for x in machine_lines if x["page_id"] == p["page_id"]]
               for p in machine_pages}
    machine_numbers = {p["page_id"]: p["page_number"] for p in machine_pages}
    for truth_page in truth_pages:
        page_id = truth_page["page_id"]
        actual = [line for line in truth_page.get("lines", []) if not line.get("ambiguous")]
        ambiguous_lines = [line for line in truth_page.get("lines", [])
                           if line.get("ambiguous")]
        ambiguous += len(ambiguous_lines)
        predicted = by_page[page_id]
        pairs = sorted(((iou(pred["line_bbox"], actual_line["bbox"]), pi, ti)
                        for pi, pred in enumerate(predicted)
                        for ti, actual_line in enumerate(actual)), reverse=True)
        used_pred, used_truth = set(), set()
        for overlap, pi, ti in pairs:
            if overlap < .5 or pi in used_pred or ti in used_truth:
                continue
            used_pred.add(pi)
            used_truth.add(ti)
            tp += 1
            pred, target = predicted[pi], actual[ti]
            if target.get("text") is not None:
                text = target["text"]
                truth_chars += len(text)
                ocr_edits += Levenshtein.distance(pred["ocr_raw"], text)
                corrected_edits += Levenshtein.distance(pred["text_effective"], text)
                if pred["corrected_text"] is not None:
                    corrected_count += 1
                    correct_corrections += int(pred["corrected_text"] == text)
        ignored_pred = {pi for pi, pred in enumerate(predicted) if pi not in used_pred
                        and any(iou(pred["line_bbox"], item["bbox"]) >= .5
                                for item in ambiguous_lines)}
        fp += len(predicted) - len(used_pred) - len(ignored_pred)
        fn += len(actual) - len(used_truth)
        cases.append({"page_id": page_id,
                      "missed": [actual[i]["bbox"] for i in range(len(actual))
                                 if i not in used_truth],
                      "false_positive": [predicted[i]["line_id"] for i in range(len(predicted))
                                         if i not in used_pred and i not in ignored_pred],
                      "ambiguous_predictions_excluded": [predicted[i]["line_id"]
                                                         for i in sorted(ignored_pred)]})
        number = machine_numbers[page_id]
        reference = truth_page.get("page_number")
        if reference is not None:
            if number["status"] == "observed":
                page_observed += 1
                page_observed_correct += int(number["resolved_value"] == reference)
            elif number["status"] == "inferred":
                page_inferred += 1
                page_inferred_correct += int(number["resolved_value"] == reference)
    precision = ratio(tp, tp + fp)
    recall = ratio(tp, tp + fn)
    metrics = {"schema_version": "0.1", "truth_pages": len(truth_pages),
               "ambiguous_lines_excluded": ambiguous,
               "line_selection": {"tp": tp, "fp": fp, "fn": fn,
                                  "precision": precision, "recall": recall,
                                  "f1": round(2 * precision * recall / (precision + recall), 4)
                                  if precision is not None and recall is not None
                                  and precision + recall else None},
               "ocr_cer_on_matched_lines": ratio(ocr_edits, truth_chars),
               "effective_cer_on_matched_lines": ratio(corrected_edits, truth_chars),
               "accepted_correction_count": corrected_count,
               "accepted_exact_accuracy": ratio(correct_corrections, corrected_count),
               "page_number": {"observed_count": page_observed,
                               "observed_accuracy": ratio(page_observed_correct, page_observed),
                               "inferred_count": page_inferred,
                               "inferred_accuracy": ratio(page_inferred_correct, page_inferred)},
               "cases": cases,
               "matching_rule": "one-to-one greedy descending bbox IoU >= 0.5"}
    (run / "metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2) + "\n",
                                       encoding="utf-8")
    print(json.dumps(metrics, ensure_ascii=False, indent=2))
    return metrics
