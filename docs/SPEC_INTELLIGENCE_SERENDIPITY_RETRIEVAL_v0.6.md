# PAP Intelligence & Serendipity Retrieval Specification v0.6

**Status:** Draft for implementation  
**Target:** `personal-agent-platform`  
**Scope:** shared candidate retrieval / admission layer for `serendipity` and `intelligence`  
**Primary objective:** improve candidate quality, corpus coverage, and useful-candidate supply before changing the judging model  
**Compatibility goal:** preserve existing PAP scheduler, `prepare/complete` runtime contract, append-only audit artifacts, LLM judge, dedupe, gate, and delivery semantics unless explicitly stated below.

---

## 0. Executive summary

`serendipity` and `intelligence` currently underperform in a way that is consistent with an upstream candidate-generation problem rather than a model-capability problem. In particular, `serendipity` can remain silent for tens of hours even though the knowledge base continues to contain potentially useful cross-time and cross-domain evidence. The existing candidate path also has a structural coverage bug: `_candidate_rows()` sorts by `evidence_id`, truncates to at most 160 rows, and only then shuffles. That is not random sampling over the corpus; it is random ordering over a fixed prefix of the corpus.

v0.6 therefore changes the retrieval substrate before changing the LLM:

1. replace keyword-gated recall with hybrid local recall using embeddings, BM25/FTS, entities, temporal distance, domain difference, and exploration state;
2. add deterministic hard filters before any candidate reaches the model;
3. replace prefix truncation with stratified, family-aware, rotation-based sampling over the eligible corpus;
4. learn from rejection logs by cooling down repeatedly useless anchors, templates, and pair families;
5. make every stage observable so a long silent period can be diagnosed as corpus starvation, recall starvation, filter starvation, model rejection, or delivery-gate rejection.

The central invariant is:

> **Lexical overlap is a supporting feature, never a prerequisite for candidate admission.**

The second invariant is:

> **v0.6 must improve the quality and coverage of candidates presented to the model without weakening the final delivery standard merely to increase delivery frequency.**

---

## 1. Problem statement

### 1.1 Current symptoms

Observed failure modes include:

- `serendipity` may go more than 50 hours without delivery;
- repeated runs waste budget on obviously weak lexical collisions;
- directory names, headings, templates, and other low-information fragments can repeatedly become anchors;
- the same evidence families can be reconsidered while large regions of the corpus remain unexplored;
- shared keywords can dominate candidate generation even when the two evidence units have no meaningful structural relationship;
- potentially valuable pairs with low lexical overlap are never surfaced to the LLM;
- unverified clipped material can consume model budget even though it cannot safely support a final claim;
- current logs make it difficult to distinguish “nothing good exists” from “nothing good was recalled.”

### 1.2 Root cause hypothesis

The working hypothesis for v0.6 is that the main bottleneck is **candidate supply quality and coverage**, not the final judging model.

The current architecture overweights cheap lexical signals too early. Once a bad candidate enters the LLM context, the model can reject it, but the run budget is already spent. Conversely, a semantically or structurally useful connection that lacks obvious shared terms can be excluded before the model has any opportunity to reason about it.

Therefore v0.6 moves more work into a deterministic/local retrieval layer, while deliberately preserving the LLM for the part that remains genuinely open-ended: deciding whether a surviving connection is non-obvious, explanatory, actionable, or personally meaningful.

---

## 2. Goals and non-goals

### 2.1 Goals

v0.6 MUST:

- provide corpus-wide, local-first hybrid retrieval;
- support Chinese/English mixed text without requiring an external embedding API;
- remove shared-keyword presence as an admission condition;
- prevent trivial fragments and known noisy structures from reaching the LLM;
- sample across time, domain, source type, and evidence family rather than a prefix of sorted rows;
- explicitly prefer evidence families that have not been explored recently;
- reuse rejection history to avoid repeatedly spending model budget on the same failure modes;
- preserve deterministic replay when a run seed is fixed;
- expose stage-level metrics and traces sufficient to diagnose long periods without delivery;
- work for both `serendipity` and `intelligence` through one shared retrieval core plus agent-specific profiles;
- degrade safely when the embedding index is unavailable.

### 2.2 Non-goals

v0.6 MUST NOT:

- replace the existing LLM judge as its primary change;
- weaken the final quality gate or force a delivery after N silent hours;
- introduce a mandatory remote vector database;
- turn the Vault / evidence store into an LLM-preprocessed knowledge graph as a prerequisite;
- treat embedding similarity as sufficient proof of a meaningful relationship;
- automatically infer that clipped or external material represents the user's own belief;
- permanently blacklist a topic merely because several weak lexical candidates used the same word;
- create a second source of truth that cannot be rebuilt from evidence + append-only logs.

---

## 3. Architectural position

v0.6 introduces a shared **Candidate Retrieval Layer** between the evidence index and the existing agent-specific LLM judging stage.

