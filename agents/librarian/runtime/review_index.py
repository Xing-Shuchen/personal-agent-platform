"""Generate a private, offline index of current Bookscan review pages."""
from __future__ import annotations

import argparse
import html
import json
import os
from pathlib import Path

from .store import Library


def build_index(root: Path, owner: str) -> Path:
    root = root.resolve()
    target = root / "review" / "index.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    entries_by_capture = {}
    with Library(root) as lib:
        runs = {run["id"]: run for row in lib.db.execute(
            "SELECT body FROM records WHERE owner_id=? AND model='ProcessingRun' "
            "AND current=1", (owner,)) if (run := json.loads(row["body"]))}
        rows = lib.db.execute("SELECT body FROM records WHERE owner_id=? AND "
                              "model='PageObservation' AND current=1", (owner,))
        for row in rows:
            observation = json.loads(row["body"])
            try:
                report = json.loads(lib._read_object(observation["raw_output_asset"]))
                run = report["run"]
                run_id = run["run_id"]
                output_dir = Path(run["config"]["output_dir"]).resolve()
                review = (output_dir / run_id / "review.html").resolve()
                review.relative_to(root / "bookscan-runs")
                if not review.is_file():
                    continue
                page = report["pages"][0]
                number = page["page_number"]
                label = number["resolved_value"] or number["observed_label"] or "待核对"
                processing = runs[observation["processing_run_id"]]
                entry = {"capture_id": observation["capture_id"],
                         "page": label,
                         "groups": len(report["groups"]),
                         "annotations": len(report["annotations"]),
                         "candidates": len(report["review_candidates"]),
                         "failures": len(report["failures"]),
                         "run_active": processing["outcome"] in {"success", "partial"},
                         "run_created_at": processing["created_at"],
                         "url": os.path.relpath(review, target.parent)}
                previous = entries_by_capture.get(observation["capture_id"])
                if previous is None or (entry["run_active"], entry["run_created_at"]) > (
                        previous["run_active"], previous["run_created_at"]):
                    entries_by_capture[observation["capture_id"]] = entry
            except (KeyError, IndexError, ValueError, TypeError, OSError):
                continue
    entries = list(entries_by_capture.values())
    entries.sort(key=lambda item: (isinstance(item["page"], str),
                                   str(item["page"]).zfill(5), item["capture_id"]))
    parts = ["<!doctype html><html lang='zh'><meta charset='utf-8'>",
             "<title>Librarian · 纸书扫描复核</title>",
             "<style>body{font:16px system-ui;max-width:1000px;margin:auto;padding:24px;"
             "background:#f5f6f5;color:#202520}table{width:100%;border-collapse:collapse;"
             "background:#fff}th,td{text-align:left;padding:10px;border-bottom:1px solid #ddd}"
             "a{color:#175b77}small{color:#666}</style>",
             "<h1>纸书扫描复核</h1>",
             f"<p>当前 Bookscan 结果：{len(entries)} 张。逐页核对划线、批注和漏检；"
             "页面草稿保存在本机浏览器，可导出 JSON。</p>",
             "<table><thead><tr><th>页码</th><th>划线/角括号组</th>"
             "<th>批注</th><th>待核对候选</th><th>失败</th><th>操作</th></tr></thead><tbody>"]
    for entry in entries:
        escape = lambda value: html.escape(str(value), quote=True)
        parts.append("<tr>" + "".join(
            f"<td>{escape(entry[key])}</td>" for key in
            ("page", "groups", "annotations", "candidates", "failures")) +
            f"<td><a href='{escape(entry['url'])}'>打开复核页</a><br>"
            f"<small>{escape(entry['capture_id'])}</small></td></tr>")
    parts.extend(["</tbody></table>", "</html>"])
    temp = target.with_suffix(".html.tmp")
    temp.write_text("\n".join(parts), encoding="utf-8")
    temp.replace(target)
    return target


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--owner", required=True)
    args = parser.parse_args()
    print(build_index(args.root, args.owner))


if __name__ == "__main__":
    main()
