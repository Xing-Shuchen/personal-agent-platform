#!/usr/bin/env python3
"""Invoke the local one-page FB2080E CLI for an inclusive book page range."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time
import unicodedata

SKILL_DIR = Path(__file__).resolve().parent.parent


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def positive_page(value: str) -> int:
    try:
        page = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("页码必须是正整数") from exc
    if page < 1:
        raise argparse.ArgumentTypeError("页码必须大于 0")
    return page


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="按闭区间页码调用 FB2080E 单张 CLI；每张完成后留出人工翻页时间。",
        epilog=(
            "示例：--book '书名' --from-page 12 --to-page 18 --dry-run；"
            "确认第一页就位后去掉 --dry-run 启动。默认 300 dpi Color、翻页 4 秒。"
        ),
    )
    p.add_argument("--book", required=True, help="书名，只用于本地会话元数据和目录名")
    p.add_argument("--from-page", type=positive_page, required=True, help="起始页，包含")
    p.add_argument("--to-page", type=positive_page, required=True, help="结束页，包含")
    p.add_argument("--dpi", type=int, default=300, help="每页 DPI，默认 300")
    p.add_argument("--mode", choices=("Color", "Gray", "Lineart", "Dithered"), default="Color", help="每页扫描模式，默认 Color")
    p.add_argument("--delay-seconds", type=float, default=4.0, help="前一页完成后供人工翻页的秒数，默认 4")
    p.add_argument("--output-parent", type=Path, help="会话目录的父目录，默认 PAP_ROOT/var/scans/books")
    p.add_argument("--dry-run", action="store_true", help="只显示计划，不访问设备或创建文件")
    return p


def resolve_root() -> Path:
    candidates = []
    if os.environ.get("PAP_ROOT"):
        candidates.append(Path(os.environ["PAP_ROOT"]))
    local_root = SKILL_DIR / "local-root.txt"
    if local_root.is_file():
        candidates.append(Path(local_root.read_text(encoding="utf-8").strip()))
    candidates.extend((SKILL_DIR.parent.parent, Path.cwd(), *Path.cwd().parents))
    for candidate in candidates:
        root = candidate.expanduser().resolve()
        if (root / "tools/scanners/fb2080e-scan").is_file():
            return root
    raise FileNotFoundError("找不到 PAP_ROOT/tools/scanners/fb2080e-scan；请设置 PAP_ROOT。")


def safe_name(title: str) -> str:
    name = unicodedata.normalize("NFKC", title).strip()
    name = re.sub(r'[\\/\x00-\x1f<>:"|?*]+', "_", name)
    name = re.sub(r"\s+", "_", name).strip(" ._")
    return name[:60] or "book"


def save_manifest(path: Path, manifest: dict) -> None:
    temporary = path.with_suffix(".json.part")
    temporary.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def main() -> int:
    args = parser().parse_args()
    title = args.book.strip()
    if not title:
        print("书名不能为空。", file=sys.stderr)
        return 2
    if args.to_page < args.from_page:
        print("结束页不能小于起始页。", file=sys.stderr)
        return 2
    if not 75 <= args.dpi <= 600:
        print("DPI 必须在 75–600 之间。", file=sys.stderr)
        return 2
    if not 1 <= args.delay_seconds <= 600:
        print("翻页等待必须在 1–600 秒之间。", file=sys.stderr)
        return 2
    try:
        root = resolve_root()
    except FileNotFoundError as exc:
        print(exc, file=sys.stderr)
        return 2
    cli = root / "tools/scanners/fb2080e-scan"
    parent = (args.output_parent or root / "var/scans/books").expanduser().resolve()
    page_count = args.to_page - args.from_page + 1
    print(f"书名：《{title}》；页码：{args.from_page}–{args.to_page}（共 {page_count} 页，含两端）")
    print(f"参数：{args.dpi} dpi、{args.mode}；每页后等待 {args.delay_seconds:g} 秒供人工翻页。")
    print(f"输出父目录：{parent}")
    if args.dry_run:
        print(f"计划文件：page-{args.from_page:04d}.tif … page-{args.to_page:04d}.tif")
        print("dry-run：未访问设备，未创建文件。")
        return 0

    parent.mkdir(parents=True, exist_ok=True)
    prefix = f"{safe_name(title)}-p{args.from_page:04d}-{args.to_page:04d}-"
    session = Path(tempfile.mkdtemp(prefix=prefix, dir=parent))
    manifest_path = session / "session.json"
    manifest = {
        "book": title,
        "from_page": args.from_page,
        "to_page": args.to_page,
        "dpi": args.dpi,
        "mode": args.mode,
        "delay_seconds": args.delay_seconds,
        "started_utc": now(),
        "status": "running",
        "completed_pages": [],
        "failed_page": None,
    }
    save_manifest(manifest_path, manifest)
    print(f"会话目录：{session}", flush=True)
    environment = os.environ.copy()
    environment["PAP_ROOT"] = str(root)
    try:
        preflight = subprocess.run([str(cli), "--list-devices"], env=environment,
                                   capture_output=True, text=True, check=False)
        device_names = [line.strip() for line in preflight.stdout.splitlines() if line.strip()]
        if preflight.returncode != 0 or len(device_names) != 1:
            manifest["status"] = "device_unavailable"
            save_manifest(manifest_path, manifest)
            print(f"扫描仪不可用或不唯一（发现 {len(device_names)} 台），未启动扫描。", file=sys.stderr)
            return 1
        for page in range(args.from_page, args.to_page + 1):
            output = session / f"page-{page:04d}.tif"
            print(f"开始扫描第 {page} 页。", flush=True)
            command = [str(cli), "--dpi", str(args.dpi), "--mode", args.mode,
                       "--output", str(output)]
            result = subprocess.run(command, env=environment, check=False)
            if result.returncode != 0 or not output.is_file():
                manifest["status"] = "failed"
                manifest["failed_page"] = page
                manifest["failed_exit_status"] = result.returncode
                save_manifest(manifest_path, manifest)
                print(f"第 {page} 页失败，已停止。日志及完成页：{session}", file=sys.stderr)
                return 1
            manifest["completed_pages"].append(page)
            save_manifest(manifest_path, manifest)
            if page < args.to_page:
                print(f"第 {page} 页完成。请翻到第 {page + 1} 页；"
                      f"{args.delay_seconds:g} 秒后自动开始。Ctrl+C 可取消。", flush=True)
                time.sleep(args.delay_seconds)
    except KeyboardInterrupt:
        manifest["status"] = "interrupted"
        save_manifest(manifest_path, manifest)
        print(f"\n已中断；完成页保留在 {session}", file=sys.stderr)
        return 130
    manifest["status"] = "complete"
    manifest["finished_utc"] = now()
    save_manifest(manifest_path, manifest)
    print(f"完成 {page_count} 页：{session}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