```text
Evidence / World Historian / Personal Historian
                    |
                    v
        +-------------------------+
        | Evidence Feature Index  |
        | FTS/BM25                |
        | local embeddings        |
        | entities / concepts     |
        | provenance / metadata   |
        +------------+------------+
                     |
                     v
        +-------------------------+
        | Hybrid Recall Engine    |
        | semantic                |
        | lexical                 |
        | entity                  |
        | temporal                |
        | domain bridge           |
        | exploration             |
        +------------+------------+
                     |
                     v
        +-------------------------+
        | Deterministic Filters   |
        +------------+------------+
                     |
                     v
        +-------------------------+
        | Stratified Selector     |
        | + cooldown policy       |
        | + diversity / MMR       |
        +------------+------------+
                     |
                     v
        agent-specific ContextPack
                     |
                     v
              existing LLM judge
                     |
                     v
           existing gate / dedupe
                     |
                     v
                 delivery
```

The Evidence Feature Index is a **derived, rebuildable index**. Append-only run/rejection artifacts remain the audit source of truth.

---

## 4. Core data model

v0.6 SHOULD extend the existing evidence/index schema rather than create a parallel database when equivalent fields already exist.

### 4.1 Required evidence features

Each candidate-addressable evidence unit MUST expose at least:

```text
evidence_id                 stable evidence-unit identifier
document_id                 containing document / artifact identifier
family_id                   exploration and dedupe family
content_hash                normalized content hash
body_text                   effective正文, excluding structural shell where possible
body_char_count             effective正文 length
source_type                 authored_note | diary | clip | world_event | claim | thread | ...
domain                      configured / derived broad domain, may be unknown
occurred_at                 event/content time if known
ingested_at                 index ingestion time
authorship                  user_authored | external | mixed | unknown
requires_source_verification boolean
verification_state          verified | independently_supported | unverified | not_required
template_fingerprint        optional structural/template fingerprint
topic_cluster_id            optional derived topic cluster
mechanism_signature         optional structured mechanism/concept signature
quality_flags               bitset/list of deterministic quality flags
embedding_text_hash         hash of text used for embedding
```

### 4.2 `family_id`

`family_id` exists to prevent a single source family from monopolizing exploration.

Recommended mapping:

- section/chunk from an authored note -> containing note/document;
- daily/weekly fragments -> canonical period artifact where appropriate;
- World Historian event -> event cluster or thread when available;
- Claim correction -> claim lineage;
- mirrored/saved webpage -> canonical URL/source family;
- repeated OCR pages from the same original item -> original item;
- otherwise -> `document_id`.

A family may contain multiple evidence units, but the selector SHOULD normally admit at most 1–2 units from one family per run unless an agent-specific strategy explicitly needs a local sequence.

### 4.3 Local embedding cache

Embeddings MUST be local-first and rebuildable.

Suggested default interface:

```yaml
embedding:
  provider: sentence_transformers
  model: intfloat/multilingual-e5-small
  normalize: true
  batch_size: 32
  device: auto
```

The concrete model is configuration, not part of the storage contract. A higher-quality multilingual model such as BGE-M3 may be substituted without changing candidate semantics.

Cache key:

```text
(model_id, embedding_text_hash)
```

Embedding rows MUST include model/version metadata so a model switch cannot silently mix incompatible vectors.

For the initial implementation, SQLite + a compact vector sidecar / local ANN index is preferred over introducing a network service. Brute-force cosine over a moderate corpus is acceptable as a reference implementation if it meets runtime budgets.

---

## 5. Hybrid recall

### 5.1 Recall principles

Candidate generation MUST be a union of multiple independent channels. No single channel may act as a universal prerequisite.

At minimum, implement:

- semantic vector recall;
- BM25/FTS recall;
- shared entity recall;
- temporal recurrence / cross-time recall;
- domain-difference / bridge recall;
- exploration recall from underexplored families.

When existing concept/mechanism metadata is available, also include mechanism-based recall.

### 5.2 Explicit lexical invariant

The following logic is forbidden:

```python
if not shared_keywords(a, b):
    reject_pair()
```

The following is allowed:

```python
features.lexical_overlap = lexical_overlap(a, b)
features.bm25_rank = ...
# lexical evidence contributes to ranking but is not an admission predicate
```

A candidate recalled only by embeddings, entities, temporal recurrence, or exploration MAY reach the LLM if it survives deterministic quality filters.

### 5.3 Rank fusion

Raw BM25 and cosine values are not directly comparable. v0.6 SHOULD use rank-based fusion, preferably Reciprocal Rank Fusion (RRF), to combine independent recall channels.

For channel `c` with rank `r_c`:

```text
rrf_c = 1 / (k + r_c)       # default k = 60
```

Base fused score:

```text
recall_score =
    w_semantic * rrf_semantic
  + w_lexical  * rrf_lexical
  + w_entity   * rrf_entity
  + w_temporal * rrf_temporal
  + w_domain   * rrf_domain
  + w_explore  * rrf_explore
```

The lexical weight MUST be capped so that lexical similarity alone cannot dominate a `serendipity` ranking.

### 5.4 Pair feature vector

Before hard filtering/ranking, compute a normalized pair feature record:

