# Future ContextPack specification

`serendipity.context-pack.v1` contains run ID, index generation, deterministic seed, time window, three budgets (retrieval/reasoning/expression), seed evidence, 6–8 candidate pairs with provenance/time/strategy reasons, excluded counts, derivation overlap, expandable IDs, versions and hash. Suggested initial context is 6–8k tokens, at most four <=1,200-token expansions and <=5k total tool payload.

`intelligence.context-pack.v1` contains world watermark/deltas, <=6 eligible personal targets, optional Watch Hypothesis IDs, possible update type, urgency, expandable world/personal evidence IDs, versions and hash. Suggested initial context is 4–6k tokens with <=3 expansions and <=4k tool payload.

Tool responses label source prose `UNTRUSTED_EVIDENCE_DATA`; only metadata is protocol. A web-search firewall permits only public-world terms. Private diary, health, relationship, finance or work wording never becomes a web query.

Synthetic example: `{ "schema":"serendipity.context-pack.v1", "index_generation":1, "rng_seed":"sha256:…", "candidates":[{"left_evidence_id":"evf_authored:r1","right_evidence_id":"evf_external:r1","strategy":"temporal_recurrence"}], "pack_hash":"sha256:…" }`.
