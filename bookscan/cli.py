"""Offline CLI for inspect, run, review, and evaluate."""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import cv2
import yaml

from . import __version__
from .annotations import collect_annotations
from .brackets import collect_brackets
from .epub import EpubIndex
from .groups import group_adjacent
from .inputs import (bbox_from_source, bbox_to_source, discover, infer_page_roi,
                     sha256, source_image, working_image)
from .pagenum import detect_page_number, interpolate
from .vision import (OCR, associate, curved_underline_candidates,
                     infer_page_rotation, merge_mark_candidates, text_lines, to_source_line,
                     underline_candidates)


def read_config(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("config must be a mapping")
    base = path.resolve().parent
    root = Path(data.get("root", "."))
    if not root.is_absolute():
        root = (base / root).resolve()
    data["root"] = str(root)
    for key in ("epub", "manifest", "output_dir"):
        if data.get(key):
            p = Path(data[key]).expanduser()
            if not p.is_absolute():
                p = (base / p).resolve()
            data[key] = str(p)
    if "models" not in data:
        raise ValueError("config.models is required")
    return data


def epub_path(root: Path, configured: str | None) -> Path:
    if configured:
        path = Path(configured)
        if not path.is_file():
            raise FileNotFoundError(path)
        return path
    books = list(root.glob("*.epub"))
    if len(books) != 1:
        raise ValueError(f"expected one EPUB under {root}, found {len(books)}")
    return books[0]


def write_json(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str) + "\n",
                    encoding="utf-8")


def write_jsonl(path: Path, records: list[dict]) -> None:
    path.write_text("".join(json.dumps(item, ensure_ascii=False, default=str) + "\n"
                            for item in records), encoding="utf-8")


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()]


def _cache_key(data: object) -> str:
    return hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False,
                                     default=str).encode()).hexdigest()


def _code_hash(*modules: str) -> str:
    digest = hashlib.sha256()
    root = Path(__file__).resolve().parent
    for module in modules:
        digest.update((root / module).read_bytes())
    return digest.hexdigest()


def _cached_json(path: Path, compute):
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8")), True
    value = compute()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    write_json(temporary, value)
    temporary.replace(path)
    return value, False


def inspect(root: Path, manifest: Path | None) -> int:
    pages = discover(root, manifest)
    books = sorted(root.glob("*.epub"))
    hashes = {}
    for page in pages:
        hashes.setdefault(page["source_sha256"], []).append(page["source_file"])
    report = {"root": str(root.resolve()), "file_count": len({p["source_file"] for p in pages}),
              "scan_count": len(pages),
              "formats": sorted({Path(p["source_file"]).suffix.lower() for p in pages}),
              "pages": [{k: p[k] for k in ("scan_index", "source_file", "source_page_index",
                                                "source_size", "source_sha256", "rotation",
                                                "valid_page_roi", "deskew_degrees", "exif_orientation",
                                                "input_error")}
                        for p in pages],
              "duplicate_files": [group for group in hashes.values() if len(set(group)) > 1],
              "epubs": [{"file": str(p), "sha256": sha256(p)} for p in books],
              "device": "cpu", "available_ocr_weights": [
                  {"name": name, "path": str(path),
                   "ready": all((path / file).is_file() for file in
                                ("inference.json", "inference.yml", "inference.pdiparams"))}
                  for name in ("PP-OCRv5_mobile_det", "PP-OCRv5_mobile_rec")
                  for path in [Path.home() / ".paddlex" / "official_models" / name]],
              "suggested_manifest": [
                  {"file": p["source_file"], "rotation": p["rotation"],
                   "deskew_degrees": p["deskew_degrees"],
                   "valid_page_roi": p["valid_page_roi"]} for p in pages]}
    for book in report["epubs"]:
        try:
            index = EpubIndex(Path(book["file"]))
            book.update({"parseable": True, "spine_items": len(index.chapters),
                         "paragraphs": len(index.paragraphs)})
        except Exception as exc:
            book.update({"parseable": False, "error": str(exc)})
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if (pages and not any(p["input_error"] for p in pages) and
                 len(books) == 1 and report["epubs"][0]["parseable"]) else 2