```json
{
  "semantic_similarity": 0.0,
  "lexical_overlap": 0.0,
  "entity_jaccard": 0.0,
  "shared_entity_count": 0,
  "temporal_distance_days": 0,
  "temporal_distance_norm": 0.0,
  "domain_same": false,
  "domain_distance": 0.0,
  "source_type_same": false,
  "topic_same": false,
  "mechanism_delta": 0.0,
  "evidence_quality": 0.0,
  "verification_quality": 0.0,
  "exploration_bonus": 0.0,
  "prior_rejection_penalty": 0.0,
  "prior_delivery_penalty": 0.0,
  "recall_channels": ["semantic", "explore"]
}
```

### 5.5 Serendipity profile

`serendipity` seeks a bridge that is simultaneously plausible and non-obvious. It SHOULD prefer:

- moderate/strong semantic or structural relation;
- substantial temporal separation where available;
- cross-domain or cross-source-type pairs;
- a mechanism relation that is not merely “same topic”;
- previously underexplored families;
- high provenance/evidence quality.

Illustrative default post-fusion ranking adjustment:

```text
score_serendipity = recall_score
  + 0.18 * domain_distance
  + 0.14 * temporal_distance_norm
  + 0.14 * mechanism_delta
  + 0.10 * evidence_quality
  + 0.10 * exploration_bonus
  - 0.20 * same_topic_penalty
  - 0.25 * prior_rejection_penalty
  - 0.20 * prior_delivery_penalty
```

These are defaults for tuning, not semantic constants.

Do not over-optimize for maximum embedding similarity. Pairs with extremely high similarity often represent duplication or obvious topical proximity; they should be checked for same-topic/no-mechanism-delta before ranking highly.

### 5.6 Intelligence profile

`intelligence` uses the same retrieval core but different structured signals. It SHOULD prefer candidates that connect an external update to one of:

- an Open Question;
- an authored belief / claim that may need updating;
- an active project;
- a pending decision;
- an existing watch query;
- a World Historian Thread;
- recent diary friction that expresses a concrete unresolved problem.

Useful relationship types include:

```text
answers_question
updates_belief
contradicts_claim
changes_project_assumption
changes_decision_input
crosses_watch_threshold
extends_thread
closes_uncertainty
```

For intelligence, domain difference is not intrinsically valuable. **Personal consequence / model-update linkage** has a higher weight than cross-domain novelty.

---

## 6. Deterministic pre-LLM hard filters

Hard filters exist to remove candidates that should not consume model tokens. They MUST be deterministic, traceable, and conservative.

Every rejection MUST record a machine-readable `reason_code`.

### 6.1 Fragment quality filter

Reject an evidence unit when it contains only structural shell such as:

- title only;
- headings/table of contents only;
- frontmatter/template fields only;
- path/directory listing only;
- boilerplate navigation;
- empty checklist/template placeholders.

Suggested flags:

```text
TITLE_ONLY
STRUCTURE_ONLY
TEMPLATE_ONLY
NAVIGATION_ONLY
```

Detection SHOULD use effective正文 extraction rather than raw file length.

### 6.2 Minimum effective body

Default minimum:

```yaml
hard_filter:
  min_effective_chars: 80
  min_effective_tokens: 24
```

Reject when both length tests indicate insufficient information.

Structured World Historian records may have a separate lower threshold if the structured fields themselves carry enough evidence. This exception MUST be explicit by `source_type`, not a global threshold reduction.

### 6.3 Stopword-only lexical collision

If a pair's only positive recall signal is lexical overlap and all shared lexical items are stopwords / generic structural tokens / configured noise terms, reject it.

Important distinction:

- **No shared terms:** allowed.
- **Only meaningless shared terms and no other signal:** rejected.

Maintain language-aware stopwords plus a PAP-specific noise lexicon, e.g. common template words, repository boilerplate, directory labels, and repeated system headings.

### 6.4 Same-topic-without-mechanism-delta

Reject obvious near-topic pairs when there is no evidence of a different mechanism, consequence, role, or relation.

Use conservative rules. Suggested hard-reject condition:

```text
same_topic == true
AND semantic_similarity >= same_topic_semantic_threshold
AND entity_jaccard >= same_topic_entity_threshold
AND mechanism_delta <= mechanism_delta_floor
```

If mechanism metadata is unknown, do not infer a strong mechanism difference. However, absence of mechanism metadata alone MUST NOT cause a hard rejection unless other near-duplicate/same-topic signals are strong.

This filter is intended to remove pairs like two notes describing the same MLIR directory/module with no new structural relation, not to suppress all same-domain reasoning.

### 6.5 Duplicate / same-family filter

Reject:

- same `evidence_id`;
- identical normalized content hash;
- near-duplicate chunks from the same family when the pair adds no temporal/causal relation;
- duplicate external source mirrors.

### 6.6 Source verification filter

If either candidate requires source verification and the claim being used is not independently supported, reject before the LLM.

```text
requires_source_verification == true
AND verification_state NOT IN {verified, independently_supported}
=> reject UNVERIFIED_SOURCE
```

Independent support MUST come from a distinct source family. Multiple copies of the same canonical source do not count as independent evidence.

