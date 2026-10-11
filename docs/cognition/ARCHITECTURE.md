# Architecture

The Vault remains canonical. Cognitive Retrieval Layer records are materialized projections: `canonical document -> document revision -> evidence unit`. Deleting `cognition.sqlite3` loses no facts and a rebuild recreates it.

Phase 1 uses SQLite and FTS5 only. A build opens a BUILDING generation, retains the last COMPLETE generation on failure, reads each candidate twice around content read to detect a concurrent write, hashes exact and normalized text, and commits a new COMPLETE generation only after all work succeeds. Exact unchanged content at a disappeared old path is a move; two simultaneous equal files remain distinct documents. A simultaneous anonymous move-and-edit may become a new family rather than being fuzzy-merged.

The generic segmenter excludes frontmatter, follows Markdown headings, splits only oversized sections at paragraph boundaries, preserves heading and exact character spans, and never applies universal fixed-size chunks. Future typed adapters may refine units without changing document identity.

The schema includes `documents`, `document_revisions`, `evidence_units`, FTS5, relational `links`, `derivations`, retrieval-run metadata, and generation records. Phase 1 does not create an external service, a graph database, LLM extraction, or agent migration.

> Status note (2026-10): embeddings are now implemented — `evidence_embeddings` stores transformer vectors when `sentence-transformers` is importable and deterministic `pap-local-hash-v1` vectors otherwise (see `pap/retrieval.py`); `PAP_CANDIDATE_RETRIEVAL_EMBEDDINGS_ENABLED=0` disables them. The two production adapters (`agents/{intelligence,serendipity}/runtime/cognition.py`, wired via `runtime: cognition` in both manifests) build the index and feed `shadow_pack` output to scheduled model runs, so the shadow-pack machinery is production-connected.

Future retrieval is ID-first: a ContextPack gives candidates and bounded excerpts; an LLM expands evidence IDs selectively. Candidate strategies may include lexical, shared entity/mechanism, recurrence, question closure, structural contrast, graph walk and controlled random leap. Scores construct candidates only; the LLM makes the final evidential judgment.
