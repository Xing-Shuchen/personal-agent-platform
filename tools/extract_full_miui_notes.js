#!/usr/bin/env node
const fs = require('fs');
const cp = require('child_process');
const path = require('path');

const tmp = '/tmp/full-notes-export';
const output = '/home/xingzeng/文档/Obsidian/Second_Brain/备忘录导出-2026-09-12.md';
const checkpoint = `${tmp}/notes.json`;
fs.mkdirSync(tmp, { recursive: true });
const run = (cmd) => {
  for (let attempt = 0; attempt < 3; attempt++) {
    try { return cp.execFileSync('bash', ['-lc', cmd], { stdio: 'ignore', timeout: 15000 }); }
    catch (error) {
      if (attempt === 2) throw error;
      cp.execFileSync('bash', ['-lc', 'sleep 2'], { stdio: 'ignore' });
    }
  }
};
const dump = (remote, local) => { run(`adb shell uiautomator dump ${remote} >/dev/null`); run(`adb pull ${remote} ${local} >/dev/null`); return fs.readFileSync(local, 'utf8'); };
const decode = (s) => s.replaceAll('&#10;', '\n').replaceAll('&amp;', '&').replaceAll('&quot;', '"').replaceAll('&#128527;', '😏');
const attr = (tag, name) => (tag.match(new RegExp(`${name}="([^"]*)"`)) || [, ''])[1];
const nodes = (xml) => [...xml.matchAll(/<node\b[^>]*>/g)].map((m) => ({ tag: m[0], text: decode(attr(m[0], 'text')), id: attr(m[0], 'resource-id'), bounds: attr(m[0], 'bounds') }));
const box = (bounds) => (bounds.match(/\[(\d+),(\d+)\]\[(\d+),(\d+)\]/) || []).slice(1).map(Number);
const inside = (child, parent) => { const [x1,y1,x2,y2] = box(child.bounds), [a,b,c,d] = box(parent.bounds); return x1 >= a && y1 >= b && x2 <= c && y2 <= d; };

run('adb shell am force-stop com.miui.notes');
run('adb shell am start -n com.miui.notes/.ui.NotesListActivity >/dev/null');
run('sleep 2');
// Main activity restores the last tab; switch explicitly to Notes (not To-dos).
run('adb shell input tap 360 3030');
run('sleep 2');
// Ensure the combined view is selected rather than the travel folder.
run('adb shell input tap 127 622');
run('sleep 2');
const notes = fs.existsSync(checkpoint) ? JSON.parse(fs.readFileSync(checkpoint, 'utf8')) : [];
const seen = new Set(notes.map((n) => `${n.date}\u0000${n.title}\u0000${n.preview || ''}`));
for (let page = 0; page < 24; page++) {
  const listXml = dump('/sdcard/full-list.xml', `${tmp}/list-${page}.xml`);
  const listNodes = nodes(listXml);
  const groups = listNodes.filter((n) => n.id === 'com.miui.notes:id/note_group' && box(n.bounds)[3] - box(n.bounds)[1] > 150);
  let added = 0;
  for (const group of groups) {
    const fields = listNodes.filter((n) => inside(n, group));
    const title = fields.find((n) => n.id === 'com.miui.notes:id/title')?.text || '';
    const date = fields.find((n) => n.id === 'com.miui.notes:id/time')?.text || '';
    const preview = fields.find((n) => n.id === 'com.miui.notes:id/content_body')?.text || '';
    const key = `${date}\u0000${title}\u0000${preview}`;
    if (!title || seen.has(key)) continue;
    seen.add(key);
    const [x1,y1,x2,y2] = box(group.bounds);
    run(`adb shell input tap ${Math.floor((x1+x2)/2)} ${Math.floor((y1+y2)/2)}`);
    run('sleep 1');
    // The detail editor is a WebView. Its accessibility tree contains the
    // complete rendered text after opening and cancelling Markdown export.
    run('adb shell input tap 912 240');
    run('sleep 1');
    run('adb shell input tap 720 2660');
    run('sleep 1');
    run('adb shell input keyevent BACK');
    run('sleep 1');
    const detailXml = dump('/sdcard/full-detail.xml', `${tmp}/detail-${notes.length}.xml`);
    const detailNodes = nodes(detailXml);
    const candidates = detailNodes.map((n) => n.text.trim()).filter((t) => t.length > 0 && !['小米笔记','标题','返回','分享','模板','更多'].includes(t));
    const body = candidates.sort((a,b) => b.length - a.length)[0] || preview || title;
    notes.push({ date, title, preview, body });
    fs.writeFileSync(checkpoint, JSON.stringify(notes));
    added++;
    process.stdout.write(`extracted ${notes.length}: ${title.slice(0, 36)}\n`);
    run('adb shell input keyevent BACK');
    run('sleep 1');
    // Returning from the export picker occasionally lands on the launcher;
    // explicitly restore the list activity before the next card is tapped.
    run('adb shell am start -n com.miui.notes/.ui.NotesListActivity >/dev/null');
    run('sleep 1');
  }
  run('adb shell input swipe 720 2700 720 850 350');
  run('sleep 2');
}
const esc = (s) => s.replaceAll('|', '\\|');
const md = ['# 备忘录导出', '', `完整正文提取时间：2026-09-12；共 ${notes.length} 条。`, ''];
for (const n of notes) md.push(`## ${esc(n.title)}`, '', `日期：${n.date || '未显示'}`, '', n.body, '');
fs.writeFileSync(output, md.join('\n'));
console.log(`Wrote ${output}`);