For intelligence, a trusted primary source MAY satisfy verification according to the existing World Historian trust policy. The retrieval layer should consume that policy result rather than reimplement source trust ad hoc.

### 6.7 Cooldown filter

Candidates matching an active cooldown MAY be dropped or penalized according to cooldown scope. See Section 9.

### 6.8 Filter trace

For every filtered candidate, record:

```json
{
  "candidate_id": "...",
  "stage": "hard_filter",
  "reason_code": "SAME_TOPIC_NO_MECHANISM_DELTA",
  "feature_snapshot": {
    "semantic_similarity": 0.93,
    "entity_jaccard": 0.78,
    "mechanism_delta": 0.02
  }
}
```

Do not persist full private正文 in ordinary operational logs; use IDs, hashes, numeric features, and short safe diagnostics.

---

## 7. Candidate-pool sampling redesign

### 7.1 Remove the current prefix bias

The following behavior MUST be removed:

```text
ORDER BY evidence_id
LIMIT 160
shuffle(...)
```

Shuffling after truncation does not create corpus coverage.

No global `LIMIT` may be applied before stratification unless it is applied independently inside every stratum according to an explicit quota.

### 7.2 Stratification axes

Sampling SHOULD stratify by at least:

1. **time bucket**
2. **domain**
3. **source type**
4. **evidence family exploration state**

Default time buckets:

```text
recent      0–14 days
medium      15–90 days
long        91–365 days
archive     >365 days / unknown historical
```

These thresholds are configurable.

### 7.3 Weighted fair allocation

Each run has a `seed_budget` and a `pair_budget`. Allocate seed slots across non-empty strata using weighted fair scheduling rather than pure proportional sampling.

A stratum with a small corpus MUST still receive occasional slots. Large recent strata must not starve archive or cross-domain material.

Example default for serendipity seed time allocation:

```yaml
recent: 0.30
medium: 0.25
long: 0.25
archive: 0.20
```

These are target shares, not strict per-run guarantees when strata are empty.

### 7.4 Rotate unexplored evidence families

Maintain derived family exploration state:

```text
family_id
last_explored_at
explore_count
last_selected_at
selected_count
last_llm_seen_at
llm_seen_count
accepted_count
delivered_count
```

Within each stratum, priority order SHOULD be:

1. never explored;
2. least recently explored;
3. lower `explore_count`;
4. deterministic run-seeded tie break.

This creates eventual coverage without relying on `ORDER BY RANDOM()` over the entire corpus.

### 7.5 Deterministic randomness

Runs MUST be reproducible when `run_seed` and index snapshot are fixed.

Tie-break value:

```text
tie_break = uint64(sha256(run_seed || family_id || evidence_id)[0:8])
```

Use this in application code after retrieving the oldest/least-explored candidate set for a stratum.

### 7.6 Per-family cap

Default:

```yaml
sampling:
  max_seed_units_per_family: 1
  max_pair_units_per_family: 2
```

Exceptions require an explicit retrieval strategy, e.g. a timeline relation that needs adjacent events.

### 7.7 Exploration reserve

Reserve a fraction of each model-stage candidate budget for candidates whose main reason for selection is exploration rather than high fused rank.

Default:

```yaml
serendipity:
  exploration_reserve: 0.20
intelligence:
  exploration_reserve: 0.10
```

This prevents the system from converging permanently onto the same high-scoring semantic neighborhoods.

---

## 8. Candidate budgeting and diversity

Suggested starting budgets:

```yaml
budgets:
  serendipity:
    seed_evidence: 24
    recall_per_seed_per_channel: 12
    prefilter_pair_cap: 600
    postfilter_rank_cap: 120
    llm_pair_budget: 32
  intelligence:
    seed_evidence: 32
    recall_per_seed_per_channel: 16
    prefilter_pair_cap: 800
    postfilter_rank_cap: 160
    llm_pair_budget: 40
```

These values are tuneable. The important contract is stage separation and metrics, not the exact numbers.

Before serialization to the LLM, apply diversity selection / MMR over:

- evidence family;
- domain pair;
- source-type pair;
- time bucket pair;
- retrieval strategy;
- semantic neighborhood.

No single anchor, domain pair, or family pair should occupy most of the LLM budget.

---

## 9. Learning from rejection logs

### 9.1 Principle

The system should learn **where not to spend retrieval/model budget**, but it should not convert LLM taste judgments into permanent censorship.

Only stable, structural rejection categories should create automatic cooldowns.

### 9.2 Rejection taxonomy

Minimum `reason_code` set:

```text
TITLE_ONLY
STRUCTURE_ONLY
TEMPLATE_ONLY
INSUFFICIENT_BODY
STOPWORD_ONLY_COLLISION
DUPLICATE_CONTENT
SAME_FAMILY_TRIVIAL
SAME_TOPIC_NO_MECHANISM_DELTA
UNVERIFIED_SOURCE
LEXICAL_COLLISION
WEAK_CONNECTION
OBVIOUS_CONNECTION
ALREADY_DELIVERED
NO_PERSONAL_CONSEQUENCE
NO_MODEL_UPDATE
MODEL_REJECT_OTHER
DELIVERY_GATE_REJECT
```

