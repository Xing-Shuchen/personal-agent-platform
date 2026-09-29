"""Self-contained offline review page generated from immutable machine JSONL."""
from __future__ import annotations

import html
import json
import os
from collections import Counter, defaultdict
from pathlib import Path


def _rows(path: Path) -> list[dict]:
    return [json.loads(s) for s in path.read_text(encoding="utf-8").splitlines() if s]


def _e(value: object) -> str:
    return html.escape("" if value is None else str(value))


REVIEW_SCRIPT = r"""
const key = 'bookscan-review:' + runId;
let saved = {};
try { saved = JSON.parse(localStorage.getItem(key) || '{}'); } catch (_) {}
const pages = [...document.querySelectorAll('.page-review')];
const notes = [...document.querySelectorAll('textarea[data-annotation-id]')];
const persist = () => localStorage.setItem(key, JSON.stringify(saved));
function download(name, content, type) {
  const blob = new Blob([content], {type});
  const anchor = document.createElement('a');
  anchor.href = URL.createObjectURL(blob);
  anchor.download = name;
  anchor.click();
  setTimeout(() => URL.revokeObjectURL(anchor.href), 1000);
}
function renderMissing(page) {
  const pageId = page.dataset.pageId;
  const target = page.querySelector('.missing-lines');
  target.replaceChildren();
  (saved[pageId].missing || []).forEach((item, index) => {
    const row = document.createElement('div');
    row.className = 'review-row';
    const box = document.createElement('input');
    box.type = 'text'; box.value = item.bbox.join(',');
    box.setAttribute('aria-label', '原图坐标 x1,y1,x2,y2');
    box.addEventListener('change', () => {
      const values = box.value.split(',').map(Number);
      if (values.length !== 4 || values.some(x => !Number.isFinite(x)) ||
          values[0] >= values[2] || values[1] >= values[3] ||
          values[0] < 0 || values[1] < 0 ||
          values[2] > Number(page.dataset.sourceWidth) ||
          values[3] > Number(page.dataset.sourceHeight)) {
        alert('坐标需要是原图内的 x1,y1,x2,y2，且右下角大于左上角。');
        box.value = item.bbox.join(','); return;
      }
      item.bbox = values.map(Math.round); persist(); drawBoxes(page);
    });
    const text = document.createElement('textarea');
    text.placeholder = '照片可见整行文字；未转录可留空';
    text.value = item.text || '';
    text.addEventListener('input', () => { item.text = text.value; persist(); });
    const remove = document.createElement('button');
    remove.type = 'button'; remove.textContent = '删除';
    remove.addEventListener('click', () => {
      saved[pageId].missing.splice(index, 1); persist(); renderMissing(page);
    });
    row.append('原图框 ', box, ' 文字 ', text, remove);
    target.append(row);
  });
  drawBoxes(page);
}
function drawBoxes(page) {
  const image = page.querySelector('.source-wrap img');
  const canvas = page.querySelector('canvas');
  if (!image.complete || !image.naturalWidth || !image.clientWidth) return;
  canvas.width = image.clientWidth; canvas.height = image.clientHeight;
  const ctx = canvas.getContext('2d');
  ctx.strokeStyle = '#d00000'; ctx.lineWidth = 2;
  const sx = canvas.width / image.naturalWidth;
  const sy = canvas.height / image.naturalHeight;
  (saved[page.dataset.pageId].missing || []).forEach(item => {
    const [x1,y1,x2,y2] = item.bbox;
    ctx.strokeRect(x1*sx, y1*sy, (x2-x1)*sx, (y2-y1)*sy);
  });
}
for (const page of pages) {
  const pageId = page.dataset.pageId;
  saved[pageId] ||= {lines:{}, missing:[], complete:false, pageNumber:''};
  const state = saved[pageId];
  const number = page.querySelector('.truth-page-number');
  number.value = state.pageNumber ?? '';
  number.addEventListener('input', () => { state.pageNumber = number.value; persist(); });
  const complete = page.querySelector('.page-complete');
  complete.checked = !!state.complete;
  complete.addEventListener('change', () => {
    state.complete = complete.checked; persist(); updateProgress();
  });
  page.querySelectorAll('.review-row[data-line-id]').forEach(row => {
    const id = row.dataset.lineId;
    const decision = row.querySelector('.line-decision');
    const text = row.querySelector('.line-text');
    if (state.lines[id]) {
      decision.value = state.lines[id].decision || '';
      text.value = state.lines[id].text ?? text.value;
    }
    const saveLine = () => {
      state.lines[id] = {decision:decision.value, text:text.value};
      persist(); updateProgress();
    };
    decision.addEventListener('change', saveLine);
    text.addEventListener('input', saveLine);
  });
  page.querySelector('.add-missing').addEventListener('click', () => {
    state.missing.push({bbox:[0,0,1,1],text:''});
    persist(); renderMissing(page);
  });
  const image = page.querySelector('.source-wrap img');
  const canvas = page.querySelector('canvas');
  image.addEventListener('load', () => drawBoxes(page));
  page.addEventListener('toggle', () => drawBoxes(page));
  let start = null;
  canvas.addEventListener('pointerdown', event => {
    const rect = canvas.getBoundingClientRect();
    start = [event.clientX-rect.left, event.clientY-rect.top];
    canvas.setPointerCapture(event.pointerId);
  });
  canvas.addEventListener('pointerup', event => {
    if (!start || !image.naturalWidth) return;
    const rect = canvas.getBoundingClientRect();
    const end = [event.clientX-rect.left, event.clientY-rect.top];
    const sx = image.naturalWidth / rect.width;
    const sy = image.naturalHeight / rect.height;
    const box = [Math.round(Math.min(start[0],end[0])*sx),
                 Math.round(Math.min(start[1],end[1])*sy),
                 Math.round(Math.max(start[0],end[0])*sx),
                 Math.round(Math.max(start[1],end[1])*sy)];
    start = null;
    if (box[2]-box[0] < 5 || box[3]-box[1] < 5) return;
    state.missing.push({bbox:box,text:''}); persist(); renderMissing(page);
  });
  renderMissing(page);
}
saved.groups ||= {};
document.querySelectorAll('article[data-group-id]').forEach(article => {
  const id = article.dataset.groupId;
  const verdict = article.querySelector('.group-decision');
  const text = article.querySelector('.group-text');
  if (saved.groups[id]) {
    verdict.value = saved.groups[id].decision || '';
    text.value = saved.groups[id].text || '';
  }
  const saveGroup = () => {
    saved.groups[id] = {decision:verdict.value, text:text.value}; persist();
  };
  verdict.addEventListener('change', saveGroup);
  text.addEventListener('input', saveGroup);
});
saved.annotations ||= {};
for (const field of notes) {
  field.value = saved.annotations[field.dataset.annotationId] || '';
  field.addEventListener('input', () => {
    saved.annotations[field.dataset.annotationId] = field.value; persist();
  });
}
function updateProgress() {
  const completed = pages.filter(page => saved[page.dataset.pageId].complete).length;
  document.getElementById('review-progress').textContent =
    `已核验 ${completed}/${pages.length} 页；完整真值仅在所有页面和行均确认后导出。`;
}
updateProgress();
document.getElementById('download-decisions').onclick = () =>
  download('review-decisions.json', JSON.stringify({run_id:runId,pages:saved},null,2), 'application/json');
document.getElementById('import-decisions').addEventListener('change', async event => {
  const file = event.target.files[0];
  if (!file) return;
  try {
    const imported = JSON.parse(await file.text());
    if (imported.run_id !== runId || !imported.pages || typeof imported.pages !== 'object')
      throw new Error('运行 ID 不匹配或文件格式错误');
    localStorage.setItem(key, JSON.stringify(imported.pages));
    location.reload();
  } catch (error) { alert(error.message); }
});
document.getElementById('download-annotations').onclick = () => {
  const rows = notes.map(field => ({annotation_id:field.dataset.annotationId,
    transcription:field.value,
    review_status:field.value.trim()?'transcribed':'needs_review'}));
  download('annotation-review.json', JSON.stringify(rows,null,2), 'application/json');
};
document.getElementById('download-truth').onclick = () => {
  const incomplete = pages.filter(page => {
    const state = saved[page.dataset.pageId];
    return !state.complete || [...page.querySelectorAll('.review-row[data-line-id]')]
      .some(row => !state.lines[row.dataset.lineId]?.decision);
  });
  if (incomplete.length) {
    alert(`仍有 ${incomplete.length} 页未完成整页和逐行核验。`); return;
  }
  const rows = pages.map(page => {
    const state = saved[page.dataset.pageId];
    const lines = [...page.querySelectorAll('.review-row[data-line-id]')].flatMap(row => {
      const verdict = state.lines[row.dataset.lineId];
      if (verdict.decision === 'rejected') return [];
      const line = {bbox:JSON.parse(row.dataset.bbox)};
      if (verdict.decision === 'ambiguous') line.ambiguous = true;
      if (verdict.text.trim()) line.text = verdict.text.trim();
      return [line];
    });
    for (const item of state.missing) {
      const line = {bbox:item.bbox};
      if (item.text.trim()) line.text = item.text.trim();
      lines.push(line);
    }
    return {page_id:page.dataset.pageId,
      page_number:state.pageNumber === '' ? null : Number(state.pageNumber),
      lines};
  });
  download('ground-truth.jsonl', rows.map(x => JSON.stringify(x)).join('\n')+'\n',
    'application/x-ndjson');
};
"""


