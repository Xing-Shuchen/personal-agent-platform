---
name: news-capture
description: Capture a user-named external development or URL into the World Historian as sourced claims, an event, and a continuing thread.
---

# Capture an external event

Treat the input as a seed for an ongoing thread, not as an article title.

1. Read `config.yaml` from this profile directory for the preferred `sources`
   list. When the seed maps to one of those outlets (远川研究所矩阵、腾讯科技、
   新潮沉思录、36氪、量子位、机器之心、智能涌现、凤凰网, or a vetted RSS
   feed), start from it: `kind: rss` feeds fetch directly, `kind: site` outlets
   are browsed, `kind: wechat` outlets are searched via `site:mp.weixin.qq.com`.
2. Search for the current state of the event and locate at least one primary or
   authoritative source when one exists. Keep secondary reporting only when it
   adds a distinct claim or records how understanding evolved.
3. Search the Chronicle for an existing matching thread before creating one.
4. Separate source observations, claims, event facts, and open questions.
   Preserve `occurred_at`, `reported_at`, and `observed_at` separately; use
   `null` and an explicit precision when the occurrence time is unknown.
   Give every event a short `title` (maximum 60 characters) for its timeline
   heading, and put the complete account in `summary` as Markdown body text.
   The title is an identifying phrase, never a compressed evidence dump.
5. Create a small initial source set, the event, its claims, thread entities,
   open questions, and watch queries. Do not assert motivations as facts.
   For every named person whose statement is referenced, also retrieve and
   store the verbatim original (发言原话 / 公开信 / 文章全文或明确节选) as a
   Chronicle `quote` with a `slug` (renders to `原文素材/<slug>.md`) and its
   source URL. Prefer the original platform (微博 / 公众号 / 头条 / 官网) over
   media paraphrase; if only a paraphrase is available, store the verbatim
   quotation as reported and state the limitation. Never fabricate a quote.
6. Read [the Chronicle bundle format](references/chronicle-bundle.md),
   then persist one validated JSON bundle with:

   `"/home/xingzeng/personal-agent-platform/.venv/bin/python" "/home/xingzeng/personal-agent-platform/agents/world-historian/runtime/cli.py" store-bundle --json <path>`

   The runtime assigns deterministic IDs and commits the bundle atomically.
6. Return a compact Chinese intake report: what was captured, the best primary
   evidence, unresolved questions, uncertainty, and whether an existing thread
   was reused.

## Math in stored text

Event summaries, claim statements, and open questions are projected verbatim
into the Obsidian vault, where `$...$` (inline) and `$$...$$` (display) render
as LaTeX. When storing mathematical content, write real LaTeX inside `$...$`
instead of Unicode notation: `$Y(X) \gg X\log X/\log_3 X$`, not
`Y(X)≫X·logX/log₃X`; `$\pi_1(X)$`, not `π₁(X)`. Narrative prose stays plain —
only actual formulas/expressions get `$` delimiters. Never use Unicode
sub/superscripts inside formulas (`log₃`, `π₁` → `\log_3`, `\pi_1`);
`S⁶` in running prose may stay, but inside a formula write `$S^6$`.

Initialize or inspect storage with `/home/xingzeng/personal-agent-platform/agents/world-historian/runtime/cli.py init`, `search`, `thread`,
and `stats`. Never place the SQLite database or raw snapshots under `profile/`.