The first nine are deterministic/structural. `LEXICAL_COLLISION` is typically an LLM or post-hoc diagnosis that can safely train lexical cooldowns. `WEAK_CONNECTION`, `OBVIOUS_CONNECTION`, and other qualitative judgments should create soft penalties, not broad hard blocks.

### 9.3 Rejection event schema

Append one event per final candidate decision:

```json
{
  "schema": "candidate-rejection.v1",
  "run_id": "...",
  "agent": "serendipity",
  "candidate_id": "...",
  "evidence_ids": ["a", "b"],
  "family_ids": ["fa", "fb"],
  "recall_channels": ["bm25"],
  "reason_code": "LEXICAL_COLLISION",
  "anchor_refs": [
    {"kind": "lexical", "value_hash": "sha256:..."}
  ],
  "template_fingerprints": [],
  "pair_family_key": "...",
  "at": "..."
}
```

### 9.4 Anchor cooldown

An `anchor` is the specific feature that repeatedly creates bad pairings: a lexical token/phrase, entity, concept, or other recall hook.

For lexical anchors:

- require at least **3 `LEXICAL_COLLISION` rejections across distinct pair families within 7 days** before cooldown;
- cooldown affects the **lexical channel contribution**, not every other channel;
- a pair may still be recalled by semantic/entity/temporal channels.

Default cooldown progression:

```text
first qualified cooldown    24h
second                      72h
third                       7d
subsequent                  14d cap
```

A later accepted/delivered pair using the same anchor SHOULD reduce or clear its penalty.

This is specifically designed to stop anchors such as recurring directory/module names from consuming every run without permanently forbidding that subject.

### 9.5 Template cooldown

A template fingerprint that repeatedly yields `TEMPLATE_ONLY`, `STRUCTURE_ONLY`, or `INSUFFICIENT_BODY` SHOULD be suppressed before pair generation.

Default:

```text
2 deterministic rejects from same template fingerprint -> 7d cooldown
5+ rejects -> 30d cooldown
```

If the source content hash or extractor version changes, the cooldown SHOULD be invalidated and reevaluated.

### 9.6 Pair-family cooldown

Define:

```text
pair_family_key = stable_hash(
  sorted(family_id_a, family_id_b)
  + dominant_recall_channel
)
```

Repeated lexical/obvious rejects for the same family pair should cause exponential cooldown:

```text
2 rejects / 7d -> 72h
3 rejects / 14d -> 7d
4+             -> 14d cap
```

Do not use an overly broad key such as just `(domain_a, domain_b)`, which would suppress unrelated valuable pairs.

### 9.7 Soft rejection penalty

Qualitative rejections should decay rather than hard block.

Suggested:

```text
penalty(t) = base_penalty * exp(-age_days / half_life_days)
```

Default half-life: 14 days.

Accepted or delivered candidates should apply a negative penalty / reset for the exact pair family so the system can recover from earlier misclassification.

---

## 10. Agent-specific candidate semantics

### 10.1 Serendipity

A model-stage serendipity candidate SHOULD already satisfy all of the following before the LLM sees it:

- both evidence units have substantive content;
- provenance is usable;
- no required verification is missing;
- it is not an exact/near duplicate;
- the pair is not merely the same topic with no mechanism delta;
- it has at least one nontrivial recall path;
- it contributes to diversity / exploration or ranks strongly under bridge features.

The LLM then decides whether the relation is genuinely surprising and explanatory.

The retrieval layer MUST NOT attempt to fully automate “serendipity.” Its purpose is to generate a **better search frontier**.

### 10.2 Intelligence

Intelligence candidate formation is asymmetric:

```text
external update / world evidence
            x
personal hook / question / belief / project / decision
```

The model should not receive arbitrary “news + interest keyword” pairs.

Before LLM judging, each pair SHOULD have one explicit proposed relation type and evidence supporting that relation.

Example:

```json
{
  "relation_type": "updates_belief",
  "world_evidence_id": "...",
  "personal_evidence_id": "...",
  "recall_channels": ["semantic", "entity"],
  "verification_state": "independently_supported"
}
```

---

## 11. ContextPack changes

Do not break the existing top-level ContextPack version unless required by current schema rules. If compatible, add a retrieval block; otherwise introduce `*.context-pack.v2` with an explicit migration.

Required retrieval diagnostics per candidate:

```json
{
  "retrieval": {
    "channels": ["semantic", "temporal", "explore"],
    "channel_ranks": {
      "semantic": 4,
      "temporal": 11
    },
    "fused_score": 0.083,
    "features": {
      "semantic_similarity": 0.71,
      "lexical_overlap": 0.03,
      "domain_distance": 1.0,
      "temporal_distance_days": 824,
      "mechanism_delta": 0.62,
      "exploration_bonus": 0.9
    },
    "strata": {
      "time_a": "archive",
      "time_b": "recent",
      "domain_a": "compiler",
      "domain_b": "personal-process",
      "source_type_a": "note",
      "source_type_b": "diary"
    },
    "cooldown": {
      "active": false,
      "penalty": 0.0
    }
  }
}
```

