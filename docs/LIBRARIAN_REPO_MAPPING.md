# Librarian v0.8 repository mapping

This maps `SPEC_v0.8_Librarian.md` §40 to the repository as inspected on
2026-09-28. The specification is a draft for a physical reading ingestion
system; the referenced `references/source-design.txt`, `schemas/`, `examples/`,
and validation report did not accompany the standalone file in this worktree.

| Responsibility | Existing PAP component | Implementation boundary |
|---|---|---|
| Agent identity, profile, scheduling | `agents/librarian/agent.yaml`, `agents/librarian/profile/`, `pap/spec.py` | Dedicated Librarian profile is registered locally with no proactive jobs; OpenClaw `librarian` is bound to the dedicated `feishu:librarian` China-region account. DM pairing and trusted sender mapping are active. Image intake is the separate hook. |
| Gateway invocation | `pap/run.py` invokes OpenClaw turns; no typed attachment acceptance API in PAP | `agents/librarian/openclaw-plugin/` observes staged OpenClaw image media and sends stable source IDs and staged file paths to `runtime/gateway_bridge.py`. The bridge durably stores the original bytes. The mapped first-book Feishu batch and idempotent replay passed. |
| Work, Edition, BookInstance, ReadingSession, capture, trace | None | Librarian-owned transactional state under `agents/librarian/runtime/`; runtime files under `var/librarian/`. |
| Original image and raw model output | No general object store. `pap/artifact.py` is append-only JSONL without blob durability or access control | Add a Librarian-local content-addressed object port; persist bytes before a capture receipt. Do not put private images in Git or the shared artifact log. |
| Domain events | `pap/artifact.py` and `paplog` are observability/inter-agent records, not transactional domain outboxes | Store domain outbox rows in the same SQLite transaction as trace/session changes. A publisher can bridge events later. |
| Migrations | World Historian has an agent-specific SQLite migration pattern | Use agent-local SQLite migrations. Do not insert reading entities into Chronicle. |
| Search | `pap/cognition.py` indexes Markdown evidence, with WeRead note recognition | Librarian's current-trace index has owner-filtered search and original provenance. The OpenClaw plugin registers `librarian_search` only for a trusted mapped sender in the dedicated agent, forwarding to `runtime/gateway_search.py`. A mapped search found a real p.41 trace and an unmapped sender had no tool. Real inbound search-to-answer remains unverified. |
| Digital adapters | Vault has WeRead and Koodo Markdown exports; `pap/cognition.py` recognizes some WeRead headings. This PC also has native Koodo `books.db` and `notes.db`, and the Obsidian WeRead plugin has a configured Agent API key. | `runtime/digital.py` parses observed exports. `runtime/koodo_native.py` reads Koodo SQLite records read-only; `runtime/weread_native.py` reads the WeRead Agent API. The live Librarian worker imported 118 Koodo notes and four records from one configured WeRead book, then owner-scoped search found each medium. The gateway schedules five-minute repeats; live repeat and app-driven create/edit/delete still require observation. Other WeRead books are outside the current explicit list. |
| Physical image extraction | No existing PAP vision pipeline for annotated book pages | `runtime/vision.py` retains provider image adapters. `runtime/ocr.py` uses local RapidOCR, the owner-provided EPUB and a stroke detector for the first book, with OpenClaw image inference limited to handwriting crops. It segments multiple original-book pages within one photo. `runtime/worker.py` exports capture references with hidden HTML metadata to the Obsidian review note and sends a Feishu notification. `runtime/pipeline.py` retains original/raw evidence, reconciles revised extractions without overwriting user corrections, and renders owner-scoped crops. The separate §38.1 four-photo acceptance remains open. |
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

The source-design attachment and four §38.1 annotated photos cited by the draft
remain deferred by the user. A different first-book five-photo set was processed
from Feishu and is under user review. The 18 model entry schemas and 42 positive/43
negative synthetic fixtures now exist under `agents/librarian/runtime/`. The
canonical schema has 77 definitions after extracting repeated nested types;
their names cannot be compared to the unavailable source-design package. The full
M1 image acceptance test and M2 live adapter test cannot be claimed without
those inputs. A synthetic extractor can verify persistence, normalization, and
retrieval behavior, but cannot establish OCR or handwriting accuracy.

On this PC, the local OpenClaw intake plugin loads one `message_received` hook,
the mapped-only `librarian_search` tool and a recovery worker service. The
trusted Feishu sender mapping is active. The first-book batch/replay and mapped
search call passed; a real inbound question and the separate §38.1 acceptance
remain open. See the AC-by-AC audit in `LIBRARIAN_V0_8_HANDOFF.md`.
