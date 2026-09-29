"""Generate a private, offline index of current Bookscan review pages."""
from __future__ import annotations

import argparse
import html
import json
import os
import re
from pathlib import Path

from .handwriting_review import ACCEPTED, REJECTED
from .store import Library


def _bookscan_run_dir(root: Path, run: dict) -> Path:
    """Resolve a report within the current private root after a restore/move."""
    run_id = run["run_id"]
    if not isinstance(run_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", run_id):
        raise ValueError("invalid Bookscan run ID")
    allowed = (root / "bookscan-runs").resolve()
    configured = Path(run["config"]["output_dir"])
    candidate = (configured / run_id).resolve()
    if candidate.is_relative_to(allowed) and candidate.is_dir():
        return candidate
    matches = [path.resolve() for path in allowed.glob(f"*/run-*/output/{run_id}")
               if path.is_dir() and path.resolve().is_relative_to(allowed)]
    if len(matches) != 1:
        raise ValueError("Bookscan run not unique in current root")
    return matches[0]


def build_handwriting_index(root: Path, owner: str) -> Path:
    """Show only handwritten notes that the user needs to confirm."""
    root = root.resolve()
    target = root / "review" / "handwriting.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    entries = []
    with Library(root) as lib:
        for row in lib.db.execute("SELECT body FROM records WHERE owner_id=? AND "
                                  "model='ReadingTrace' AND current=1", (owner,)):
            trace = json.loads(row["body"])
            ids = trace.get("source", {}).get("detection_ids", [])
            if (trace.get("medium") != "physical" or
                    "margin_note" not in trace.get("trace_types", []) or
                    len(ids) != 1 or not ids[0].startswith("bookscan_note_") or
                    (trace["status"] != "active" and
                     trace["review"].get("reason") != REJECTED)):
                continue
            try:
                index = int(ids[0][len("bookscan_note_"):])
                observation = lib.get(owner, "PageObservation", trace["source"]["observation_id"])
                report = json.loads(lib._read_object(observation["raw_output_asset"]))
                annotation = report["annotations"][index]
                run = report["run"]
                image = (_bookscan_run_dir(root, run) / "annotations" /
                         f"{annotation['annotation_id']}.png").resolve()
                image.relative_to(root / "bookscan-runs")
                if not image.is_file():
                    continue
            except (KeyError, IndexError, ValueError, TypeError, OSError):
                continue
            reason = trace["review"].get("reason")
            page = (trace.get("location", {}).get("page") or {}).get("number")
            entries.append({"trace_id": trace["id"], "revision": trace["revision"],
                            "page": page, "image": os.path.relpath(image, target.parent),
                            "original": annotation.get("ocr_raw") or "",
                            "text": trace["content"]["annotation"]["text"] or "",
                            "status": "已确认" if reason == ACCEPTED else
                                      "已排除" if reason == REJECTED else "待复核"})
    entries.sort(key=lambda item: (item["page"] is None, item["page"] or 0,
                                   item["trace_id"]))
    escape = lambda value: html.escape(str(value), quote=True)
    pending = sum(item["status"] == "待复核" for item in entries)
    parts = ["<!doctype html><html lang='zh'><meta charset='utf-8'>",
             "<meta name='viewport' content='width=device-width,initial-scale=1'>",
             "<title>Librarian · 手写笔记复核</title>",
             "<style>body{font:16px system-ui;max-width:860px;margin:auto;padding:24px;"
             "background:#f5f6f5;color:#202520}article{background:white;padding:18px;"
             "margin:18px 0;border:1px solid #ddd;border-radius:8px}img{max-width:100%;"
             "max-height:430px;object-fit:contain}textarea{display:block;width:100%;"
             "min-height:90px;box-sizing:border-box;margin:12px 0;font:inherit}"
             "button{font:inherit;padding:8px 14px;margin-right:8px}small{color:#666}"
             "a{color:#175b77}</style>",
             "<h1>手写笔记复核</h1>",
             f"<p>共 {len(entries)} 条，待复核 {pending} 条。只需确认手写内容；"
             "画线文字按现有结果保留。<a href='index.html'>返回全部扫描</a></p>"]
    for item in entries:
        parts.extend([f"<article data-trace-id='{escape(item['trace_id'])}' "
                      f"data-revision='{item['revision']}'>",
                      f"<h2>第 {escape(item['page'] or '未知')} 页 · "
                      f"<span class='state'>{escape(item['status'])}</span></h2>",
                      f"<a href='{escape(item['image'])}' target='_blank'>"
                      f"<img src='{escape(item['image'])}' alt='手写笔记裁片'></a>",
                      f"<p><small>机器初稿：{escape(item['original'])}</small></p>",
                      f"<textarea aria-label='手写笔记文字'>{escape(item['text'])}</textarea>",
                      "<button type='button' data-decision='accepted'>确认文字</button>",
                      "<button type='button' data-decision='rejected'>误检，排除</button>",
                      "<span class='result' role='status'></span></article>"])
    parts.append("""<script>
document.querySelectorAll('article').forEach(card => {
  card.querySelectorAll('button').forEach(button => button.addEventListener('click', async () => {
    const result = card.querySelector('.result');
    const decision = button.dataset.decision;
    const text = decision === 'accepted' ? card.querySelector('textarea').value.trim() : '';
    if (decision === 'accepted' && !text) { result.textContent = '请填写手写文字'; return; }
    card.querySelectorAll('button').forEach(item => item.disabled = true);
    result.textContent = '正在入库…';
    try {
      const response = await fetch('/api/handwriting-review', {
        method: 'POST', headers: {'Content-Type':'application/json'},
        body: JSON.stringify({trace_id: card.dataset.traceId,
          expected_revision: Number(card.dataset.revision), decision, text})
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.message || data.code || '提交失败');
      card.dataset.revision = String(data.revision);
      card.querySelector('.state').textContent = decision === 'accepted' ? '已确认' : '已排除';
      result.textContent = (data.vault_status === 'updated' ? '已入库并刷新 Vault' :
        '已入库；Vault 状态：' + data.vault_status) +
        (data.review_page_status === 'review_required' ? '；复核页待重建' : '');
    } catch (error) { result.textContent = String(error.message || error); }
    finally { card.querySelectorAll('button').forEach(item => item.disabled = false); }
  }));
});
</script></html>""")
    temp = target.with_suffix(".html.tmp")
    temp.write_text("\n".join(parts), encoding="utf-8")
    temp.replace(target)
    return target


def build_index(root: Path, owner: str) -> Path:
    root = root.resolve()
    target = root / "review" / "index.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    entries_by_capture = {}
    with Library(root) as lib:
        runs = {run["id"]: run for row in lib.db.execute(
            "SELECT body FROM records WHERE owner_id=? AND model='ProcessingRun' "
            "AND current=1", (owner,)) if (run := json.loads(row["body"]))}
        reviewed = {run["capture_id"] for run in runs.values()
                    if run["extractor_version"].startswith("bookscan-human-review-v1:")
                    and run["outcome"] in {"success", "partial"}}
        rows = lib.db.execute("SELECT body FROM records WHERE owner_id=? AND "
                              "model='PageObservation' AND current=1", (owner,))
        for row in rows:
            observation = json.loads(row["body"])
            try:
                report = json.loads(lib._read_object(observation["raw_output_asset"]))
                run = report["run"]
                run_id = run["run_id"]
                review = (_bookscan_run_dir(root, run) / "review.html").resolve()
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
                         "review_status": "已入库" if observation["capture_id"] in reviewed
                                          else "待复核",
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
             f"<p><a href='handwriting.html'>只复核手写笔记</a>。"
             f"当前 Bookscan 结果：{len(entries)} 张；"
             f"已入库复核：{sum(item['review_status'] == '已入库' for item in entries)} 张。"
             "完整逐页复核页仍可查看扫描；当前只要求核对手写笔记。</p>",
             "<table><thead><tr><th>页码</th><th>状态</th><th>划线/角括号组</th>"
             "<th>批注</th><th>待核对候选</th><th>失败</th><th>操作</th></tr></thead><tbody>"]
    for entry in entries:
        escape = lambda value: html.escape(str(value), quote=True)
        parts.append("<tr>" + "".join(
            f"<td>{escape(entry[key])}</td>" for key in
            ("page", "review_status", "groups", "annotations", "candidates", "failures")) +
            f"<td><a href='{escape(entry['url'])}'>打开复核页</a><br>"
            f"<small>{escape(entry['capture_id'])}</small></td></tr>")
    parts.extend(["</tbody></table>", "</html>"])
    temp = target.with_suffix(".html.tmp")
    temp.write_text("\n".join(parts), encoding="utf-8")
    temp.replace(target)
    build_handwriting_index(root, owner)
    return target


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--owner", required=True)
    args = parser.parse_args()
    print(build_index(args.root, args.owner))


if __name__ == "__main__":
    main()