This metadata is for model context only when useful. Full operational traces may remain outside the prompt to save tokens.

---

## 12. Prepare / complete lifecycle

### 12.1 `prepare`

`prepare` SHOULD execute:

```text
1. read eligible evidence metadata
2. choose seed strata and underexplored families
3. recall by independent channels
4. union + dedupe candidate pairs
5. compute pair features
6. apply deterministic hard filters
7. apply cooldown policy / rejection penalties
8. rank by agent profile
9. diversity/MMR selection
10. build ContextPack
11. record retrieval-run summary
```

### 12.2 `complete`

`complete` SHOULD:

```text
1. ingest model decision for each candidate
2. ingest gate/dedupe/delivery outcome
3. append candidate decision / rejection events
4. update derived family exploration state
5. update derived cooldown state
6. update delivery history / duplicate penalty inputs
7. emit stage metrics and health diagnostics
```

If `complete` fails after the append-only event is written, derived state must be rebuildable by replay.

---

## 13. Storage additions

Prefer extending the existing SQLite cognitive index. Suggested derived tables/materialized views:

### 13.1 `evidence_embeddings`

```text
evidence_id TEXT
model_id TEXT
text_hash TEXT
dim INTEGER
vector BLOB / sidecar_ref
created_at TEXT
PRIMARY KEY (evidence_id, model_id, text_hash)
```

### 13.2 `evidence_family_state`

```text
family_id TEXT PRIMARY KEY
last_explored_at TEXT
explore_count INTEGER
last_llm_seen_at TEXT
llm_seen_count INTEGER
accepted_count INTEGER
delivered_count INTEGER
updated_at TEXT
```

### 13.3 `retrieval_runs`

```text
run_id TEXT PRIMARY KEY
agent TEXT
run_seed TEXT
index_snapshot_id TEXT
eligible_evidence_count INTEGER
eligible_family_count INTEGER
seed_count INTEGER
raw_pair_count INTEGER
hard_filtered_count INTEGER
postfilter_count INTEGER
llm_candidate_count INTEGER
model_accepted_count INTEGER
delivered_count INTEGER
started_at TEXT
completed_at TEXT
```

### 13.4 `cooldown_state`

Derived from append-only rejection events:

```text
scope_kind TEXT        # anchor | template | pair_family
scope_key TEXT
reason_code TEXT
reject_count INTEGER
cooldown_until TEXT
penalty REAL
last_reject_at TEXT
last_positive_at TEXT
PRIMARY KEY(scope_kind, scope_key, reason_code)
```

Do not treat `cooldown_state` as authoritative; it must be reconstructable.

---

## 14. Configuration

Suggested shape:

```yaml
candidate_retrieval:
  version: v0.6
  enabled: true
  shadow_mode: false

  embedding:
    enabled: true
    provider: sentence_transformers
    model: intfloat/multilingual-e5-small
    normalize: true
    batch_size: 32

  lexical:
    enabled: true
    engine: sqlite_fts5
    rrf_k: 60

  hard_filter:
    min_effective_chars: 80
    min_effective_tokens: 24
    reject_structure_only: true
    reject_stopword_only_collision: true
    reject_unverified_source: true
    same_topic_semantic_threshold: 0.90
    same_topic_entity_threshold: 0.50
    mechanism_delta_floor: 0.10

  sampling:
    max_seed_units_per_family: 1
    max_pair_units_per_family: 2
    time_buckets_days: [14, 90, 365]
    deterministic_seed: true

  cooldown:
    lexical_anchor_min_rejects: 3
    lexical_anchor_window_days: 7
    lexical_anchor_hours: [24, 72, 168, 336]
    template_min_rejects: 2
    pair_family_min_rejects: 2
    qualitative_penalty_half_life_days: 14

  profiles:
    serendipity:
      exploration_reserve: 0.20
      llm_pair_budget: 32
      lexical_weight_cap: 0.15
      prefer_cross_domain: true
      prefer_cross_time: true

    intelligence:
      exploration_reserve: 0.10
      llm_pair_budget: 40
      require_personal_hook: true
      require_world_verification_when_marked: true
```

All thresholds MUST be surfaced in run metadata so offline evaluation can reproduce the decision path.

---

## 15. Observability

A 50-hour silence is not itself a sufficient diagnostic. v0.6 MUST record where candidates disappear.

### 15.1 Stage funnel

Per run:

```text
eligible evidence
eligible families
selected seeds
raw recalled pairs
hard-filter survivors
cooldown survivors
ranked survivors
LLM candidates
LLM accepted
final gate accepted
delivered
```

### 15.2 Coverage metrics

Record:

- unique evidence families explored per run;
- rolling 7d / 30d family coverage;
- coverage by time bucket;
- coverage by domain;
- coverage by source type;
- fraction of LLM candidates from never-before-seen families;
- fraction selected through non-lexical channels;
- prefix-bias diagnostic: distribution of selected evidence across evidence-ID/order quantiles.

### 15.3 Waste metrics

Record:

