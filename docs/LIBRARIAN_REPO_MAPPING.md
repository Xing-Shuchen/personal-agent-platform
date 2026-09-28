# Librarian v0.8 repository mapping

This maps `SPEC_v0.8_Librarian.md` §40 to the repository as inspected on
2026-09-28. The specification is a draft for a physical reading ingestion
system; the referenced `references/source-design.txt`, `schemas/`, `examples/`,
and validation report did not accompany the standalone file in this worktree.

| Responsibility | Existing PAP component | Implementation boundary |
|---|---|---|
| Agent identity, profile, scheduling | `agents/*/agent.yaml`, `pap/spec.py`, `pap/scheduler.py` | Add a Librarian agent only when its invocation and delivery behavior are defined. |
| Gateway invocation | `pap/run.py` invokes OpenClaw turns; no typed attachment acceptance API in PAP | A gateway bridge must provide stable source event/item IDs and trusted upload bytes. A text-only agent invocation cannot claim to accept photos. |
| Work, Edition, BookInstance, ReadingSession, capture, trace | None | Librarian-owned transactional state under `agents/librarian/runtime/`; runtime files under `var/librarian/`. |
| Original image and raw model output | No general object store. `pap/artifact.py` is append-only JSONL without blob durability or access control | Add a Librarian-local content-addressed object port; persist bytes before a capture receipt. Do not put private images in Git or the shared artifact log. |
| Domain events | `pap/artifact.py` and `paplog` are observability/inter-agent records, not transactional domain outboxes | Store domain outbox rows in the same SQLite transaction as trace/session changes. A publisher can bridge events later. |
| Migrations | World Historian has an agent-specific SQLite migration pattern | Use agent-local SQLite migrations. Do not insert reading entities into Chronicle. |
| Search | `pap/cognition.py` indexes Markdown evidence, with WeRead note recognition | Librarian needs a current-trace, owner-filtered index with original image provenance. Existing cognition indexing does not provide it. |
| Digital adapters | Vault has WeRead and Koodo Markdown exports; `pap/cognition.py` recognizes some WeRead headings | `agents/librarian/runtime/digital.py` parses observed export shapes into ReadingTrace. Markdown shape is not proof of platform API or live sync semantics. |
| Knowledge promotion | Cognition stores retrieval evidence; no Librarian KnowledgeObject write port | Keep candidates separate and optional. No automatic promotion from ordinary highlights. |

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
