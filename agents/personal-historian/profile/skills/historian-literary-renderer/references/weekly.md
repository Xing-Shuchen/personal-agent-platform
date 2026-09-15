# Human-facing weekly narrative

Write for the person whose week this was, not for a database auditor.
Begin with Obsidian-compatible YAML Properties in exactly this shape:

```yaml
---
schema_version: 1
week: YYYY-Www
type: ethnography-weekly
status: complete | partial
period_start: YYYY-MM-DD
period_end: YYYY-MM-DD
people: []
projects: []
topics: []
artifacts: []
phrases: []
scenes: []
threads: []
---
```

The fixed values must match the canonical PeriodSummary. Select only concise,
useful indexing values explicitly supported by it. `phrases` may contain only
verbatim phrases already present in the canonical summary. Empty lists are
valid. These Properties index this replaceable view; they are not new evidence.
After the closing `---`, write the narrative beginning with one level-1 heading.
Use first person when the canonical material is clearly the user's own diary or
self-testimony; do not make the user read their life as a report about "他".

Use this shape when the material supports it:

```text
# 周报 · M.D – M.D

## 主线：一句具体、可回忆的判断
chronological narrative in short paragraphs

## 副线：真正独立且值得保留的第二条线
one or two paragraphs

## 背景：贯穿全周、改变体验的条件
one short paragraph
```

The headings are semantic roles, not mandatory labels. Omit an empty section
instead of forcing every week into three parts. Usually use 600–1400 Chinese
characters. Keep dates readable (`8 月 26 日`, `周三`) rather than ISO timestamps.

A good main line connects supported moments across days and ends with what
changed or remained unresolved. It does not merely name the busiest project.
When the canonical summary supports a coherent relationship, care, travel, or
lived-experience arc with a concrete culmination, prefer that as the main line
over building tools or organizing the historical system itself. Tool-building
can be a secondary line even when it occupies more source text. Subjective
salience and human consequence matter more than activity volume.

Before drafting, silently choose the smallest set of details that makes that
arc intelligible. A detail belongs in the main line only when it changes the
situation, reveals the relationship, motivates a supported decision, or pays
off later. Omit incidental meals, commutes, prices, telemetry, implementation
mechanics, and database/browser facts unless one is genuinely necessary to the
arc. Do not turn every canonical claim into prose; selection is the renderer's
main job.

Write the main line as a remembered week, not as a compressed evidence report.
Prefer scene, transition, and consequence over qualification. Never mention
snapshot timing, collection timing, source types, independent verification,
or phrases such as `这是自述`, `不是量出来的`, `记录只说明`, and `证据显示`.
The canonical layer already preserves those distinctions. In the literary view,
use light attribution such as `我记得`, `我写下`, or `她说` only when it is
material to meaning. Preserve an actual contradiction or uncertainty in plain
language, but do not narrate the provenance machinery.

For a relationship-and-travel arc, look for this supported sequence: the other
person's difficult state; what I did in response; the decision to leave routine;
friction on the way; one concrete moment of release; and the narrator's own
closing judgment. Use only links and judgments present in the canonical summary,
but prefer this emotional spine when it exists. End the main line on the human
payoff, not on cost accounting, driving speed, or an unrelated future purchase.

If the canonical period begins with days that have no narrative evidence, the
title may use the first and last supported dates (for example `8.26 – 8.30`)
instead of implying a seven-day account. Do not end with an audit appendix or a
generic evidence disclaimer. Express a material limit locally (`日记里记着`,
`我当时觉得`) and omit technical caveats that do not change the story.
Quotes are allowed only when the canonical summary contains the quote. Never
upgrade recorded browsing, commits, or file mtimes into lived experience.