- `%` of raw candidates removed by each hard-filter reason;
- `%` of LLM rejects diagnosed as pure lexical collision;
- repeated anchor reject rate;
- repeated pair-family reject rate;
- model tokens spent on candidates later classified as deterministic noise;
- top noisy anchors by count, storing hashes/normalized labels only as privacy policy permits.

### 15.4 Silence diagnostics

When no delivery occurs, classify the run:

```text
NO_ELIGIBLE_EVIDENCE
RECALL_STARVATION
HARD_FILTER_STARVATION
COOLDOWN_STARVATION
MODEL_REJECTION
DELIVERY_GATE_REJECTION
NORMAL_SILENCE
```

Do not automatically relax thresholds. Emit health diagnostics so tuning is evidence-based.

### 15.5 Recommended health alerts

Alert/log warning when any of the following persists:

- zero post-filter candidates for 3 consecutive scheduled runs;
- >80% of LLM budget comes from one evidence family/domain pair;
- >40% of LLM rejects are lexical collisions for 5 runs;
- rolling 7d explored-family coverage is below configured target;
- embedding index lag exceeds one indexing cycle;
- more than 20% of otherwise viable intelligence candidates fail verification.

---

## 16. Failure behavior and fallbacks

### 16.1 Embedding unavailable

Fallback to:

```text
FTS/BM25 + entity + temporal + domain + exploration
```

Do not revert to “shared keyword required.”

Emit `embedding_degraded=true` in run metadata.

### 16.2 Empty or stale index

Do not silently produce a normal “no delivery.” Emit a retrieval health failure when index freshness is outside policy.

### 16.3 Over-filtering

If hard filtering causes starvation, the diagnostic must identify the dominant reason code. The runtime MUST NOT automatically bypass `UNVERIFIED_SOURCE`, duplicate, or structure-only filters just to meet a delivery target.

### 16.4 Cooldown overreach

Every cooldown must expire, be inspectable, and be overridable by a stronger independent recall path. Lexical-anchor cooldown is channel-specific by default.

---

## 17. Testing requirements

### 17.1 Unit tests

Must cover:

- keyword-free semantic pair survives recall;
- stopword-only lexical collision is removed;
- title-only / template-only fragment is removed;
- short but explicitly allowed structured event is handled correctly;
- unverified `requires_source_verification` candidate is removed;
- independent source family satisfies verification;
- same-topic/no-mechanism-delta rule triggers conservatively;
- anchor cooldown activates at threshold and expires;
- anchor cooldown suppresses lexical contribution but not semantic recall;
- template cooldown invalidates when content/extractor version changes;
- pair-family cooldown key is symmetric;
- qualitative rejection penalty decays;
- accepted candidate reduces relevant penalty.

### 17.2 Sampling tests

Must prove:

- reordering `evidence_id` does not materially change stratum coverage;
- a corpus larger than 160 rows produces candidates from outside the first 160 rows;
- fixed run seed + fixed snapshot gives identical selection;
- previously unexplored families are preferred;
- repeatedly running the selector eventually rotates through eligible families;
- one large recent domain cannot permanently starve archive/minority strata;
- per-family cap is respected.

### 17.3 Integration tests

Test full `prepare -> judge fixture -> complete` for:

- `serendipity`;
- `intelligence`;
- embedding disabled;
- all evidence filtered;
- mixed verified/unverified external material;
- cooldown replay from append-only rejection events;
- failed `complete` followed by derived-state rebuild.

### 17.4 Offline evaluation set

Create a small curated benchmark with:

- known valuable cross-time connections that have low keyword overlap;
- pure lexical collisions;
- same-topic obvious pairs;
- cross-domain but empty analogies;
- title/template fragments;
- OCR/noisy fragments;
- unverified clips;
- verified external updates connected to active personal questions;
- already-delivered or user-explicit connections.

Measure Recall@K for known valuable pairs and noise rate before the LLM.

---

## 18. Acceptance criteria

v0.6 is ready to enable for production `serendipity` when all of the following are true:

1. **No lexical admission gate**
   - tests demonstrate that a zero-keyword-overlap pair can reach the LLM through a non-lexical channel.

2. **Prefix bias removed**
   - on a fixture with >160 evidence rows, selected candidates demonstrably include evidence outside the previous prefix;
   - selection distribution is driven by strata/family state, not `evidence_id` order.

3. **Deterministic noise is removed before the model**
   - title/template/short/stopword-only/unverified fixtures do not enter the LLM ContextPack.

4. **Exploration rotates**
   - repeated runs over a static corpus increase unique-family coverage instead of repeatedly selecting the same family set.

5. **Rejection learning works**
   - repeated lexical-collision anchors enter cooldown and reduce repeated LLM waste;
   - semantic/entity recall can still surface a strong candidate involving the same topic.

6. **Observability is sufficient**
   - every no-delivery run can be classified by stage;
   - metrics report recall channels, filter reasons, strata coverage, and cooldown impact.

7. **No forced-noise regression**
   - final delivery gate behavior is unchanged;
   - v0.6 does not add “deliver something after N hours” logic.

