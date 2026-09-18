# Evidence schema

An Evidence Unit stores identity (`evidence_id`, `evidence_family_id`, revision, document), provenance (`source_path/type`, voice, origin, assertion kind, permission record), exact span/heading/block anchor, original text, exact and normalized hashes, multi-clock timestamp JSON, maturity/sensitivity/confidence, derived/synthesized/retrieval/verification flags, and scanner/segmenter/extractor/schema versions.

`document_id` prefers intrinsic frontmatter/plugin/Historian identifiers, then safe unchanged-content move detection, then a local derived ID. Family anchors use structured IDs when available and otherwise heading structural ordinal. Revisions change when source text changes. No UUID is written to Markdown.

`derivations` is reserved for summary-to-source lineage; it prevents future weekly/daily and claim/raw-source double counting. `links` stores Wikilinks now and permits structural/Historian relations later.
