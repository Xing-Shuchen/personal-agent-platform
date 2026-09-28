# Librarian v0.8 repository mapping

This maps `SPEC_v0.8_Librarian.md` §40 to the repository as inspected on
2026-09-28. The specification is a draft for a physical reading ingestion
system; the referenced `references/source-design.txt`, `schemas/`, `examples/`,
and validation report did not accompany the standalone file in this worktree.

| Responsibility | Existing PAP component | Implementation boundary |
|---|---|---|
| Agent identity, profile, scheduling | `agents/librarian/agent.yaml`, `agents/librarian/profile/`, `pap/spec.py` | Dedicated Librarian profile is registered locally with no proactive jobs; OpenClaw `librarian` has zero channel bindings. Image intake is the separate hook. |
| Gateway invocation | `pap/run.py` invokes OpenClaw turns; no typed attachment acceptance API in PAP | `agents/librarian/openclaw-plugin/` observes staged OpenClaw image media and sends stable source IDs and trusted bytes to `runtime/gateway_bridge.py`. Live intake requires an explicit sender-to-owner mapping and Gateway reload. |
| Work, Edition, BookInstance, ReadingSession, capture, trace | None | Librarian-owned transactional state under `agents/librarian/runtime/`; runtime files under `var/librarian/`. |
| Original image and raw model output | No general object store. `pap/artifact.py` is append-only JSONL without blob durability or access control | Add a Librarian-local content-addressed object port; persist bytes before a capture receipt. Do not put private images in Git or the shared artifact log. |
| Domain events | `pap/artifact.py` and `paplog` are observability/inter-agent records, not transactional domain outboxes | Store domain outbox rows in the same SQLite transaction as trace/session changes. A publisher can bridge events later. |
| Migrations | World Historian has an agent-specific SQLite migration pattern | Use agent-local SQLite migrations. Do not insert reading entities into Chronicle. |
| Search | `pap/cognition.py` indexes Markdown evidence, with WeRead note recognition | Librarian needs a current-trace, owner-filtered index with original image provenance. Existing cognition indexing does not provide it. |
| Digital adapters | Vault has WeRead and Koodo Markdown exports; `pap/cognition.py` recognizes some WeRead headings. This PC also has native Koodo `books.db` and `notes.db`, and the Obsidian WeRead plugin has a configured Agent API key. | `runtime/digital.py` parses observed exports. `runtime/koodo_native.py` reads Koodo SQLite records read-only; initial import/replay was verified on 118 real native notes. `runtime/weread_native.py` reads the WeRead Agent API, maps stable highlight/review IDs, and supports replay, updates, removals and correction conflicts. A real upstream book yielded 38 highlights and one review; first import/replay, raw evidence and owner isolation passed in a temporary store. App-driven changes and periodic invocation remain unverified. |
| Physical image extraction | No existing PAP vision pipeline for annotated book pages | `runtime/vision.py` prepares a traceable EXIF-oriented derivative for Claude Messages or OpenAI-compatible Chat Completions. Both transports have mock tests. The local OpenClaw Z.AI route advertises image input, but its write-only credential has not reached this runtime; live vision remains unverified. `runtime/pipeline.py` renders owner-scoped crops from the original. Direct mark-to-print links across pages are rejected; explicit cross-page observation links remain separate traces. Synthetic rotated two-page geometry passes; real photo acceptance remains open. |
| Exception review | No shared Librarian review UI | `runtime/review.py` returns separate owner-scoped catalog resolution and important-content queues. User corrections close content review after the uncertain fields are checked. |
| Knowledge promotion | Cognition stores retrieval evidence; no Librarian KnowledgeObject write port | `runtime/knowledge.py` supports provenance-bound candidates, decisions and an idempotent writer port. No actual knowledge service writer is configured; ordinary highlights do not auto-promote. |

## Immediate integration decisions

- JSON Schema is the normative contract. Runtime validation and fixtures must
  load that file instead of maintaining another independent model definition.
- `owner_id` comes from a trusted caller context. Never treat a model-produced
  or attachment-supplied owner string as authorization.
- The `ReadingTrace` boundary is common to physical, WeRead, and Koodo. A
  `PageCapture` stays immutable evidence; resolution and observations are
  separate records.
- All commits stay on `main`; `release-v0.8` is a pointer to a verified
  milestone, never a development branch.

## Evidence still needed for the full specification

The source-design attachment and real annotated photos cited by the draft are
absent from this repository. The 18 model entry schemas and 42 positive/43
negative synthetic fixtures now exist under `agents/librarian/runtime/`. The
canonical schema has 77 definitions after extracting repeated nested types;
their names cannot be compared to the unavailable source-design package. The full
M1 image acceptance test and M2 live adapter test cannot be claimed without
those inputs. A synthetic extractor can verify persistence, normalization, and
retrieval behavior, but cannot establish OCR or handwriting accuracy.

On this PC, the local OpenClaw intake plugin is installed and loads one
`message_received` hook, with `ownerMappings: []`. The Librarian profile and
unbound OpenClaw agent exist, but no trusted channel/account/sender identity
has been established for automatic image intake. Leave the mapping empty until
that identity is known. The live Gateway batch/replay and provider acceptance
remain open; see the AC-by-AC audit in `LIBRARIAN_V0_8_HANDOFF.md`.
