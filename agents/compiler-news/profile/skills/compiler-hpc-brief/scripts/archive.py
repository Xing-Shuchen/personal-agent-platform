#!/usr/bin/env python3
"""Archive one compiler briefing and maintain its Obsidian directory note."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import date, datetime
import fcntl
import json
import os
from pathlib import Path
import re
import tempfile
from zoneinfo import ZoneInfo

ARCHIVE_DIR = Path("2Area/41 新闻及事件/AI Compiler")
INDEX_NAME = "AI编译器简报目录.md"
TITLE = "AI 编译器与高性能计算软件栈简报"
FOOTER = "——回复条目主题，即可让 World Historian 开始长期追踪。"
START = "<!-- compiler-brief-index:start -->"
END = "<!-- compiler-brief-index:end -->"
BRIEF_NAME = re.compile(r"AI编译器简报-(\d{4}-\d{2}-\d{2})\.md")


def _today() -> str:
    return datetime.now(ZoneInfo("Asia/Shanghai")).date().isoformat()


def _day(value: str) -> str:
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError("brief date must be YYYY-MM-DD")
    return date.fromisoformat(value).isoformat()


def _folder(vault: Path, archive_dir: Path) -> Path:
    vault = vault.expanduser().resolve()
    if not vault.is_dir():
        raise ValueError("configured vault directory does not exist")
    folder = (vault / archive_dir).resolve()
    if archive_dir.is_absolute() or not folder.is_relative_to(vault):
        raise ValueError("archive directory must be relative to the configured vault")
    return folder


@contextmanager
def _locked(folder: Path):
    folder.mkdir(parents=True, exist_ok=True)
    # Lock the directory itself: concurrent runs need no extra file in the vault.
    descriptor = os.open(folder, os.O_RDONLY)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield
    finally:
        os.close(descriptor)


def _write_changed(path: Path, text: str) -> bool:
    if path.exists() and path.read_text(encoding="utf-8") == text:
        return False
    scratch = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         prefix=".compiler-brief-", delete=False) as stream:
            scratch = Path(stream.name)
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        if path.exists():
            scratch.chmod(path.stat().st_mode & 0o777)
        scratch.replace(path)
    finally:
        if scratch is not None:
            scratch.unlink(missing_ok=True)
    return True


def _frontmatter_date(text: str, key: str) -> str | None:
    front = re.match(r"\A---\n(.*?)\n---(?:\n|$)", text, re.S)
    match = re.search(rf"^{key}:\s*[\"']?(\d{{4}}-\d{{2}}-\d{{2}})[\"']?\s*$",
                      front[1], re.M) if front else None
    return _day(match[1]) if match else None


def render_brief(day: str, body: str, model: str, *, archived: str | None = None) -> str:
    day = _day(day)
    if not model.strip():
        raise ValueError("the actual run model is required")
    lines = body.strip().splitlines()
    expected = f"{TITLE}｜{day}"
    if not lines or lines[0].removeprefix("# ").strip() != expected:
        raise ValueError("brief heading must match the requested date")
    content = "\n".join(line for line in lines[1:] if line.strip() != FOOTER).strip()
    if not content:
        raise ValueError("brief content is empty")
    source = ("compiler-hpc-brief (PAP scheduled job, agent=compiler-news, "
              f"runner=OpenClaw Gateway, model={model.strip()})")
    return ("---\ntype: note\narea: world-historian\nkind: briefing-archive\n"
            f"source: {json.dumps(source, ensure_ascii=False)}\ndate: {day}\n"
            f"archived: {_day(archived or _today())}\n---\n\n# {expected}\n\n{content}\n")


def _index_content(folder: Path, *, extra: str | None = None) -> tuple[str, int]:
    names = {path.name for path in folder.glob("AI编译器简报-*.md") if path.is_file()}
    if extra:
        names.add(extra)
    briefs = []
    for name in sorted(names):
        match = BRIEF_NAME.fullmatch(name)
        if match:
            try:
                briefs.append((_day(match[1]), Path(name).stem))
            except ValueError:
                continue  # Files not named with a real date are not daily archives.
    block = "\n".join([
        START, f"共 **{len(briefs)}** 期，按简报日期排列。", "",
        *(f"- [[{stem}|{day}]]" for day, stem in briefs), END,
    ])
    index = folder / INDEX_NAME
    if not index.exists():
        today = _today()
        return ("---\ntype: note\narea: world-historian\nkind: briefing-index\n"
                f"status: active\ncreated: {today}\nupdated: {today}\n---\n\n"
                "# AI 编译器简报目录\n\n"
                "新简报归档后自动加入目录；同日更新保留一个入口。\n\n"
                f"{block}\n", len(briefs))
    original = index.read_text(encoding="utf-8")
    if START not in original and END not in original:
        updated = original.rstrip() + "\n\n" + block + "\n"
    else:
        if (original.count(START) != 1 or original.count(END) != 1
                or original.index(START) > original.index(END)):
            raise ValueError("brief index has invalid managed markers; repair them before archiving")
        left, right = original.index(START), original.index(END) + len(END)
        updated = original[:left] + block + original[right:]
    if updated != original:
        front = re.match(r"\A---\n(.*?)\n---(?:\n|$)", updated, re.S)
        if front:
            refreshed = re.sub(r"^updated:.*$", f"updated: {_today()}", front[0], flags=re.M)
            updated = refreshed + updated[front.end():]
    return updated, len(briefs)


def update_index(vault: Path, *, archive_dir: Path = ARCHIVE_DIR) -> dict:
    folder = _folder(vault, archive_dir)
    with _locked(folder):
        text, count = _index_content(folder)
        changed = _write_changed(folder / INDEX_NAME, text)
    return {"index": str(folder / INDEX_NAME), "brief_count": count, "index_updated": changed}


def archive_brief(vault: Path, day: str, body: str, model: str, *,
                  archive_dir: Path = ARCHIVE_DIR) -> dict:
    day = _day(day)
    folder = _folder(vault, archive_dir)
    # Reject invalid input before creating any output directory.
    render_brief(day, body, model)
    with _locked(folder):
        target = folder / f"AI编译器简报-{day}.md"
        archived = _frontmatter_date(target.read_text(encoding="utf-8"), "archived") if target.exists() else None
        text = render_brief(day, body, model, archived=archived)
        # Validate and prepare the directory before saving the new briefing.
        index_text, count = _index_content(folder, extra=target.name)
        written = _write_changed(target, text)
        indexed = _write_changed(folder / INDEX_NAME, index_text)
    return {"brief": str(target), "brief_updated": written,
            "index": str(folder / INDEX_NAME), "index_updated": indexed, "brief_count": count}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for command in ("archive", "index"):
        sub = commands.add_parser(command)
        sub.add_argument("--vault", type=Path, default=os.environ.get("PAP_VAULT") or None)
        sub.add_argument("--archive-dir", type=Path, default=ARCHIVE_DIR)
        if command == "archive":
            sub.add_argument("--date", required=True)
            sub.add_argument("--body-file", type=Path, required=True)
            sub.add_argument("--model", required=True)
    args = parser.parse_args(argv)
    if not args.vault or not str(args.vault).strip():
        parser.error("set PAP_VAULT or pass --vault explicitly")
    try:
        if args.command == "archive":
            result = archive_brief(args.vault, args.date, args.body_file.read_text(encoding="utf-8"),
                                   args.model, archive_dir=args.archive_dir)
        else:
            result = update_index(args.vault, archive_dir=args.archive_dir)
    except (OSError, ValueError) as exc:
        parser.exit(1, f"archive failed: {exc}\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
