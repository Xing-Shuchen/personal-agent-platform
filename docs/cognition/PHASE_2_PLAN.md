# Phase 2–4 implementation and remaining work

Implemented: heading-level adapters for diary observation/reflection/`对影成`, WeRead highlight versus comment, Zotero quotes/comments, World Historian Event/Claim/Open Question headings, and Evernote OCR detection. Derived weekly/monthly-like sections reference Wikilinks through `derivations`; this is deliberately conservative and awaits typed Personal Historian artifact ingestion.

Implemented: deterministic candidate construction using shared lexical/CJK-bigram features and Wikilinks, with same-family, synthesized and delivered-pair exclusion accounting. `pap cognition shadow serendipity` and `pap cognition shadow intelligence` write replayable packs under `.index/cognition/context-packs/` and audit run metadata in SQLite.

> Status note (2026-10): the pack machinery is now connected to production — the scheduled `intelligence-pulse` and `serendipity-pulse` jobs run through `agents/{intelligence,serendipity}/runtime/cognition.py`, which build the index and inject `shadow_pack` output as the model's input. Embeddings are implemented with a deterministic offline fallback (see ARCHITECTURE.md status note).

Remaining before opt-in: direct canonical Historian artifact adapters, richer explicit weekly/day lineage, entity/mechanism extraction, temporal recurrence and structural-analogy strategies, canonical PAP delivery history read-through (the `delivered_connections` table is read for dedupe but not yet written), and a controlled A/B comparison against current browsing.

Watch Hypotheses remain future derived records: `{id,status,prior_evidence_id,prior_kind,update_conditions,affected_projects,question_ids,evidence_threshold,urgency_condition,expiry,revisit_after,derived_from,extractor_version,confidence,sensitivity}`. They may originate only from eligible self-authored belief/question/decision/project-friction evidence.

Synthetic samples: an authored unit has `voice:self, origin:authored`; an external saved unit has `voice:external, origin:saved_external, requires_source_verification:true`; a generated unit has `is_derived:true` and `derivations` rows. A rename preserves document family when old exact bytes disappear. An FTS result is a bounded excerpt, never whole-body dump. See `CONTEXT_PACK_SPEC.md` for both future pack examples.
