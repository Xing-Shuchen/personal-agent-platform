"""Recover and complete Feishu capture batches in the Librarian runtime.

The OpenClaw plugin starts this worker after intake and on Gateway startup.
It uses local OCR for printed text and photo marks, an owner-provided EPUB for
alignment, and writes an idempotent Obsidian review note before notifying.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
from zipfile import ZipFile
from xml.etree import ElementTree as ET

from PIL import Image, ImageOps

from .ocr import visible_header_page
from .bookscan_adapter import bookscan_extractor, processor_fingerprint
from .gateway_review_finalize import auto_reconcile_fully_reviewed
from .pipeline import (process_capture, reconcile_extraction, bind_fingerprint_context,
                       resolve_capture,
                       _repair_trace_index_best_effort)
from .store import Library, LibrarianError, _new, _now, _unknown_time
from .koodo_native import sync_koodo_sqlite
from .weread_native import fetch_weread_book, sync_weread_book


def _current(lib: Library, owner: str, model: str) -> list[dict]:
    rows = lib.db.execute("SELECT body FROM records WHERE owner_id=? AND model=? AND current=1 ORDER BY rowid",
                          (owner, model)).fetchall()
    return [json.loads(row["body"]) for row in rows]


def _latest_pending_review_ids(runs: list[dict]) -> set[str]:
    """Older pending versions must not reopen a later reconciled capture."""
    latest = {run["capture_id"]: run for run in runs}
    return {capture_id for capture_id, run in latest.items()
            if run["outcome"] == "pending" and
            "RECONCILIATION_REQUIRED" in run["issues"]}


def _notified_batch_is_current(batch: dict, *, notified: bool,
                               revised_notice: bool, unbound: bool,
                               matching_runs: list[dict],
                               latest_runs: dict[str, dict],
                               pending_review_ids: set[str]) -> bool:
    captures = set(batch["capture_ids"])
    return (notified and revised_notice and not unbound and
            captures.isdisjoint(pending_review_ids) and
            {run["capture_id"] for run in matching_runs} == captures and
            all(latest_runs.get(capture_id, {}).get("outcome") in {"success", "partial"}
                for capture_id in captures))


def _header_for_legacy_regions(resolution: dict, observation: dict,
                               raw: dict) -> tuple[int, float] | None:
    """Reject margin paragraph numbers misread as vertical page boundaries."""
    pages = resolution["pages"]
    observed = observation["pages"]
    if not pages or len(pages) != len(observed) or not 1 <= len(pages) <= 3:
        return None
    if any(page["id"] != seen["id"] or page["bbox"] != seen["bbox"]
           for page, seen in zip(pages, observed)):
        return None
    header = visible_header_page(raw)
    if not header:
        return None
    if len(pages) == 1:
        return header if pages[0]["page"]["value"] is None else None
    x0, _, x1, _ = pages[0]["bbox"]
    if (x1 - x0 < .6 or
            any(abs(page["bbox"][0] - x0) > .002 or
                abs(page["bbox"][2] - x1) > .002 for page in pages)):
        return None
    markers = raw.get("page_markers", [])
    if (len(markers) != len(pages) - 1 or
            pages[0]["page"]["value"] is not None or
            any(marker.get("source") not in {"full_ocr", "margin_ocr"} or
                page["page"]["value"] is None or
                page["page"]["value"]["number"] != marker.get("number")
                for page, marker in zip(pages[1:], markers))):
        return None
    return header if all(marker["number"] != header[0] for marker in markers) else None


def _repair_visible_header_pages(lib: Library, owner: str, capture_ids: list[str]) -> int:
    """Resolve old unknown/margin-number regions from their own printed header."""
    runs = {run["capture_id"]: run for run in _current(lib, owner, "ProcessingRun")}
    resolutions = {item["capture_id"]: item for item in
                   _current(lib, owner, "CaptureResolution")}
    observations = {item["processing_run_id"]: item for item in
                    _current(lib, owner, "PageObservation")}
    repaired = 0
    for capture_id in capture_ids:
        run, resolution = runs.get(capture_id), resolutions.get(capture_id)
        if (not run or run["outcome"] not in {"success", "partial"} or
                not run["extractor_version"].startswith("rapidocr-epub-notes-") or
                not resolution):
            continue
        observation = observations.get(run["id"])
        if not observation:
            continue
        page_map = {page["id"]: page for page in resolution["pages"]}
        traces = [trace for trace in _current(lib, owner, "ReadingTrace")
                  if trace["status"] == "active" and
                  trace["source"].get("capture_id") == capture_id]
        if (not traces or not any(trace["location"]["page"] is None for trace in traces) or
                any((region := page_map.get(trace["location"]["page_region_id"])) is None or
                    trace["location"]["page"] != region["page"]["value"]
                    for trace in traces)):
            continue
        try:
            raw = json.loads(lib._read_object(observation["raw_output_asset"]))
            header = _header_for_legacy_regions(resolution, observation, raw)
        except (LibrarianError, ValueError, TypeError, KeyError):
            continue
        if not header:
            continue
        number, confidence = header
        pages = json.loads(json.dumps(resolution["pages"]))
        for page in pages:
            page["page"] = {"value": {"label": str(number), "number": number,
                                      "scheme": "arabic"},
                            "confidence": confidence, "basis": "vision",
                            "status": "resolved"}
        try:
            resolve_capture(lib, owner, capture_id, resolution["revision"],
                            pages=pages, _basis="vision")
        except LibrarianError as error:
            if error.code not in {"RECONCILIATION_REQUIRED", "REVISION_CONFLICT",
                                  "CONTEXT_CONFLICT"}:
                raise
            continue
        repaired += 1
    return repaired


def _epub_metadata(path: Path) -> dict:
    values: dict[str, list[str]] = {}
    with ZipFile(path) as archive:
        for name in archive.namelist():
            if name.lower().endswith(".opf"):
                root = ET.fromstring(archive.read(name))
                for element in root.iter():
                    key = element.tag.split("}")[-1]
                    if key in {"title", "creator", "publisher", "date", "language"} and element.text:
                        values.setdefault(key, []).append(element.text.strip())
                break
    return values


def _book_for_cover(root: Path, cover: bytes) -> tuple[str, Path] | None:
    from rapidocr import RapidOCR
    import numpy as np
    with Image.open(io.BytesIO(cover)) as source:
        image = ImageOps.exif_transpose(source).convert("RGB")
        image.thumbnail((2000, 2000))
        result = RapidOCR()(np.asarray(image))
    text = " ".join(result.txts or [])
    digits = re.sub(r"\D", "", text)
    for epub in sorted((root / "source-books").glob("[0-9]" * 13 + ".epub")):
        isbn = epub.stem
        if isbn in digits or re.search(r"ISBN\s*" + r"\D*".join(isbn), text, re.I):
            return isbn, epub
    return None


def _book_for_page(root: Path, original: bytes) -> tuple[str, Path] | None:
    """Identify an already supplied EPUB from multiple printed lines on a page.

    A single common phrase is insufficient evidence of a book identity. The
    worker can use this when the user sends interior pages without a cover.
    """
    from rapidocr import RapidOCR
    import numpy as np
    from .ocr import EpubGroundTruth

    epubs = sorted((root / "source-books").glob("[0-9]" * 13 + ".epub"))
    if not epubs:
        return None
    with Image.open(io.BytesIO(original)) as source:
        image = ImageOps.exif_transpose(source).convert("RGB")
        image.thumbnail((1800, 1800))
        result = RapidOCR()(np.asarray(image))
    lines = [line for line in (result.txts or []) if len(line) >= 12]
    if len(lines) < 3:
        return None
    choices = []
    for epub in epubs:
        ground_truth = EpubGroundTruth(epub)
        matches = sum(ground_truth.match(line)[1] >= .85 for line in lines)
        if matches >= 3 and matches / len(lines) >= .2:
            choices.append((matches, epub))
    if not choices:
        return None
    choices.sort(reverse=True)
    if len(choices) > 1 and choices[0][0] - choices[1][0] < 3:
        return None
    return choices[0][1].stem, choices[0][1]


def _processing_batches(batches: list[dict]) -> list[dict]:
    """Treat a quick sequence of single-photo messages as one review batch."""
    ordered = sorted(batches, key=lambda batch: batch["received_at"])
    groups: list[list[dict]] = []
    for batch in ordered:
        previous = groups[-1][-1] if groups else None
        same_scope = previous and all(
            batch["origin"][key] == previous["origin"][key]
            for key in ("transport", "account_id", "conversation_id"))
        gap = ((datetime.fromisoformat(batch["received_at"]) -
                datetime.fromisoformat(previous["received_at"])).total_seconds()
               if previous else float("inf"))
        if (same_scope and len(batch["capture_ids"]) == 1 and
                all(len(item["capture_ids"]) == 1 for item in groups[-1]) and
                0 <= gap <= 30 and len(groups[-1]) < 50):
            groups[-1].append(batch)
        else:
            groups.append([batch])
    merged = []
    for group in groups:
        if len(group) == 1:
            merged.append(group[0])
            continue
        digest = hashlib.sha256(json.dumps([item["id"] for item in group]).encode()).hexdigest()[:32]
        merged.append({**group[0], "id": "batch_" + digest,
                       "capture_ids": [item["capture_ids"][0] for item in group],
                       "source_batch_ids": [item["id"] for item in group]})
    return merged


def _catalog(lib: Library, owner: str, isbn: str, epub: Path, batch: dict) -> str:
    metadata = _epub_metadata(epub)
    title = metadata.get("title", [isbn])[0].split("（", 1)[0].split("(", 1)[0].strip()
    common = {"schema_version": "0.1.0", "owner_id": owner,
              "created_at": _now(), "revision": 1, "supersedes_revision": None}
    editions = [item for item in _current(lib, owner, "Edition")
                if item["isbn"]["isbn13"] == isbn]
    if len(editions) > 1:
        raise LibrarianError("CONTEXT_CONFLICT", "multiple editions share photographed ISBN")
    if editions:
        edition_id = editions[0]["id"]
        work_id = editions[0]["work_id"]
    else:
        work_id, edition_id = _new("work"), _new("edition")
        lib.register(owner, {**common, "object_type": "Work", "id": work_id,
                             "title": title, "original_title": None,
                             "authors": [{"name": name, "entity_id": None}
                                         for name in metadata.get("creator", [])],
                             "identifiers": []})
        date = metadata.get("date", [""])[0]
        lib.register(owner, {**common, "object_type": "Edition", "id": edition_id,
                             "work_id": work_id, "edition_label": None,
                             "publisher": metadata.get("publisher", [None])[0],
                             "publication_year": int(date[:4]) if date[:4].isdigit() else None,
                             "isbn": {"isbn13": isbn, "isbn10": None},
                             "language": metadata.get("language", [None])[0],
                             "page_count": None, "volume_label": None})
    scope = (batch["origin"]["transport"], batch["origin"]["account_id"],
             batch["origin"]["conversation_id"])
    assigned = lib.db.execute(
        "SELECT DISTINCT session_id FROM capture_context WHERE owner_id=? AND capture_id IN ("
        + ",".join("?" for _ in batch["capture_ids"]) + ")",
        (owner, *batch["capture_ids"])).fetchall()
    if len(assigned) > 1:
        raise LibrarianError("CONTEXT_CONFLICT", "batch captures have different sessions")
    affinity_id, _ = lib._choose_session((owner, *scope), None)
    chosen_id = assigned[0]["session_id"] if assigned else affinity_id
    chosen = lib.get(owner, "ReadingSession", chosen_id) if chosen_id else None
    if chosen and chosen["edition_id"] != edition_id:
        raise LibrarianError("CONTEXT_CONFLICT", "selected session conflicts with photographed ISBN")
    if chosen and chosen["status"] == "closed":
        raise LibrarianError("CONTEXT_CONFLICT", "closed session cannot receive a new batch")
    copies = [item for item in _current(lib, owner, "BookInstance")
              if item["edition_id"] == edition_id]
    if chosen:
        instance_id = chosen["book_instance_id"]
        if not instance_id or instance_id not in {item["id"] for item in copies}:
            raise LibrarianError("CONTEXT_CONFLICT", "selected session lacks a matching copy")
    elif len(copies) == 1:
        instance_id = copies[0]["id"]
    elif len(copies) > 1:
        raise LibrarianError("CONTEXT_CONFLICT", "multiple physical copies need explicit selection")
    else:
        instance_id = _new("copy")
        lib.register(owner, {**common, "object_type": "BookInstance", "id": instance_id,
                             "edition_id": edition_id, "medium": "physical",
                             "acquired_at": _unknown_time(), "ownership_status": "unknown",
                             "physical": {"qr_id": None, "shelf": None},
                             "reading_status": {"state": "unknown", "current_page": None,
                                                "progress_evidence_ref": None}})
    if chosen:
        session = chosen
    else:
        session = lib.start_session(owner, instance_id)
        received_at = batch["received_at"]
        with lib.transaction():
            lib._remember_session((owner, *scope), session["id"], received_at, False)
    with lib.transaction():
        for capture_id in batch["capture_ids"]:
            lib.db.execute("INSERT OR IGNORE INTO capture_context VALUES(?,?,?,?)",
                           (owner, capture_id, session["id"], "edition_fingerprint"))
    return title


def _repair_legacy_auto_affinity(lib: Library, owner: str) -> int:
    """Demote only legacy worker selections proven by edition-fingerprint captures."""
    lib.db.execute(
        "CREATE TABLE IF NOT EXISTS legacy_affinity_repairs ("
        "owner_id TEXT NOT NULL, transport TEXT NOT NULL, account_id TEXT NOT NULL, "
        "conversation_id TEXT NOT NULL, session_id TEXT NOT NULL, "
        "last_assigned_at TEXT NOT NULL, repaired_at TEXT NOT NULL, "
        "PRIMARY KEY(owner_id,transport,account_id,conversation_id,session_id))")
    rows = lib.db.execute(
        "SELECT transport,account_id,conversation_id,session_id FROM session_scope "
        "WHERE owner_id=? AND selected=1 AND last_assigned_at IS NULL", (owner,)).fetchall()
    repaired = 0
    for row in rows:
        scope = (row["transport"], row["account_id"], row["conversation_id"])
        captures = []
        for context in lib.db.execute(
                "SELECT capture_id,basis FROM capture_context WHERE owner_id=? AND session_id=?",
                (owner, row["session_id"])):
            if context["basis"] != "edition_fingerprint":
                captures = []
                break
            capture = lib.get(owner, "PageCapture", context["capture_id"])
            origin = capture["origin"]
            if (origin["transport"], origin["account_id"], origin["conversation_id"]) == scope:
                captures.append(capture)
        if not captures:
            continue
        received_at = max(item["received_at"] for item in captures)
        with lib.transaction():
            updated = lib.db.execute(
                "UPDATE session_scope SET selected=0,last_assigned_at=? "
                "WHERE owner_id=? AND transport=? AND account_id=? AND conversation_id=? "
                "AND session_id=? AND selected=1 AND last_assigned_at IS NULL",
                (received_at, owner, *scope, row["session_id"])).rowcount
            if updated:
                lib.db.execute("INSERT INTO legacy_affinity_repairs VALUES(?,?,?,?,?,?,?)",
                               (owner, *scope, row["session_id"], received_at, _now()))
                repaired += 1
    return repaired


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".librarian-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


_RETRY_DELAYS = (300, 1800, 7200)
_RETRYABLE_CODES = {"WORKER_FAILED", "EXTRACTOR_UNAVAILABLE",
                    "EXTRACTION_SCHEMA_INVALID"}


def _retry_fingerprint(root: Path, vision_model: str) -> str:
    sources = [(path.name, hashlib.sha256(path.read_bytes()).hexdigest())
               for path in sorted((root / "source-books").glob("*.epub"))]
    return hashlib.sha256(json.dumps({"vision_model": vision_model,
                                      "bookscan": processor_fingerprint(),
                                      "sources": sources}, sort_keys=True).encode()).hexdigest()[:16]


def _retry_due(status_file: Path, now: str, fingerprint: str) -> tuple[bool, int]:
    if not status_file.exists():
        return True, 0
    try:
        previous = json.loads(status_file.read_text(encoding="utf-8"))
        if previous.get("retry_fingerprint") != fingerprint:
            return True, 0
        attempts = previous.get("retry_attempts", 0)
        if not isinstance(attempts, int) or attempts < 0:
            return True, 0
        next_at = previous.get("next_retry_at")
        if previous.get("retry_exhausted") or attempts >= len(_RETRY_DELAYS):
            return False, attempts
        if next_at and datetime.fromisoformat(now) < datetime.fromisoformat(next_at):
            return False, attempts
        return True, attempts
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return True, 0


def _status_with_retry(outcome: dict, previous_attempts: int, now: str,
                       fingerprint: str) -> dict:
    codes = ({outcome.get("code")} |
             {issue.get("code") for issue in outcome.get("issues", [])
              if isinstance(issue, dict)})
    if not codes.intersection(_RETRYABLE_CODES):
        return {"at": now, **outcome, "retry_attempts": 0,
                "next_retry_at": None, "retry_exhausted": False,
                "retry_fingerprint": fingerprint}
    attempts = previous_attempts + 1
    exhausted = attempts >= len(_RETRY_DELAYS)
    return {"at": now, **outcome, "retry_attempts": attempts,
            "next_retry_at": None if exhausted else
            (datetime.fromisoformat(now) + timedelta(seconds=_RETRY_DELAYS[attempts - 1])).isoformat(),
            "retry_exhausted": exhausted, "retry_fingerprint": fingerprint}


def _trace_marker(trace_id: str, revision: int) -> str:
    return (f'<span hidden data-librarian-trace="{trace_id}" '
            f'data-revision="{revision}"></span>')


def _batch_marker(batch_id: str) -> str:
    return f'<span hidden data-librarian-batch="{batch_id}"></span>'


def _has_batch_marker(text: str, batch_id: str) -> bool:
    return (_batch_marker(batch_id) in text or
            f"<!-- librarian-batch: {batch_id} -->" in text)


def _hide_vault_markers(vault: Path, batch: dict) -> bool:
    """Upgrade earlier exports in place while leaving review edits intact."""
    folder = vault / "2Area" / "40 学习与阅读" / "阅读笔记"
    changed = False
    trace_pattern = re.compile(r"<!-- librarian-trace: (rt_[A-Za-z0-9_-]+) revision: (\d+) -->")
    for note in folder.glob("*.md"):
        original = note.read_text(encoding="utf-8")
        if not _has_batch_marker(original, batch["id"]):
            continue
        updated = trace_pattern.sub(lambda match: _trace_marker(match.group(1), int(match.group(2))),
                                    original)
        updated = updated.replace(f"<!-- librarian-batch: {batch['id']} -->",
                                  _batch_marker(batch["id"]))
        if updated != original:
            _atomic_write(note, updated.encode("utf-8"))
            changed = True
    return changed


def _render_batch_note_legacy(batch: dict, title: str, traces: list[dict], *,
                              created: str, spatial_order: bool = True) -> str:
    traces = list(traces)
    if spatial_order:
        traces.sort(key=lambda item: ((item["location"]["page"] or {}).get("number", 0),
                                      item["location"]["bbox"][1]))
    else:
        traces.sort(key=lambda item: (item["location"]["page"] or {}).get("number", 0))
    if not traces:
        raise LibrarianError("NO_MARKS", "no reading marks found in batch")
    lines = (["---", "type: reference", "area: reading", "status: review",
              f"created: {created}", f"updated: {created}", "---", "",
              f"# {title}", "", f"- ISBN: {batch.get('isbn', '待核对')}",
              "- 来源：飞书图书专员；正文依据 EPUB 对齐，划线与笔记位置依据照片。",
              "- 状态：待人工 review", ""])
    for trace in traces:
        page = trace["location"]["page"]
        label = page["label"] if page else "页码待核对"
        lines.extend([f"## 第 {label} 页 · {'、'.join(trace['trace_types'])}", "",
                      _trace_marker(trace['id'], trace['revision'])])
        printed = trace["content"]["printed_text"]["text"]
        annotation = trace["content"]["annotation"]["text"]
        if printed:
            lines.extend(["", "**画线**", "", printed])
        if annotation:
            lines.extend(["", "**手写笔记（待核对）**", "", annotation])
        lines.extend(["", f"原图证据：`{trace['source']['capture_id']}`（保存在 Librarian 数据库）", ""])
    return "\n".join(lines).rstrip() + "\n\n" + _batch_marker(batch["id"]) + "\n"


def _render_batch_note(batch: dict, title: str, traces: list[dict], *,
                       created: str, spatial_order: bool = True,
                       presentation_version: int = 6,
                       received_at_by_capture: dict[str, str] | None = None) -> str:
    if not traces:
        raise LibrarianError("NO_MARKS", "no reading marks found in batch")
    traces = sorted(traces, key=lambda item: (
        (item["location"]["page"] or {}).get("number") or
        (0 if presentation_version == 1 else 10**9),
        item["location"]["bbox"][1]))
    notes = [trace for trace in traces if trace["content"]["annotation"]["text"]]
    highlights = [trace for trace in traces if trace["content"]["printed_text"]["text"]
                  and trace not in notes]
    unreadable = [trace for trace in traces if trace not in notes and trace not in highlights]
    lines = ["---", "doc_type: physical-highlights-notes", "type: reference",
             "area: reading", "status: review", f"created: {created}",
             f"updated: {created}", f"isbn: '{batch.get('isbn', '')}'",
             f"noteCount: {len(highlights)}", f"reviewCount: {len(notes)}",
             *([f"unreadableCount: {len(unreadable)}"] if presentation_version >= 5 else []),
             "---", "", "# 元数据", f"> [!abstract] {title}",
             f"> - 书名： {title}", f"> - ISBN： {batch.get('isbn', '待核对')}",
             "> - 来源： 飞书图书专员 · 纸质书照片",
             "> - 状态： 待人工 review", ""]

    def render_section(heading: str, entries: list[dict]) -> None:
        if not entries:
            return
        lines.extend([f"# {heading}", ""])
        last_page = None
        for trace in entries:
            page = trace["location"]["page"]
            label = page["label"] if page else "页码待核对"
            if label != last_page:
                lines.extend([f"## 第 {label} 页" if page else "## 页码待核对", ""])
                last_page = label
            printed = trace["content"]["printed_text"]["text"]
            annotation = trace["content"]["annotation"]["text"]
            if heading == "读书笔记":
                lines.extend(["### 划线评论" if printed else "### 手写笔记（待核对）", ""])
            if printed:
                flattened = printed
                if presentation_version == 2:
                    flattened = re.sub(r"(?<=[A-Za-z0-9])\n(?=[A-Za-z0-9])", " ", printed)
                    flattened = flattened.replace("\n", "")
                if presentation_version == 3:
                    quote_lines = flattened.splitlines()
                    for index, quote_line in enumerate(quote_lines):
                        prefix = "> 📌 " if index == 0 else "> "
                        suffix = f" ^{trace['id']}" if index == len(quote_lines) - 1 else ""
                        lines.append(prefix + quote_line + suffix)
                else:
                    if presentation_version >= 4:
                        flattened = re.sub(r"\s*\n\s*", "", printed.strip())
                    lines.append(f"> 📌 {flattened} ^{trace['id']}")
                if presentation_version != 1 and not flattened.rstrip().endswith(("。", "！", "？", "!", "?")):
                    lines.append("> ⚠️ 转录可能不完整，待核对")
            if annotation:
                rendered_note = annotation if presentation_version == 1 else annotation.replace("\n", " / ")
                lines.append(f"> 💭 {rendered_note}（手写待核对）")
            if not printed and not annotation and presentation_version >= 5:
                lines.append(f"> ⚠️ 检测到标记，文字尚未辨认 ^{trace['id']}")
            source_time = (received_at_by_capture or {}).get(trace["source"]["capture_id"])
            try:
                stamp = datetime.fromisoformat(
                    source_time if presentation_version >= 6 else trace["created_at"]
                ).astimezone(ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%d %H:%M:%S")
            except (TypeError, KeyError, ValueError):
                stamp = "未知" if presentation_version >= 6 else created
            time_label = f"收图：{stamp}" if presentation_version >= 6 else stamp
            lines.extend([f"> ⏱ {time_label}",
                          f"> 原图证据：`{trace['source']['capture_id']}`",
                          _trace_marker(trace["id"], trace["revision"]), ""])

    render_section("高亮划线", highlights)
    render_section("读书笔记", notes)
    if presentation_version >= 5:
        render_section("待核对的标记", unreadable)
    lines.append(_batch_marker(batch["id"]))
    return "\n".join(lines).rstrip() + "\n"


def _capture_received_times(lib: Library, owner: str, capture_ids: set[str]) -> dict[str, str]:
    return {capture["id"]: capture["received_at"]
            for capture in _current(lib, owner, "PageCapture")
            if capture["id"] in capture_ids}


def _export(lib: Library, owner: str, batch: dict, title: str, vault: Path) -> Path:
    folder = vault / "2Area" / "40 学习与阅读" / "阅读笔记"
    note = folder / f"{title}.md"
    traces = [trace for trace in _current(lib, owner, "ReadingTrace")
              if trace["status"] == "active" and
              trace["source"].get("capture_id") in batch["capture_ids"]]
    received = _capture_received_times(lib, owner, set(batch["capture_ids"]))
    block = _render_batch_note(batch, title, traces, created=_now()[:10],
                               received_at_by_capture=received)
    if note.exists():
        old = note.read_text(encoding="utf-8")
        if re.search(r'data-librarian-batch="batch_book_[0-9]{13}"', old):
            return note
        if _has_batch_marker(old, batch["id"]):
            return note
        block = old.rstrip() + "\n\n" + block
    _atomic_write(note, block.encode("utf-8"))
    return note


def _refresh_generated_note(vault: Path, batch: dict, title: str,
                            old_traces: list[dict], new_traces: list[dict],
                            received_at_by_capture: dict[str, str] | None = None) -> Path:
    """Replace only an unchanged generated note; preserve any review edits."""
    note = vault / "2Area" / "40 学习与阅读" / "阅读笔记" / f"{title}.md"
    old = note.read_text(encoding="utf-8")
    if re.search(r'data-librarian-batch="batch_book_[0-9]{13}"', old):
        return note
    match = re.search(r"(?m)^created: (\d{4}-\d{2}-\d{2})$", old)
    candidates = (
            _render_batch_note(batch, title, old_traces, created=match.group(1),
                               received_at_by_capture=received_at_by_capture),
            _render_batch_note(batch, title, old_traces, created=match.group(1),
                               presentation_version=5),
            _render_batch_note(batch, title, old_traces, created=match.group(1),
                               presentation_version=1),
            _render_batch_note(batch, title, old_traces, created=match.group(1),
                               presentation_version=2),
            _render_batch_note(batch, title, old_traces, created=match.group(1),
                               presentation_version=3),
            _render_batch_note(batch, title, old_traces, created=match.group(1),
                               presentation_version=4),
            _render_batch_note_legacy(batch, title, old_traces, created=match.group(1)),
            _render_batch_note_legacy(batch, title, old_traces,
                                      created=match.group(1), spatial_order=False)) if match else ()
    matches = [(candidate, old.find(candidate)) for candidate in candidates
               if old.count(candidate) == 1]
    matches = [(candidate, index) for candidate, index in matches
               if (index == 0 or old[:index].endswith("\n\n")) and
               (index + len(candidate) == len(old) or
                old[index + len(candidate):].startswith("\n"))]
    if not matches:
        raise LibrarianError("REVIEW_EDIT_CONFLICT", "Vault review note has edits; preserve it for manual reconciliation")
    matched, index = matches[0]
    revised = _render_batch_note(batch, title, new_traces, created=match.group(1),
                                 received_at_by_capture=received_at_by_capture)
    updated = old[:index] + revised + old[index + len(matched):]
    if updated != old:
        _atomic_write(note, updated.encode("utf-8"))
    return note


def _consolidate_generated_note(lib: Library, owner: str, title: str,
                                vault: Path) -> Path:
    """Collapse only verifiably generated blocks into one WeRead-style note."""
    note = vault / "2Area" / "40 学习与阅读" / "阅读笔记" / f"{title}.md"
    old = note.read_text(encoding="utf-8")
    blocks = [part.strip() for part in re.split(
        r"(?=^---\n(?:doc_type:|type:))", old, flags=re.M) if part.strip()]
    if not blocks or "".join(blocks) == "":
        raise LibrarianError("REVIEW_EDIT_CONFLICT", "generated review note unavailable")
    editions = [edition for edition in _current(lib, owner, "Edition")
                if edition["isbn"]["isbn13"] and
                lib.get(owner, "Work", edition["work_id"])["title"] == title]
    if len(editions) != 1:
        return note
    isbn = editions[0]["isbn"]["isbn13"]
    aggregate_id = f"batch_book_{isbn}"
    batches = {batch["id"]: batch for batch in
               _current(lib, owner, "CaptureBatch") +
               _processing_batches(_current(lib, owner, "CaptureBatch"))}
    date = None
    for block in blocks:
        marker = re.search(r'data-librarian-batch="([^"]+)"', block)
        stamp = re.search(r"(?m)^created: (\d{4}-\d{2}-\d{2})$", block)
        if not marker or not stamp:
            raise LibrarianError("REVIEW_EDIT_CONFLICT", "review note has an unverified block")
        date = date or stamp.group(1)
        batch = dict(batches.get(marker.group(1), {"id": aggregate_id}))
        if marker.group(1) != aggregate_id and marker.group(1) not in batches:
            raise LibrarianError("REVIEW_EDIT_CONFLICT", "review note batch is unknown")
        batch["isbn"] = isbn
        refs = re.findall(r'data-librarian-trace="([^"]+)" data-revision="(\d+)"', block)
        traces = []
        for trace_id, revision in refs:
            row = lib.db.execute(
                "SELECT body FROM records WHERE owner_id=? AND model='ReadingTrace' "
                "AND id=? AND revision=?",
                (owner, trace_id, int(revision))).fetchone()
            if row is None:
                raise LibrarianError("REVIEW_EDIT_CONFLICT", "review note trace is unknown")
            traces.append(json.loads(row["body"]))
        if not traces:
            raise LibrarianError("REVIEW_EDIT_CONFLICT", "review note has no trace anchors")
        received = _capture_received_times(lib, owner,
                                            {trace["source"]["capture_id"] for trace in traces})
        variants = [_render_batch_note(batch, title, traces, created=stamp.group(1),
                                       presentation_version=version,
                                       received_at_by_capture=received).strip()
                    for version in (1, 2, 3, 4, 5, 6)]
        variants.extend([_render_batch_note_legacy(batch, title, traces,
                                                   created=stamp.group(1)).strip(),
                         _render_batch_note_legacy(batch, title, traces,
                                                   created=stamp.group(1),
                                                   spatial_order=False).strip()])
        if block not in variants:
            raise LibrarianError("REVIEW_EDIT_CONFLICT", "review note has user edits")
    sessions = {session["id"] for session in _current(lib, owner, "ReadingSession")
                if session["edition_id"] == editions[0]["id"]}
    related_captures = {row["capture_id"] for row in lib.db.execute(
        "SELECT capture_id,session_id FROM capture_context WHERE owner_id=?", (owner,))
        if row["session_id"] in sessions}
    current = [trace for trace in _current(lib, owner, "ReadingTrace")
               if trace["status"] == "active" and trace["medium"] == "physical" and
               trace["source"].get("capture_id") in related_captures]
    if not current:
        return note
    rendered = _render_batch_note({"id": aggregate_id, "isbn": isbn},
                                  title, current, created=date,
                                  received_at_by_capture=_capture_received_times(
                                      lib, owner,
                                      {trace["source"]["capture_id"] for trace in current}))
    if rendered != old:
        _atomic_write(note, rendered.encode("utf-8"))
    return note


def _refresh_generated_notes(lib: Library, owner: str, vault: Path | None) -> list[dict]:
    """Keep generated notes current even when a batch is waiting for review."""
    if vault is None:
        return []
    titles = {lib.get(owner, "Work", edition["work_id"])["title"]
              for edition in _current(lib, owner, "Edition")}
    folder = vault / "2Area" / "40 学习与阅读" / "阅读笔记"
    issues = []
    for title in titles:
        if not (folder / f"{title}.md").is_file():
            continue
        try:
            _consolidate_generated_note(lib, owner, title, vault)
        except LibrarianError as error:
            issues.append({"source": "vault_note", "title": title,
                           "status": "review_required" if error.code == "REVIEW_EDIT_CONFLICT" else "error",
                           "code": error.code})
        except Exception:
            issues.append({"source": "vault_note", "title": title,
                           "status": "error", "code": "WORKER_FAILED"})
    return issues


def _remove_vault_images(vault: Path, batch: dict) -> bool:
    """Migrate our earlier review export without touching user-written text."""
    folder = vault / "2Area" / "40 学习与阅读" / "阅读笔记"
    changed = False
    pattern = re.compile(r"!\[\[Attachments/Librarian/" + re.escape(batch["id"])
                         + r"/(capture_[A-Za-z0-9_-]+)\.jpg\]\]")
    for note in folder.glob("*.md"):
        original = note.read_text(encoding="utf-8")
        if not _has_batch_marker(original, batch["id"]):
            continue
        updated = pattern.sub(lambda match:
                              f"原图证据：`{match.group(1)}`（保存在 Librarian 数据库）", original)
        if updated != original:
            _atomic_write(note, updated.encode("utf-8"))
            changed = True
    image_dir = folder / "Attachments" / "Librarian" / batch["id"]
    if image_dir.is_dir():
        shutil.rmtree(image_dir)
        changed = True
    return changed


def _notify(root: Path, batch: dict, note: Path, count: int, *,
            unresolved: int = 0, issues: int = 0) -> None:
    marker = root / "notifications" / f"{batch['id']}.json"
    if marker.exists():
        return
    alignment = "、EPUB 辅助核对" if batch.get("isbn") else ""
    message = (f"《{note.stem}》照片已用 OCR 识别{alignment}，并写入图书专员数据库和 Obsidian。"
               f"当前 {count} 条画线/笔记；{unresolved} 条页码、{issues} 张提取差异待核对。"
               f"请在「2Area/40 学习与阅读/阅读笔记/{note.name}」review；"
               "手写文字标为待核对。")
    command = ["openclaw", "message", "send", "--channel", "feishu", "--account", "librarian",
               "--target", batch["origin"]["conversation_id"], "--message", message, "--json"]
    result = subprocess.run(command, capture_output=True, text=True, timeout=45)
    if result.returncode:
        raise RuntimeError("Feishu review notification failed")
    _atomic_write(marker, json.dumps({"batch_id": batch["id"], "sent_at": _now()}).encode())


def _review_digest(traces: list[dict]) -> str:
    evidence = [(trace["id"], trace["revision"], trace["location"]["page"],
                 trace["content"]["printed_text"]["text"],
                 trace["content"]["annotation"]["text"])
                for trace in sorted(traces, key=lambda item: item["id"])]
    return hashlib.sha256(json.dumps(evidence, ensure_ascii=False,
                                     sort_keys=True).encode()).hexdigest()[:16]


def _notify_correction(root: Path, batch: dict, note: Path, count: int, *,
                       unresolved: int = 0, issues: int = 0,
                       revision_key: str) -> None:
    marker = root / "notifications" / f"{batch['id']}-revision-{revision_key}.json"
    if marker.exists():
        return
    message = (f"《{note.stem}》的页码与画线识别已更新，数据库和 Obsidian 已同步更新。"
               f"现有 {count} 条画线/笔记；{unresolved} 条页码、{issues} 张提取差异待核对。"
               f"请在「2Area/40 学习与阅读/阅读笔记/{note.name}」review。")
    result = subprocess.run(["openclaw", "message", "send", "--channel", "feishu",
                             "--account", "librarian", "--target",
                             batch["origin"]["conversation_id"], "--message", message,
                             "--json"], capture_output=True, text=True, timeout=45)
    if result.returncode:
        raise RuntimeError("Feishu correction notification failed")
    _atomic_write(marker, json.dumps({"batch_id": batch["id"],
                                       "sent_at": _now()}).encode())


def _sync_digital(lib: Library, root: Path, owner: str, *,
                  koodo: tuple[str, Path, Path] | None,
                  weread: tuple[str, Path, list[str]] | None) -> list[dict]:
    results = []
    if koodo:
        source_id, books_db, notes_db = koodo
        try:
            counts = sync_koodo_sqlite(lib, owner, source_id, books_db, notes_db)
            results.append({"source": "koodo", "status": "success", "counts": counts})
        except Exception as error:
            results.append({"source": "koodo", "status": "error",
                            "code": error.code if isinstance(error, LibrarianError) else "SYNC_FAILED"})
    if weread:
        source_id, data_path, book_ids = weread
        try:
            plugin_data = json.loads(data_path.read_text(encoding="utf-8"))
            if not isinstance(plugin_data, dict):
                raise LibrarianError("UPSTREAM_FORMAT_UNSUPPORTED", "WeRead plugin data invalid")
            key = plugin_data.get("wereadApiKey")
            if not isinstance(key, str) or not key:
                raise LibrarianError("UPSTREAM_UNAVAILABLE", "WeRead API key unavailable")
        except Exception as error:
            key = None
            results.append({"source": "weread", "status": "error",
                            "code": error.code if isinstance(error, LibrarianError) else "SYNC_FAILED"})
        for book_id in book_ids:
            if key is None:
                break
            try:
                book, items = fetch_weread_book(key, book_id)
                counts = sync_weread_book(lib, owner, source_id, book, items)
                results.append({"source": "weread", "status": "success", "counts": counts})
            except Exception as error:
                results.append({"source": "weread", "status": "error",
                                "code": error.code if isinstance(error, LibrarianError) else "SYNC_FAILED"})
    if koodo or weread:
        _atomic_write(root / "digital-sync-status.json", json.dumps(
            {"completed_at": _now(), "results": results}, ensure_ascii=False).encode())
    return results


def _process_batch(lib: Library, root: Path, vault: Path | None, owner: str,
                   batch: dict, vision_model: str) -> dict:
    if vault:
        _remove_vault_images(vault, batch)
        _hide_vault_markers(vault, batch)
    notified = (root / "notifications" / f"{batch['id']}.json").exists()
    match = None
    for capture_id in batch["capture_ids"]:
        try:
            original = lib.read_original(owner, capture_id)
            match = _book_for_cover(root, original) or _book_for_page(root, original)
        except Exception:
            match = None
        if match:
            break
    if match:
        isbn, epub = match
        try:
            title = _catalog(lib, owner, isbn, epub, batch)
        except LibrarianError as error:
            if error.code != "CONTEXT_CONFLICT":
                raise
            match = None
    if match:
        batch["isbn"] = isbn
        epub_hash = hashlib.sha256(epub.read_bytes()).hexdigest()[:16]
        version = f"bookscan-segment-v1:{processor_fingerprint()}:{isbn}:{epub_hash}"
        work_root = root / "bookscan-runs" / hashlib.sha256(owner.encode()).hexdigest()[:16]
        extractor = bookscan_extractor(epub, work_root=work_root)
        pending_review_ids = _latest_pending_review_ids(
            _current(lib, owner, "ProcessingRun"))
    else:
        title = "待确认书籍"
        version = f"bookscan-segment-v1:{processor_fingerprint()}:no-epub"
        work_root = root / "bookscan-runs" / hashlib.sha256(owner.encode()).hexdigest()[:16]
        extractor = bookscan_extractor(None, work_root=work_root)
        pending_review_ids = set()
    for capture_id in batch["capture_ids"]:
        try:
            auto_reconcile_fully_reviewed(lib, owner, capture_id)
        except LibrarianError as error:
            if error.code not in {"RECONCILIATION_REQUIRED", "REVISION_CONFLICT"}:
                raise
    if match:
        _repair_visible_header_pages(lib, owner, batch["capture_ids"])
    latest_runs = {run["capture_id"]: run for run in
                   _current(lib, owner, "ProcessingRun")}
    pending_review_ids = _latest_pending_review_ids(list(latest_runs.values()))
    runs = [run for run in _current(lib, owner, "ProcessingRun")
            if run["capture_id"] in batch["capture_ids"] and
            run["extractor_version"] == version and
            run["outcome"] in {"success", "partial"}]
    revised_notice = any((root / "notifications").glob(f"{batch['id']}-revision*.json"))
    unbound = any(trace["work_id"] is None for trace in _current(lib, owner, "ReadingTrace")
                  if trace["status"] == "active" and
                  trace["source"].get("capture_id") in batch["capture_ids"])
    if _notified_batch_is_current(batch, notified=notified,
                                 revised_notice=revised_notice, unbound=unbound,
                                 matching_runs=runs, latest_runs=latest_runs,
                                 pending_review_ids=pending_review_ids):
        existing = [trace for trace in _current(lib, owner, "ReadingTrace")
                    if trace["status"] == "active" and
                    trace["source"].get("capture_id") in batch["capture_ids"]]
        if vault:
            _refresh_generated_note(vault, batch, title, existing, existing,
                                    _capture_received_times(lib, owner,
                                        {trace["source"]["capture_id"] for trace in existing}))
            note = _consolidate_generated_note(lib, owner, title, vault)
            _notify_correction(root, batch, note, len(existing),
                               unresolved=sum(trace["location"]["page"] is None
                                              for trace in existing),
                               revision_key=_review_digest(existing))
        unresolved = sum(trace["location"]["page"] is None for trace in existing)
        return ({"batch_id": batch["id"], "status": "partial",
                 "traces": len(existing), "unresolved_pages": unresolved,
                 "note": str(vault / "2Area" / "40 学习与阅读" / "阅读笔记" / f"{title}.md")
                 if vault else None} if unresolved else
                {"batch_id": batch["id"], "status": "unchanged"})
    snapshot = root / "reconciliations" / f"{batch['id']}.json"
    if notified:
        if snapshot.exists():
            old_traces = json.loads(snapshot.read_text(encoding="utf-8"))
        else:
            old_traces = [trace for trace in _current(lib, owner, "ReadingTrace")
                          if trace["status"] == "active" and
                          trace["source"].get("capture_id") in batch["capture_ids"]]
            _atomic_write(snapshot, json.dumps(old_traces, ensure_ascii=False).encode())
    extraction_issues = []
    for capture_id in batch["capture_ids"]:
        if match:
            try:
                bind_fingerprint_context(lib, owner, capture_id)
            except LibrarianError as error:
                extraction_issues.append({"capture_id": capture_id, "code": error.code})
        try:
            selected_version = version
            selected_extractor = extractor
            process_capture(lib, owner, capture_id, selected_extractor,
                            extractor_version=selected_version)
        except LibrarianError as error:
            if error.code == "RECONCILIATION_REQUIRED":
                extraction_issues.append({"capture_id": capture_id,
                                          "code": error.code})
            elif error.code in {"EXTRACTION_SCHEMA_INVALID", "EXTRACTOR_UNAVAILABLE"}:
                extraction_issues.append({"capture_id": capture_id,
                                          "code": error.code})
            else:
                raise
    traces = [trace for trace in _current(lib, owner, "ReadingTrace")
              if trace["status"] == "active" and
              trace["source"].get("capture_id") in batch["capture_ids"]]
    if not match:
        work_ids = {trace["work_id"] for trace in traces if trace["work_id"]}
        if len(work_ids) == 1:
            title = lib.get(owner, "Work", next(iter(work_ids)))["title"]
    if not vault:
        unresolved = sum(trace["location"]["page"] is None for trace in traces)
        return {"batch_id": batch["id"],
                "status": "partial" if not match or unresolved or not traces or extraction_issues else "processed",
                "traces": len(traces), "unresolved_pages": unresolved,
                "vault_status": "unconfigured",
                "issues": (["NEEDS_BOOK_RESOLUTION"] if not match else []) +
                          (["NEEDS_PAGE_RESOLUTION"] if unresolved else []) +
                          (["NO_MARKS"] if not traces else []) + extraction_issues}
    if not traces:
        return {"batch_id": batch["id"], "status": "partial", "traces": 0,
                "code": "NO_MARKS"}
    if title == "待确认书籍":
        return {"batch_id": batch["id"], "status": "partial", "traces": len(traces),
                "code": "NEEDS_BOOK_RESOLUTION"}
    if notified:
        note = _refresh_generated_note(vault, batch, title, old_traces, traces,
                                       _capture_received_times(lib, owner,
                                           {trace["source"]["capture_id"] for trace in traces}))
        note = _consolidate_generated_note(lib, owner, title, vault)
        _notify_correction(root, batch, note, len(traces),
                           unresolved=sum(trace["location"]["page"] is None for trace in traces),
                           issues=len(extraction_issues),
                           revision_key=_review_digest(traces))
        snapshot.unlink(missing_ok=True)
    else:
        note = _export(lib, owner, batch, title, vault)
        note = _consolidate_generated_note(lib, owner, title, vault)
        _notify(root, batch, note, len(traces),
                unresolved=sum(trace["location"]["page"] is None for trace in traces),
                issues=len(extraction_issues))
    unresolved = sum(trace["location"]["page"] is None for trace in traces)
    return {"batch_id": batch["id"],
            "status": "partial" if unresolved or extraction_issues else "processed",
            "traces": len(traces), "unresolved_pages": unresolved,
            "issues": extraction_issues, "note": str(note)}


def run(root: Path, vault: Path | None, owner: str, *,
        vision_model: str = "zai/glm-5.3-flash",
        koodo: tuple[str, Path, Path] | None = None,
        weread: tuple[str, Path, list[str]] | None = None,
        physical_only: bool = False, digital_only: bool = False) -> list[dict]:
    if physical_only and digital_only:
        raise ValueError("worker modes are mutually exclusive")
    root.mkdir(parents=True, exist_ok=True)
    results = []
    if not digital_only:
        with (root / "physical-worker.lock").open("w") as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                results.append({"source": "physical", "status": "already_running"})
            else:
                with Library(root) as lib:
                    _repair_legacy_auto_affinity(lib, owner)
                    _repair_trace_index_best_effort(lib, owner)
                    results.extend(_refresh_generated_notes(lib, owner, vault))
                    retry_fingerprint = _retry_fingerprint(root, vision_model)
                    for batch in _processing_batches(_current(lib, owner, "CaptureBatch")):
                        if batch["origin"]["transport"] != "feishu":
                            continue
                        newest = max((lib.get(owner, "PageCapture", capture_id)["received_at"]
                                      for capture_id in batch["capture_ids"]),
                                     default=batch["received_at"])
                        if (datetime.fromisoformat(_now()) -
                                datetime.fromisoformat(newest)).total_seconds() < 45:
                            continue
                        status_file = root / "batch-status" / f"{batch['id']}.json"
                        now = _now()
                        due, previous_attempts = _retry_due(status_file, now,
                                                            retry_fingerprint)
                        if not due:
                            continue
                        try:
                            outcome = _process_batch(lib, root, vault, owner, batch, vision_model)
                            if outcome["status"] == "unchanged":
                                traces = [trace for trace in _current(lib, owner, "ReadingTrace")
                                          if trace["status"] == "active" and
                                          trace["source"].get("capture_id") in batch["capture_ids"]]
                                current = {"batch_id": batch["id"], "status": "processed",
                                           "traces": len(traces), "unresolved_pages": 0,
                                           "issues": []}
                                try:
                                    previous = json.loads(status_file.read_text(encoding="utf-8"))
                                except (OSError, ValueError, TypeError):
                                    previous = {}
                                if previous.get("note"):
                                    current["note"] = previous["note"]
                                if any(previous.get(key) != value for key, value in current.items()):
                                    _atomic_write(status_file, json.dumps(
                                        _status_with_retry(current, 0, _now(),
                                                           retry_fingerprint)).encode())
                            else:
                                _atomic_write(status_file, json.dumps(
                                    _status_with_retry(outcome, previous_attempts, _now(),
                                                       retry_fingerprint)).encode())
                                results.append(outcome)
                        except Exception as error:
                            outcome = {"batch_id": batch["id"], "status": "error",
                                       "code": error.code if isinstance(error, LibrarianError) else "WORKER_FAILED"}
                            _atomic_write(status_file, json.dumps(
                                _status_with_retry(outcome, previous_attempts, _now(),
                                                   retry_fingerprint)).encode())
                            results.append(outcome)
    if not physical_only and (koodo or weread):
        with (root / "digital-worker.lock").open("w") as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                results.append({"source": "digital", "status": "already_running"})
            else:
                with Library(root) as lib:
                    results.extend(_sync_digital(lib, root, owner, koodo=koodo, weread=weread))
    return results


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--vault", type=Path)
    parser.add_argument("--owner", required=True)
    parser.add_argument("--vision-model", default="zai/glm-5.3-flash")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--physical-only", action="store_true")
    mode.add_argument("--digital-only", action="store_true")
    parser.add_argument("--koodo-source-id")
    parser.add_argument("--koodo-books-db", type=Path)
    parser.add_argument("--koodo-notes-db", type=Path)
    parser.add_argument("--weread-source-id")
    parser.add_argument("--weread-plugin-data", type=Path)
    parser.add_argument("--weread-book-id", action="append", default=[])
    args = parser.parse_args()
    koodo_args = (args.koodo_source_id, args.koodo_books_db, args.koodo_notes_db)
    weread_args = (args.weread_source_id, args.weread_plugin_data, args.weread_book_id)
    if any(value is not None for value in koodo_args) and not all(koodo_args):
        parser.error("Koodo source ID and both database paths are required together")
    if (any(value is not None for value in weread_args[:2]) or weread_args[2]) and not all(weread_args):
        parser.error("WeRead source ID, plugin data and book IDs are required together")
    print(json.dumps(run(args.root, args.vault, args.owner, vision_model=args.vision_model,
                         koodo=koodo_args if all(koodo_args) else None,
                         weread=weread_args if all(weread_args) else None,
                         physical_only=args.physical_only, digital_only=args.digital_only),
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