def build_review(run: Path) -> None:
    run = run.resolve()
    meta = json.loads((run / "run.json").read_text(encoding="utf-8"))
    pages = _rows(run / "pages.jsonl")
    lines = _rows(run / "lines.jsonl")
    groups = _rows(run / "groups.jsonl")
    annotations = _rows(run / "annotations.jsonl") if (run / "annotations.jsonl").exists() else []
    brackets = _rows(run / "brackets.jsonl") if (run / "brackets.jsonl").exists() else []
    reviews = _rows(run / "review_candidates.jsonl")
    failures = _rows(run / "failures.jsonl")
    by_page = defaultdict(list)
    by_review = defaultdict(list)
    by_annotation = defaultdict(list)
    by_line = defaultdict(list)
    for group in groups:
        by_page[group["page_id"]].append(group)
    for item in reviews:
        by_review[item["page_id"]].append(item)
    for item in annotations:
        by_annotation[item["page_id"]].append(item)
    for line in lines:
        by_line[line["page_id"]].append(line)
    parts = ["<!doctype html><html lang='zh'><meta charset='utf-8'>",
             "<title>Bookscan 离线核验</title>",
             "<style>body{font:16px system-ui;max-width:1300px;margin:auto;padding:24px;"
             "background:#f5f6f5;color:#202520}h1,h2{margin:.6em 0}section,article{background:white;"
             "border:1px solid #ddd;border-radius:8px;margin:20px 0;padding:16px}"
             "img{max-width:100%}.page{max-height:650px;object-fit:contain}"
             "table{border-collapse:collapse;width:100%}td,th{border-bottom:1px solid #ddd;"
             "padding:6px;text-align:left;vertical-align:top}code,pre{white-space:pre-wrap;"
             "overflow-wrap:anywhere}.crops{display:flex;gap:12px;flex-wrap:wrap}"
             "summary{cursor:pointer;font-weight:600}.flag{color:#9b3500}"
             ".source-wrap{position:relative;display:inline-block;max-width:100%;touch-action:none}"
             ".source-wrap img{display:block;max-height:700px}"
             ".source-wrap canvas{position:absolute;inset:0;width:100%;height:100%;cursor:crosshair}"
             ".review-row{padding:8px;border-bottom:1px solid #ddd}"
             ".review-row textarea{width:100%;min-height:3em}"
             ".review-row select{margin:0 8px}</style>",
             f"<h1>Bookscan 离线核验</h1><p>运行 {_e(meta['run_id'])} · "
             f"{len(pages)} 页 · {len(groups)} 组 / {len(lines)} 条标记行 · "
             f"{len(annotations)} 处手写批注候选 · "
             f"{len(brackets)} 组角括号标记 · "
             f"{len(reviews)} 个待核对候选"
             f" · {len(failures)} 个失败记录</p>",
             "<p>叠加图：绿色为已选行，红色为下划线证据，橙色为待核对线条，"
             "蓝色为视觉页码候选，紫色为手写批注区域，青色为角括号范围。</p>",
             "<p class='flag'>人工真值未提供：准确率未评估。请逐页检查，包括零结果页面。"
             "完成每页人工核验后可导出 ground-truth.jsonl，再运行 evaluate。</p>",
             "<p id='review-progress'>尚未核验</p>"]
    for page in pages:
        number = page["page_number"]
        source = Path(meta["config"]["root"]) / page["source_file"]
        source_link = os.path.relpath(source, run)
        clean = f"pages/{page['page_id']}.jpg"
        overlay = f"overlays/{page['page_id']}.jpg"
        parts.append(f"<section id='{_e(page['page_id'])}'>"
                     f"<h2>{_e(page['scan_index'])}: {_e(page['source_file'])}</h2>"
                     f"<p>状态 {_e(page['processing_status'])}；已选 "
                     f"{_e(page['selected_line_count'])} 行；旋转 {_e(page['rotation'])}°；"
                     f"有效区域 {_e(page['valid_page_roi'])}</p>"
                     f"<p>页码：{_e(number['status'])}；视觉读数 "
                     f"{_e(number['observed_label'])}；推断 {_e(number['inferred_value'])}；"
                     f"候选 {_e([(x['raw'], x['region']) for x in number['candidates']])}；"
                     f"依据 {_e(number['inference_evidence'])}</p>"
                     f"<p><a href='{_e(clean)}'>打开转正单页</a> · "
                     f"<a href='{_e(overlay)}'>打开框选图</a> · "
                     f"<a href='{_e(source_link)}'>打开原始扫描件</a></p>")
        if (run / overlay).exists():
            parts.append(f"<a href='{_e(overlay)}'><img class='page' src='{_e(overlay)}' "
                         "alt='原图叠加行框和下划线框'></a>")
        parts.append(f"<details class='page-review' data-page-id='{_e(page['page_id'])}' "
                     f"data-page-number='{_e(number['resolved_value'])}' "
                     f"data-source-width='{page['source_size'][0]}' "
                     f"data-source-height='{page['source_size'][1]}'>"
                     "<summary>逐页人工核验：确认画线、记录漏检</summary>"
                     "<p>先检查上方整页叠加图，再逐条确认机器选中的行。"
                     "如有漏检，在下方原始扫描件上拖动框出整行；坐标会按原图像素保存。"
                     "若照片显示不出来，可手工输入原图坐标。</p>"
                     f"<div class='source-wrap'><img src='{_e(source_link)}' "
                     "alt='原始扫描件，用于框出漏检行'><canvas></canvas></div>"
                     "<h4>机器选中行</h4>")
        underline_lines = [line for line in by_line[page["page_id"]]
                           if line.get("mark_type", "underline") == "underline"]
        if not underline_lines:
            parts.append("<p>机器未选中下划线行；请核对是否漏检。</p>")
        for line in underline_lines:
            parts.append(f"<div class='review-row' data-line-id='{_e(line['line_id'])}' "
                         f"data-bbox='{_e(json.dumps(line['line_bbox']))}'>"
                         f"<a href='{_e(line['evidence_crop'])}'>"
                         f"<img src='{_e(line['evidence_crop'])}' alt='已选行证据'></a>"
                         f"<p><code>{_e(line['line_id'])}</code> · "
                         f"原图框 {_e(line['line_bbox'])}</p>"
                         "<label>判断 <select class='line-decision'>"
                         "<option value=''>待核验</option><option value='accepted'>真实画线</option>"
                         "<option value='rejected'>误收</option><option value='ambiguous'>无法判定</option>"
                         "</select></label><label>照片可见整行文字 "
                         f"<textarea class='line-text' placeholder='人工转录；机器 OCR：{_e(line['ocr_raw'])}'></textarea>"
                         "</label></div>")
        parts.append("<h4>漏检行</h4><div class='missing-lines'></div>"
                     "<button type='button' class='add-missing'>手工添加漏检框</button> "
                     "<label>实际印刷页码 <input class='truth-page-number' type='number' "
                     "placeholder='未知可留空'></label>"
                     "<p><label><input type='checkbox' class='page-complete'> "
                     "我已检查整页和所有候选，漏检均已补入</label></p></details>")
        if not by_page[page["page_id"]]:
            parts.append("<p class='flag'>本页没有已选划线或角括号组；仍需人工确认是否漏检。</p>")
        for group in by_page[page["page_id"]]:
            match = group.get("epub_candidate") or {}
            bracket = group.get("mark_type") == "corner_bracket"
            mark_label = "角括号「」" if bracket else "下划线"
            parts.append(f"<article data-group-id='{_e(group['group_id'])}'><h3>"
                         f"{_e(group['group_id'])} · "
                         f"{mark_label} · {_e(group['match_status'])} · "
                         f"{len(group['line_ids'])} 行</h3>"
                         f"<a href='{_e(group['evidence_crop'])}'>"
                         f"<img src='{_e(group['evidence_crop'])}' alt='文字和标记证据'></a>"
                         "<table><tr><th>标记覆盖的 OCR 文字（估算）</th><td>" +
                         _e(group.get("marked_ocr_text")) +
                         "</td></tr><tr><th>照片整行 OCR</th><td>" + _e(group["ocr_raw"]) +
                         "</td></tr><tr><th>标记对应的 EPUB 文字</th><td>" +
                         _e(match.get("exact")) +
                         "</td></tr><tr><th>向标点扩展</th><td>" +
                         _e(group.get("epub_expanded_text")) +
                         "</td></tr><tr><th>当前文本 / 来源</th><td>" +
                         _e(group["text_effective"]) + " / " +
                         _e(group["text_basis"]) +
                         "</td></tr><tr><th>匹配区间</th><td>" +
                         _e((match.get("href"), match.get("start"), match.get("end"),
                             match.get("expanded_start"), match.get("expanded_end"))) +
                         "</td></tr><tr><th>待核对原因</th><td>" +
                         _e(group.get("review_reasons")) +
                         "</td></tr></table><p><label>人工判断 <select class='group-decision'>"
                         "<option value=''>待核验</option><option value='accepted'>文本正确</option>"
                         "<option value='wrong_span'>标记范围错误</option>"
                         "<option value='wrong_epub'>EPUB 定位或扩展错误</option>"
                         "<option value='rejected'>误收标记</option></select></label></p>"
                         "<label>人工认可文本（有修订时填写）"
                         "<textarea class='group-text' rows='2' style='width:100%'></textarea>"
                         "</label></article>")
        if by_annotation[page["page_id"]]:
            parts.append("<h3>手写批注（独立证据，待人工核对）</h3>"
                         "<p>可在下方修订手写转录；浏览器会在本机保存草稿，"
                         "点击页面底部按钮下载核对结果。</p>")
        for note in by_annotation[page["page_id"]]:
            parts.append(f"<article><h4>{_e(note['annotation_id'])}</h4>"
                         f"<a href='{_e(note['evidence_crop'])}'>"
                         f"<img src='{_e(note['evidence_crop'])}' alt='手写批注裁图'></a>"
                         "<table><tr><th>机器 OCR 猜测</th><td>" +
                         _e(note['ocr_raw']) +
                         "</td></tr><tr><th>人工转录</th><td><textarea "
                         f"data-annotation-id='{_e(note['annotation_id'])}' "
                         "rows='3' style='width:100%' placeholder='逐字核对后填写'></textarea>"
                         "</td></tr><tr><th>状态</th><td>需人工核对或转录"
                         "</td></tr></table></article>")
        if by_review[page["page_id"]]:
            parts.append("<details><summary>被拒绝或无法关联的候选 " +
                         str(len(by_review[page["page_id"]])) + "</summary><pre>" +
                         _e(json.dumps(by_review[page["page_id"]], ensure_ascii=False,
                                       indent=2)) + "</pre></details>")
        parts.append("</section>")
    if failures:
        parts.append("<section><h2>失败</h2><pre>" +
                     _e(json.dumps(failures, ensure_ascii=False, indent=2)) +
                     "</pre></section>")
    parts.append("<p><button id='download-decisions'>下载核验草稿 JSON</button> "
                 "<label>导入核验草稿 JSON <input id='import-decisions' type='file' "
                 "accept='application/json,.json'></label> "
                 "<button id='download-truth'>下载完整 ground-truth.jsonl</button> "
                 "<button id='download-annotations'>下载手写批注核对结果</button></p>")
    parts.append("<script>const runId=" + json.dumps(meta["run_id"]) + ";</script>")
    parts.append("<script>" + REVIEW_SCRIPT + "</script>")
    parts.append("</html>")
    (run / "review.html").write_text("\n".join(parts), encoding="utf-8")
    decisions = run / "review-decisions.jsonl"
    if not decisions.exists():
        decisions.touch()
    counts = Counter(group["match_status"] for group in groups)
    report = [f"# 实验报告：{meta['run_id']}", "",
              "## 输入与环境", "",
              f"- 扫描页：{len(pages)}；EPUB SHA-256：`{meta['epub']['epub_sha256']}`。",
              f"- 检测模型：`{meta['models']['detection_name']}`；识别模型："
              f"`{meta['models']['recognition_name']}`。",
              f"- CPU 本地处理耗时：{meta['elapsed_seconds']} 秒。", "",
              "## 机器输出", "",
              f"- 已选标记行：{len(lines)}，合并为 {len(groups)} 组；"
              f"组级 EPUB 匹配状态：{dict(counts)}。",
              f"- 手写批注区域：{len(annotations)}；OCR 猜测均待人工核对。",
              f"- 角括号标记：{len(brackets)}；与下划线分开记录。",
              f"- 待核对线条候选：{len(reviews)}；失败：{len(failures)}。",
              f"- 零结果页：{sum(not by_page[p['page_id']] for p in pages)}。", "",
              "## 逐页结果", "",
              "| 文件 | 印刷页码 | 已选行 | 异常 |", "| --- | --- | ---: | --- |"]
    for page in pages:
        number = page["page_number"]
        label = (f"{number['resolved_value']} ({number['status']})" if
                 number["resolved_value"] is not None else number["status"])
        report.append(f"| {page['source_file']} | {label} | "
                      f"{page['selected_line_count']} | {', '.join(page['issues'])} |")
    report += ["", "## 待核对的机器校正", "",
               "以下是机器候选，不代表人工认可或准确率。"]
    for group in [x for x in groups if x["match_status"] == "needs_review"][:10]:
        report.append(f"- `{group['group_id']}`：OCR「{group['ocr_raw']}」；"
                      f"EPUB 标点扩展「{group.get('epub_expanded_text') or ''}」；"
                      f"原因 {', '.join(group['review_reasons'])}。")
    report += ["", "## 人工评估", "",
              "未评估：尚无逐页人工真值。机器输出数量不能作为召回率或准确率。",
              "逐页查看 `review.html`，在人工真值中补充漏检行后运行 `evaluate`。", "",
              "## 下一步核验", "",
              "检查波浪线漏检、相邻行分组、印刷横线误收、页码冲突，"
              "以及 EPUB 标点扩展的版本和位置是否正确。", ""]
    (run / "experiment-report.md").write_text("\n".join(report), encoding="utf-8")