8. **Shadow evaluation improves upstream quality**
   - compared with the current implementation, the v0.6 candidate set shows higher curated-set Recall@K and fewer deterministic-noise candidates per model token budget.

For `intelligence`, additionally require:

9. every LLM-stage candidate has an explicit personal hook / model-update relation;
10. verification-required external evidence cannot reach the LLM unverified.

---

## 19. Rollout plan

### Phase 0 — instrumentation only

Add stage counters to the existing pipeline without changing selection. Establish baseline for:

- candidate counts;
- lexical-collision rejects;
- evidence-family repetition;
- current 160-row prefix coverage;
- no-delivery stage attribution.

### Phase 1 — local embeddings + hybrid recall in shadow mode

Build embeddings and run hybrid recall without changing production candidate input. Compare recalled sets and Recall@K offline.

### Phase 2 — deterministic hard filters

Enable structure/body/stopword/duplicate/verification filters. Keep model judge unchanged.

### Phase 3 — stratified family-aware sampling

Replace `_candidate_rows()` prefix logic. Enable time/domain/source/family rotation.

### Phase 4 — rejection learning and cooldown

Append rejection events, derive cooldown state, and apply channel-scoped penalties.

### Phase 5 — enable v0.6 for serendipity

Run shadow vs production comparison first, then switch candidate source behind a feature flag.

### Phase 6 — enable intelligence profile

Reuse retrieval core but enforce asymmetric world-update x personal-hook semantics and verification policy.

### Phase 7 — tuning

Tune budgets, weights, thresholds, time buckets, and cooldown windows using observed funnel metrics and the offline evaluation set.

---

## 20. Feature flags and rollback

Required feature flags:

```text
candidate_retrieval_v06_enabled
candidate_retrieval_v06_shadow
candidate_retrieval_embeddings_enabled
candidate_retrieval_hard_filter_enabled
candidate_retrieval_stratified_sampling_enabled
candidate_retrieval_cooldown_enabled
```

Rollback must be possible independently for each stage.

The old candidate path may remain temporarily available for A/B or shadow comparison, but once v0.6 is accepted it should not remain the implicit fallback for ordinary failures because its prefix bias is a correctness problem. Explicit degraded mode should instead use v0.6 sampling without embeddings.

---

## 21. Implementation notes for Codex

When implementing, first locate and document the current call graph around `_candidate_rows()`, ContextPack construction, model decision parsing, rejection logging, and `prepare/complete`. Do not assume names from this specification map 1:1 to current modules.

Prefer small components with pure/testable interfaces:

```text
EvidenceFeatureProvider
SeedSampler
RecallChannel
PairFeatureBuilder
HardFilterPipeline
HybridRanker
DiversitySelector
CooldownPolicy
RetrievalRunLogger
```

A recommended functional boundary is:

```python
def build_candidates(
    *,
    agent_profile: str,
    evidence_snapshot: EvidenceSnapshot,
    run_seed: str,
    budget: CandidateBudget,
) -> CandidateBatch:
    ...
```

`CandidateBatch` should include both selected candidates and aggregate diagnostics. Full rejected candidate payloads need not be retained in normal mode if privacy/cost policy prefers hashes + reason summaries.

Do not put embedding generation on the critical path for unchanged evidence. Index incrementally by content hash and model id.

Do not use LLM calls for the hard-filter pipeline.

Do not add an external API dependency solely for retrieval.

---

## 22. Expected behavioral change

After v0.6, a typical serendipity run should look qualitatively different:

**Before:**

```text
fixed evidence prefix -> keyword/shared-token pair generation -> shuffle -> LLM rejects obvious lexical collisions -> silence
```

**After:**

```text
stratified seeds across the corpus
    -> semantic + lexical + entity + temporal + domain + exploration recall
    -> deterministic noise removal
    -> rejection-aware cooldown
    -> diversity selection
    -> compact set of high-information, varied candidate pairs
    -> LLM judges actual connections rather than cleaning retrieval noise
```

The intended result is not “more notifications at any cost.” It is a higher probability that every scheduled run gives the model a genuinely useful frontier to reason over, while preserving silence when no candidate is good enough to deliver.

---

## 23. v0.6 decision summary

v0.6 makes four concrete architectural decisions:

1. **Recall becomes hybrid and local-first.** Embeddings are added, BM25 remains, and lexical overlap loses veto power.
2. **Deterministic garbage is filtered before the model.** Structural fragments, insufficient body, meaningless lexical collisions, trivial same-topic pairs, duplicates, and unverified required sources do not consume LLM budget.
3. **Sampling becomes coverage-oriented.** Time/domain/source strata plus least-recently-explored evidence families replace the `evidence_id` prefix + shuffle behavior.
4. **Rejections become retrieval feedback.** Repeated bad anchors/templates/pair families cool down with scoped, expiring penalties instead of wasting every run.

Model replacement should be reconsidered only after these changes are deployed and measured. If candidate Recall@K, pre-LLM precision, and corpus coverage improve while model-stage acceptance still remains poor, that will be evidence for changing the judge model. Until then, model swapping would confound retrieval quality with reasoning quality.