def prepare(config_path: Path) -> int:
    """The only command permitted to retrieve official OCR weights."""
    import shutil
    from paddleocr import TextDetection, TextRecognition

    config = read_config(config_path)
    models = config["models"]
    names = (("detection", TextDetection), ("recognition", TextRecognition))
    for prefix, model_class in names:
        name = models[f"{prefix}_name"]
        target = Path(models[f"{prefix}_dir"]).expanduser().resolve()
        if (target / "inference.pdiparams").is_file():
            print(f"ready: {name}: {target}")
            continue
        # No model_dir here: this explicit preparation step may download.
        model_class(model_name=name, device=models.get("device", "cpu"),
                    enable_mkldnn=False)
        official = Path.home() / ".paddlex" / "official_models" / name
        if not (official / "inference.pdiparams").is_file():
            raise FileNotFoundError(f"download did not produce model: {official}")
        if target != official:
            if target.exists():
                raise FileExistsError(f"incomplete model directory: {target}")
            shutil.copytree(official, target)
        print(f"ready: {name}: {target}")
    return 0


def _empty_page_number() -> dict:
    return {"observed_label": None, "observed_value": None,
            "inferred_value": None, "resolved_value": None,
            "status": "unknown", "bbox": None, "sequence_segment_id": None,
            "inference_evidence": [], "candidates": []}


def _overlay(working, page: dict, lines: list[dict], review_candidates: list[dict],
             page_number: dict, output: Path, annotations: list[dict],
             brackets: list[dict]) -> None:
    image = working.copy()
    for line in lines:
        x1, y1, x2, y2 = line["bbox"]
        cv2.rectangle(image, (x1, y1), (x2 - 1, y2 - 1), (0, 180, 0), 3)
        for mark in line["underlines"]:
            a, b, c, d = mark["bbox"]
            cv2.rectangle(image, (a, b), (c - 1, d - 1), (0, 0, 255), 3)
    for item in review_candidates:
        a, b, c, d = item["mark"]["bbox"]
        cv2.rectangle(image, (a, b), (c - 1, d - 1), (0, 165, 255), 2)
    if page_number["bbox"]:
        a, b, c, d = bbox_from_source(page_number["bbox"], page)
        cv2.rectangle(image, (a, b), (c - 1, d - 1), (255, 160, 0), 2)
    for note in annotations:
        a, b, c, d = note["working_bbox"]
        cv2.rectangle(image, (a, b), (c - 1, d - 1), (180, 50, 180), 3)
    for bracket in brackets:
        a, b, c, d = bracket["working_bbox"]
        cv2.rectangle(image, (a, b), (c - 1, d - 1), (180, 180, 0), 3)
    path = output / "overlays" / f'{page["page_id"]}.jpg'
    path.parent.mkdir(exist_ok=True)
    cv2.imwrite(str(path), image, [cv2.IMWRITE_JPEG_QUALITY, 85])
    clean = output / "pages" / f'{page["page_id"]}.jpg'
    clean.parent.mkdir(exist_ok=True)
    cv2.imwrite(str(clean), working, [cv2.IMWRITE_JPEG_QUALITY, 88])


