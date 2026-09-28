"""Recover and complete Feishu capture batches in the Librarian runtime.

The OpenClaw plugin starts this worker after intake and on Gateway startup.
It uses local OCR for printed text and photo marks, an owner-provided EPUB for
alignment, and writes an idempotent Obsidian review note before notifying.
"""
from __future__ import annotations

import argparse
import fcntl
import io
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as ET

from PIL import Image, ImageOps

from .ocr import ocr_extractor, openclaw_note_refiner
from .pipeline import process_capture
from .store import Library, LibrarianError, _now, _unknown_time


def _current(lib: Library, owner: str, model: str) -> list[dict]:
    rows = lib.db.execute("SELECT body FROM records WHERE owner_id=? AND model=? AND current=1",
                          (owner, model)).fetchall()
    return [json.loads(row["body"]) for row in rows]


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


def _catalog(lib: Library, owner: str, isbn: str, epub: Path, batch: dict) -> str:
    work_id, edition_id, instance_id = (f"work_{isbn}", f"edition_{isbn}", f"copy_{isbn}")
    metadata = _epub_metadata(epub)
    title = metadata.get("title", [isbn])[0].split("（", 1)[0].split("(", 1)[0].strip()
    common = {"schema_version": "0.1.0", "owner_id": owner,
              "created_at": _now(), "revision": 1, "supersedes_revision": None}
    known = {(item["object_type"], item["id"]) for model in ("Work", "Edition", "BookInstance")
             for item in _current(lib, owner, model)}
    if ("Work", work_id) not in known:
        lib.register(owner, {**common, "object_type": "Work", "id": work_id,
                             "title": title, "original_title": None,
                             "authors": [{"name": name, "entity_id": None}
                                         for name in metadata.get("creator", [])],
                             "identifiers": []})
    if ("Edition", edition_id) not in known:
        date = metadata.get("date", [""])[0]
        lib.register(owner, {**common, "object_type": "Edition", "id": edition_id,
                             "work_id": work_id, "edition_label": None,
                             "publisher": metadata.get("publisher", [None])[0],
                             "publication_year": int(date[:4]) if date[:4].isdigit() else None,
                             "isbn": {"isbn13": isbn, "isbn10": None},
                             "language": metadata.get("language", [None])[0],
                             "page_count": None, "volume_label": None})
    if ("BookInstance", instance_id) not in known:
        lib.register(owner, {**common, "object_type": "BookInstance", "id": instance_id,
                             "edition_id": edition_id, "medium": "physical",
                             "acquired_at": _unknown_time(), "ownership_status": "unknown",
                             "physical": {"qr_id": None, "shelf": None},
                             "reading_status": {"state": "unknown", "current_page": None,
                                                "progress_evidence_ref": None}})
    scope = (batch["origin"]["transport"], batch["origin"]["account_id"],
             batch["origin"]["conversation_id"])
    sessions = [item for item in _current(lib, owner, "ReadingSession")
                if item["book_instance_id"] == instance_id and item["status"] == "active"]
    session = sessions[0] if sessions else lib.start_session(owner, instance_id, scope=scope)
    with lib.transaction():
        for capture_id in batch["capture_ids"]:
            lib.db.execute("INSERT OR IGNORE INTO capture_context VALUES(?,?,?,?)",
                           (owner, capture_id, session["id"], "edition_fingerprint"))
    return title


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


