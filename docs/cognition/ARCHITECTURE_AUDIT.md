# Cognitive Retrieval Layer — Phase 0 audit

Audit date: 2026-09-18. The Vault was inspected read-only except for the explicitly derived fsck baseline at `.index/cognition/fsck-baseline/`.

## Confirmed

- `scripts/vault_fsck.py` is an existing, write-to-derived-data audit scanner. It excludes `.git`, `.obsidian`, `.trash`, `.index` and `_debug_remotely_save`; parses YAML with PyYAML; extracts attachments and wikilinks; and writes `files.jsonl`, `attachments.jsonl`, `stats.json`, and a report. Its manifest schema is `{path,type,source,source_id,source_url,created,updated,imported_at,attachments,sha256}`.
- `.index/` is ignored by the Vault Git rules and described in the Vault README as rebuildable audit data. No canonical note is written by this work.
- Representative format sampling found old unstructured diaries, heading-based daily notes, AI Compiler MOCs with `type/status/created/updated`, WeRead highlight/comment sections, Zotero frontmatter, World Historian thread projections (`thread_id`, source `world-historian chronicle`), source-material files, clipping notes, Evernote `yinxiang_guid`/source metadata, and README/code-like prose.
- Current fsck baseline: 2,065 Markdown files, no malformed YAML, and no duplicate `source_id`. Missing source/date fields are common and are not repaired or inferred.
- PAP injects the complete requested skill instruction into a turn (`pap/run.py:_prompt`), calls an optional runtime `prepare` before a model turn and `complete` after it, uses per-run session keys, has append-only run/artifact logs and a shared gate/dedupe mechanism. Personal Historian owns its validated cards/summaries; World Historian owns its Chronicle and Obsidian projections.
- Run records expose provider input/output tokens and cost when the runner reports them. They do not currently expose tool-result bytes, cached-vs-uncached tokens, or per-loop model-call totals. No production run was re-executed for this audit.

## Rejected or revised assumptions

- Existing fsck is reusable as the enumeration/metadata baseline, but cannot directly create evidence units because it intentionally omits body spans and heading hierarchy. Phase 1 therefore adds a narrow Markdown projection adapter; it does not replace or modify fsck.
- Current `Dairies/2026` contains both legacy heading-only notes and newer structured material; typed daily parsing must wait for Phase 2 rather than infer one universal diary schema.
- World Historian thread Markdown is a projection, not its canonical ownership database, so Phase 1 treats it conservatively as derived external material.

## Phase 1 layout

`pap/cognition.py` contains the small local store, scanner adapter, conservative classifier, heading segmenter, FTS query service and CLI. (Status note 2026-10: runtime hooks now exist — both production agents run `agents/{intelligence,serendipity}/runtime/cognition.py` adapters through their scheduled jobs.)