def run(config_path: Path, limit: int | None = None,
        scan_indices: list[int] | None = None) -> int:
    os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"
    os.environ["HF_HUB_OFFLINE"] = "1"
    started = time.monotonic()
    config = read_config(config_path)
    root = Path(config["root"])
    manifest = Path(config["manifest"]) if config.get("manifest") else None
    pages = discover(root, manifest)
    if not pages:
        raise ValueError("no scans discovered")
    if limit is not None:
        pages = pages[:limit]
    if scan_indices:
        missing = set(scan_indices) - {p["scan_index"] for p in pages}
        if missing:
            raise ValueError(f"unknown scan indices: {sorted(missing)}")
        pages = [p for p in pages if p["scan_index"] in scan_indices]
    epub = epub_path(root, config.get("epub")) if config.get("epub") else None
    index = EpubIndex(epub) if epub else None
    ocr = OCR(config)  # Explicit local model paths: no run-time download.
    for page in pages:
        if (page["auto_rotation"] or page["auto_roi"]) and not page["input_error"]:
            source = source_image(page)
            if page["auto_roi"]:
                page["valid_page_roi"] = infer_page_roi(source)
                page["transform"]["crop"] = page["valid_page_roi"]
            x1, y1, x2, y2 = page["valid_page_roi"]
            if page["auto_rotation"]:
                page["rotation"] = infer_page_rotation(
                    source[y1:y2, x1:x2], ocr, config.get("selection", {}))
                page["transform"]["rotation_clockwise"] = page["rotation"]
    fingerprint = hashlib.sha256(json.dumps({"config": config,
        "inputs": [(p["source_sha256"], p["rotation"], p["deskew_degrees"],
                    p["valid_page_roi"], p["annotation_regions"], p["bracket_regions"])
                   for p in pages], "epub": index.sha256 if index else None,
        "models": ocr.hashes, "version": __version__},
        sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:12]
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + fingerprint
    output_root = Path(config.get("output_dir") or root / "output")
    output = output_root / run_id
    output.mkdir(parents=True, exist_ok=False)
    for subdir in ("crops", "overlays", "pages", "debug", "annotations", "brackets"):
        (output / subdir).mkdir()
    write_json(output / "epub-index.json", index.export() if index else None)
    all_lines, all_groups, all_annotations, all_brackets, reviews, failures = [], [], [], [], [], []
    page_records = []
    cache_root = root / ".cache" / "bookscan-v0.1"
    vision_code = _code_hash("vision.py", "inputs.py", "pagenum.py", "cli.py")
    ocr_code = _code_hash("vision.py")
    visual_hits = ocr_hits = 0
    for page in pages:
        page_start = time.monotonic()
        record = {k: v for k, v in page.items()
                  if k not in {"source_path", "auto_rotation", "auto_roi"}}
        record.update({"processing_status": "processing", "selected_line_count": 0,
                       "issues": [], "page_number": _empty_page_number()})
        try:
            source = source_image(page)
            working = working_image(source, page)
            visual_key = _cache_key({"image": page["source_sha256"],
                "frame": page["source_page_index"], "roi": page["valid_page_roi"],
                "rotation": page["rotation"], "deskew": page["deskew_degrees"],
                "det_model": ocr.hashes["detection"],
                "rec_model": ocr.hashes["recognition"], "selection": config.get("selection", {}),
                "page_numbers": config.get("page_numbers", {}), "code": vision_code})
            visual_path = cache_root / "visual" / f"{visual_key}.json"

            def compute_visual():
                detections = ocr.detect(working)
                geometry, rejected = text_lines(detections, config.get("selection", {}))
                typical = (sorted(b["bbox"][3] - b["bbox"][1] for b in geometry)
                           [len(geometry) // 2] if geometry else 40)
                marks = merge_mark_candidates(
                    underline_candidates(working, typical, config.get("selection", {})) +
                    curved_underline_candidates(working, geometry,
                                                config.get("selection", {})), typical)
                selected, reviews = associate(geometry, marks,
                                              config.get("selection", {}))
                number_issue = None
                try:
                    number = (_empty_page_number() if not config.get("page_numbers", {}).get(
                        "enabled", True) else detect_page_number(
                            working, detections, ocr, page, config.get("page_numbers", {})))
                except Exception as exc:
                    number = _empty_page_number()
                    number_issue = str(exc)
                return {"detections": detections, "line_geometry": geometry,
                        "rejected_boxes": rejected,
                        "underline_candidates": marks, "selected": selected,
                        "association_reviews": reviews, "page_number": number,
                        "page_number_issue": number_issue}

            visual, hit = _cached_json(visual_path, compute_visual)
            visual_hits += int(hit)
            detections = visual["detections"]
            line_geometry = visual["line_geometry"]
            rejected_boxes = visual["rejected_boxes"]
            marks = visual["underline_candidates"]
            selected = visual["selected"]
            candidate_reviews = visual["association_reviews"]
            record["page_number"] = visual["page_number"]
            if visual.get("page_number_issue"):
                record["issues"].append("page_number_error")
                failures.append({"stage": "page_number", "reason_code": "page_number_error",
                                 "page_id": page["page_id"],
                                 "detail": visual["page_number_issue"]})
            page_reviews = []
            for item in candidate_reviews:
                page_reviews.append({"page_id": page["page_id"],
                                "source_file": page["source_file"],
                                "coordinate_space": "source_raster",
                                "reason": item["reason"],
                                "mark": {**item["mark"], "bbox": bbox_to_source(
                                    item["mark"]["bbox"], page)},
                                "candidate_lines": [
                                    {"reading_order": line_geometry[i]["reading_order"],
                                    "bbox": bbox_to_source(line_geometry[i]["bbox"], page)}
                                    for i in item["candidate_lines"]]})
            reviews.extend(page_reviews)
            page_lines = []
            for item in selected:
                line = to_source_line(item, page, working, source, output)
                input_crop = line.pop("_text_crop_working")
                try:
                    crop_key = _cache_key({"image_sha256": hashlib.sha256(
                        input_crop.tobytes()).hexdigest(), "shape": input_crop.shape,
                        "rec_model": ocr.hashes["recognition"], "code": ocr_code})
                    cached, hit = _cached_json(cache_root / "ocr" / f"{crop_key}.json",
                        lambda: dict(zip(("text", "score"), ocr.recognize(input_crop))))
                    ocr_hits += int(hit)
                    raw, score = cached["text"], cached["score"]
                    line.update({"ocr_raw": raw, "ocr_score": score,
                                 "ocr_attempts": [{"text": raw, "score": score,
                                     "model": ocr.rec_name,
                                     "input": line["text_crop"],
                                     "preprocessing": "none"}],
                                 "text_effective": raw, "text_basis": "visual_ocr",
                                 "match_status": "grouped", "review_status": "unreviewed"})
                except Exception as exc:
                    line.update({"ocr_raw": "", "ocr_score": None,
                                 "ocr_attempts": [{"error": str(exc)}],
                                 "candidate_text": None, "corrected_text": None,
                                 "text_effective": "", "match_status": "ocr_failed",
                                 "review_status": "unreviewed", "epub_match": None,
                                 "edits": [], "review_reasons": ["ocr_error"]})
                    failures.append({"stage": "ocr", "reason_code": "ocr_error",
                                     "page_id": page["page_id"], "line_id": line["line_id"],
                                     "evidence_path": line["evidence_crop"],
                                     "detail": str(exc)})
                page_lines.append(line)
            page_groups = group_adjacent(page_lines, selected, working, page, output,
                                         index, config.get("alignment", {}))
            group_by_line = {line_id: group["group_id"] for group in page_groups
                             for line_id in group["line_ids"]}
            for line in page_lines:
                line["group_id"] = group_by_line[line["line_id"]]
            all_groups.extend(page_groups)
            page_annotations = collect_annotations(working, page, output, ocr)
            all_annotations.extend(page_annotations)
            page_brackets = collect_brackets(working, page, output, line_geometry,
                                            ocr, index, config.get("alignment", {}))
            for bracket in page_brackets:
                all_lines.extend(bracket.pop("line_records"))
                all_groups.append(bracket)
            all_brackets.extend(page_brackets)
            _overlay(working, page, selected, candidate_reviews,
                     record["page_number"], output, page_annotations, page_brackets)
            write_json(output / "debug" / f'{page["page_id"]}.json', {
                "coordinate_space": "working_crop_rotated",
                "detections": detections, "rejected_boxes": rejected_boxes,
                "underline_candidates": marks, "association_reviews": candidate_reviews})
            all_lines.extend(page_lines)
            record["selected_line_count"] = (len(page_lines) +
                                             sum(len(item["line_ids"]) for item in page_brackets))
            record["underline_line_count"] = len(page_lines)
            record["bracket_group_count"] = len(page_brackets)
            record["processing_status"] = "processed"
        except Exception as exc:
            record["processing_status"] = "failed"
            reason = "unsupported_input" if page.get("input_error") else "processing_error"
            record["issues"].append(reason)
            failures.append({"stage": "page", "reason_code": reason,
                             "page_id": page["page_id"], "detail": str(exc)})
        record["elapsed_seconds"] = round(time.monotonic() - page_start, 3)
        page_records.append(record)
        print(f'{len(page_records)}/{len(pages)} [scan {record["scan_index"]}] '
              f'{record["source_file"]}: '
              f'{record["processing_status"]}, {record["selected_line_count"]} lines',
              flush=True)
    interpolate(page_records)
    if not all_lines:
        failures.append({"stage": "run", "reason_code": "empty_unverified",
                         "detail": "No selected lines; inspect every page before accepting the result"})
    write_jsonl(output / "pages.jsonl", page_records)
    write_jsonl(output / "lines.jsonl", all_lines)
    write_jsonl(output / "groups.jsonl", all_groups)
    write_jsonl(output / "annotations.jsonl", all_annotations)
    write_jsonl(output / "brackets.jsonl", all_brackets)
    write_jsonl(output / "review_candidates.jsonl", reviews)
    write_jsonl(output / "failures.jsonl", failures)
    write_json(output / "manifest.resolved.json", [
        {k: v for k, v in p.items() if k != "source_path"} for p in pages])
    write_json(output / "run.json", {"schema_version": "0.1", "run_id": run_id,
        "version": __version__, "created_utc": datetime.now(timezone.utc).isoformat(),
        "config": config, "epub": index.metadata() if index else None,
        "models": {"detection_name": ocr.det_name, "recognition_name": ocr.rec_name,
                   "hashes": ocr.hashes},
        "environment": {"python": sys.version, "platform": platform.platform(),
            "packages": {name: importlib.metadata.version(name) for name in
                ("paddleocr", "paddlepaddle", "opencv-contrib-python", "numpy",
                 "pillow", "rapidfuzz", "lxml")},
            "requirements_lock_sha256": sha256(root / "requirements.lock")
                if (root / "requirements.lock").is_file() else None},
        "page_count": len(page_records), "line_count": len(all_lines),
        "group_count": len(all_groups),
        "annotation_count": len(all_annotations),
        "bracket_count": len(all_brackets),
        "cache_hits": {"visual_pages": visual_hits, "ocr_lines": ocr_hits},
        "failure_count": len(failures),
        "elapsed_seconds": round(time.monotonic() - started, 3)})
    from .review import build_review
    build_review(output)
    print(output)
    return 1 if failures else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m bookscan")
    commands = parser.add_subparsers(dest="command", required=True)
    a = commands.add_parser("inspect")
    a.add_argument("--root", type=Path, required=True)
    a.add_argument("--manifest", type=Path)
    prep = commands.add_parser("prepare", help="explicitly download configured OCR models")
    prep.add_argument("--config", type=Path, required=True)
    b = commands.add_parser("run")
    b.add_argument("--config", type=Path, required=True)
    b.add_argument("--limit", type=int, help="first N pages for a quick real-sample run")
    b.add_argument("--scan-index", type=int, action="append",
                   help="process one or more 0-based manifest positions")
    c = commands.add_parser("review")
    c.add_argument("--run", type=Path, required=True)
    d = commands.add_parser("evaluate")
    d.add_argument("--run", type=Path, required=True)
    d.add_argument("--ground-truth", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "inspect":
            return inspect(args.root, args.manifest)
        if args.command == "prepare":
            return prepare(args.config)
        if args.command == "run":
            return run(args.config, args.limit, args.scan_index)
        if args.command == "review":
            from .review import build_review
            build_review(args.run)
            return 0
        if args.command == "evaluate":
            from .evaluate import evaluate
            evaluate(args.run, args.ground_truth)
            return 0
    except Exception as exc:
        print(f"bookscan: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    return 2