def _export(lib: Library, owner: str, batch: dict, title: str, vault: Path) -> Path:
    folder = vault / "2Area" / "40 学习与阅读" / "阅读笔记"
    images = folder / "Attachments" / "Librarian" / batch["id"]
    note = folder / f"{title}.md"
    traces = [trace for trace in _current(lib, owner, "ReadingTrace")
              if trace["source"]["capture_id"] in batch["capture_ids"]]
    traces.sort(key=lambda item: (item["location"]["page"] or {}).get("number", 0))
    if not traces:
        raise LibrarianError("NO_MARKS", "no reading marks found in batch")
    for capture_id in batch["capture_ids"][1:]:
        image_path = images / f"{capture_id}.jpg"
        if image_path.exists():
            continue
        with Image.open(io.BytesIO(lib.read_original(owner, capture_id))) as source:
            image = ImageOps.exif_transpose(source).convert("RGB")
            image.thumbnail((1800, 1800))
            output = io.BytesIO()
            image.save(output, "JPEG", quality=82, optimize=True)
        _atomic_write(image_path, output.getvalue())
    lines = (["---", "type: reference", "area: reading", "status: review",
              f"created: {_now()[:10]}", f"updated: {_now()[:10]}", "---", "",
              f"# {title}", "", f"- ISBN: {batch.get('isbn', '待核对')}",
              "- 来源：飞书图书专员；正文依据 EPUB 对齐，划线与笔记位置依据照片。",
              "- 状态：待人工 review", ""] if not note.exists()
             else [f"## 新增照片 · {batch['id']}", ""])
    for trace in traces:
        page = trace["location"]["page"]
        label = page["label"] if page else "页码待核对"
        lines.extend([f"## 第 {label} 页 · {'、'.join(trace['trace_types'])}", "",
                      f"<!-- librarian-trace: {trace['id']} revision: {trace['revision']} -->"])
        printed = trace["content"]["printed_text"]["text"]
        annotation = trace["content"]["annotation"]["text"]
        if printed:
            lines.extend(["", "**画线**", "", printed])
        if annotation:
            lines.extend(["", "**手写笔记（待核对）**", "", annotation])
        lines.extend(["", f"![[Attachments/Librarian/{batch['id']}/{trace['source']['capture_id']}.jpg]]", ""])
    block = "\n".join(lines).rstrip() + "\n"
    if note.exists():
        old = note.read_text(encoding="utf-8")
        if f"<!-- librarian-batch: {batch['id']} -->" in old:
            return note
        block = old.rstrip() + "\n\n" + block
    block += f"\n<!-- librarian-batch: {batch['id']} -->\n"
    _atomic_write(note, block.encode("utf-8"))
    return note


def _notify(root: Path, batch: dict, note: Path, count: int) -> None:
    marker = root / "notifications" / f"{batch['id']}.json"
    if marker.exists():
        return
    message = (f"《{note.stem}》已完成照片识别、EPUB 对齐，并写入图书专员数据库和 Obsidian。"
               f"共识别 {count} 条画线/笔记。请在「2Area/40 学习与阅读/阅读笔记/{note.name}」review；"
               "手写文字标为待核对。")
    command = ["openclaw", "message", "send", "--channel", "feishu", "--account", "librarian",
               "--target", batch["origin"]["conversation_id"], "--message", message, "--json"]
    result = subprocess.run(command, capture_output=True, text=True, timeout=45)
    if result.returncode:
        raise RuntimeError("Feishu review notification failed")
    _atomic_write(marker, json.dumps({"batch_id": batch["id"], "sent_at": _now()}).encode())


def run(root: Path, vault: Path, owner: str) -> list[dict]:
    root.mkdir(parents=True, exist_ok=True)
    with (root / "worker.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        results = []
        with Library(root) as lib:
            for batch in _current(lib, owner, "CaptureBatch"):
                if batch["origin"]["transport"] != "feishu":
                    continue
                if (root / "notifications" / f"{batch['id']}.json").exists():
                    continue
                cover = lib.read_original(owner, batch["capture_ids"][0])
                match = _book_for_cover(root, cover)
                if not match:
                    continue
                isbn, epub = match
                title = _catalog(lib, owner, isbn, epub, batch)
                extractor = ocr_extractor(epub=epub, note_refiner=openclaw_note_refiner)
                batch["isbn"] = isbn
                for capture_id in batch["capture_ids"]:
                    process_capture(lib, owner, capture_id, extractor,
                                    extractor_version=f"rapidocr-epub-notes-v2:{isbn}")
                traces = [trace for trace in _current(lib, owner, "ReadingTrace")
                          if trace["source"]["capture_id"] in batch["capture_ids"]]
                if any(trace["location"]["page"] is None for trace in traces):
                    raise LibrarianError("NEEDS_PAGE_RESOLUTION", "a marked page lacks a visible page number")
                note = _export(lib, owner, batch, title, vault)
                _notify(root, batch, note, len(traces))
                results.append({"batch_id": batch["id"], "traces": len(traces),
                                "note": str(note)})
        return results


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--vault", type=Path, required=True)
    parser.add_argument("--owner", required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.root, args.vault, args.owner), ensure_ascii=False))


if __name__ == "__main__":
    main()
