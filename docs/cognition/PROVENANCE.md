# Provenance rules

Phase 1 records `voice`, `origin_type`, `assertion_kind`, permissions, field provenance and source-verification requirements separately; it deliberately has no scalar authority score.

`self/authored` material may support a claim that the user expressed a belief, decision or question, not that it is true. Clippings and source material are external. WeRead highlights are external selected text; Zotero and Evernote default to unknown or external until a typed adapter can distinguish an annotation from publication text. OCR must be marked retrieval-only by a future adapter unless a verifiable original is attached. World Historian projections are system-derived external material. Unknown always wins over incorrect autobiographical attribution.

Every non-text field has a derivation source (`frontmatter`, `path_rule`, `markdown_structure`, `deterministic_rule`, `source_adapter`, `historian`, `llm_extractor`, or `system`). Time values carry value, precision and derivation source; filesystem mtime is freshness only.
