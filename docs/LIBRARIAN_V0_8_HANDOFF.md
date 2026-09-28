# Librarian v0.8 handoff — 2026-09-28

The requested goal is **not complete**. Development commits are on `main`.
Create `release-v0.8` only after the acceptance evidence below is complete.

## First-book production run — 2026-09-28

- The user paired the China-region `feishu:librarian` bot. A concrete
  channel/account/sender-to-owner mapping is active; its key remains in
  OpenClaw's write-only secret store. The user supplied an EPUB for
  《社会理论二十讲》 (ISBN 9787208171411), stored privately under
  `var/librarian/source-books/`.
- The original five-image Feishu message was recovered from OpenClaw's staged
  transcript through the same `acceptMessage` hook and idempotent bridge used
  for live intake. The production store contains one five-capture batch,
  five original captures, one Work/Edition/BookInstance/session chain, and
  versioned observations and processing runs. A user review found that one
  photographed sheet includes original-book pp.39 and 40; another includes
  pp.42 and 43. The worker now segments marks by visible page number and
  retains previous traces as superseded revisions when reprocessing. The
  production reprocessing completed with ten active traces on pp.39–44;
  the p.39 trace ends at “社会学思想的核心部分。”
  Replaying that event kept the five source items and capture IDs unchanged.
- Local RapidOCR and the supplied EPUB aligned printed lines; a narrow stroke
  detector found marks; only four small handwriting crops used the configured
  OpenClaw image model. The agent wrote the review note under the user's requested Vault path
  `2Area/40 学习与阅读/阅读笔记/社会理论二十讲.md`, then sent one Feishu
  review message. The user requested no images in Vault; earlier page images
  were removed and future exports include capture IDs only. Trace metadata is
  stored in hidden HTML elements. A corrected Feishu review message was sent
  after the database and Vault were updated. The user's content review is still pending.
- `librarian_search` queried this production store through the active trusted
  sender mapping and found a p.41 note; the same call with an unmapped sender
  did not expose the tool. A CLI-synthesized agent turn could not establish a
  Feishu session route, so a real inbound question and evidence-backed agent
  answer remain unverified.
- The user deferred the separate four-photo pp.159/166/171/184 acceptance
  batch and `source-design.txt`. Do not substitute similarly numbered Vault
  orphans or the first-book photos for those inputs.

## Verified locally

- The canonical contract has 77 definitions, 18 entry schemas, 42 positive
  fixtures and 43 negative fixtures. `python3
  agents/librarian/runtime/tests/validate_contracts.py` passes. The absent
  original `source-design.txt` prevents a source-package comparison.
- Capture storage, sessions, versioned traces, search, digital export parsing,
  transactional events, candidate state, and separated exception queues have
  synthetic tests. The latest broad run passed 319 tests, skipped 71 and
  deselected one existing test requiring unavailable `historian.summarization`.
- Koodo's native local SQLite store was read in read-only mode on this PC:
  71 book records and 118 note records were found, with all 118 notes linked
  to one registered book key. An ephemeral Librarian import created 118 traces;
  replay made no new traces, and raw evidence, search and owner isolation
  passed. Private note contents and the acceptance store were not committed.
- The configured Obsidian WeRead plugin's Agent API returned one real book with
  38 highlights and one review. `runtime/weread_native.py` imported all 39
  records into a temporary Library, retained exact JSON evidence, and replayed
  with no duplicates. Owner-scoped search passed. Synthetic tests cover source
  changes, removals, pagination, and correction conflicts. No private text,
  book IDs, or API key were committed.
- The OpenClaw intake plugin reports `loaded`, with one `message_received`
  typed hook, one mapped search tool, one recovery service and no diagnostics.
  The dedicated `librarian` PAP profile and OpenClaw agent are registered;
  the trusted Feishu sender mapping is active.
- A live synthetic reading-history question exposed a profile gap: the agent
  searched its workspace and overclaimed that no book existed, although the
  private Librarian store was not searched. The profile now distinguishes
  workspace memory from owner-scoped Librarian evidence. A second live turn
  correctly said it could not verify the annotation without that search port
  and did not claim the book or note was absent.
- The OpenClaw plugin now registers a `librarian_search` tool that is absent
  unless the dedicated agent's runtime channel/account/sender matches exactly
  one trusted owner mapping. The local Gateway reports the plugin loaded with
  one hook, one tool and no diagnostics; RPC probe is healthy. Synthetic tests
  cover mapping denial and owner-scoped search bridge results. The mapped
  search tool was also called against the first-book production store.
- The dedicated OpenClaw Librarian agent is now bound to a separate Feishu
  account named `librarian`. Its App Secret is in OpenClaw's write-only secret
  store, while config holds a SecretRef. The China-region WebSocket account is
  connected and the credential probe passes; DM pairing is enabled and group
  chats are disabled for this account. The sender is paired and mapped.
- `runtime/vision.py` sends an EXIF-oriented derivative through Claude
  Messages, OpenAI-compatible Chat Completions, or the configured OpenClaw
  model route. The pipeline stores the original, derivative, transform and raw
  model JSON. `zai/glm-5.3-flash` accepted a generated synthetic page; after
  tightening the JSON prompt, a live `process_capture` run in a temporary
  Library produced one underline and one margin-note trace and persisted the
  raw response. This does not establish accuracy on the four real photos.

## Required before release

1. Obtain the four annotated physical photos for p.159, p.166, p.171 and
   p.184, plus the original `source-design.txt` if it exists. Keep private
   image bytes outside Git. Similarly numbered Evernote `_orphan` files in the
   Vault have not been established as these inputs; `_orphan_171.jpg` was
   visually checked and is unrelated.
2. The configured OpenClaw vision route passed a live synthetic image request.
   Run extraction against the four real photos and verify
   the twelve trace groups, source regions, `Parsons?`, page attribution,
   progress evidence and later Weber/Parsons retrieval specified in §38.1.
3. DM pairing, trusted mapping, a real five-image batch, idempotent replay,
   and a mapped search call against production traces are verified. Obtain a
   real inbound question from the mapped sender and verify that the agent
   returns a relevant trace, edition/page and original evidence without
   overclaiming. Human review of the first-book note remains pending.
4. Verify actual app-driven create/edit/delete and periodic invocation under
   the trusted owner for both WeRead and Koodo before claiming live sync.
   Real upstream record mapping and replay were exercised on this PC for both
   sources; Markdown exports remain separate adapters.
5. Connect and verify an actual knowledge service writer if claiming the
   candidate promotion stage. The port exists but has no configured writer.
6. Audit all AC-01 through AC-26 against runtime evidence, not solely schema
   fixtures. Update this handoff and `LIBRARIAN_REPO_MAPPING.md`; then cut and
   push `release-v0.8` from the verified `main` commit.

## Resume points

- Specification: `docs/SPEC_v0.8_Librarian.md` (§37–39 for milestones, tests
  and design rules).
- Runtime: `agents/librarian/runtime/README.md`.
- Gateway plugin: `agents/librarian/openclaw-plugin/README.md`.
- Current integration boundaries: `docs/LIBRARIAN_REPO_MAPPING.md`.

## Continue on another PC

1. Pull `main` from `origin` and read this document plus the runtime and
   OpenClaw plugin READMEs. The handoff commit is on `main`; there is no
   `release-v0.8` branch yet. Install the repo Python dependencies with
   `python3 -m pip install -e .` in a virtual environment.
2. Run `PYTHONPATH=. python3 -m pytest tests/test_librarian_vision.py
   tests/test_librarian_pipeline.py tests/test_librarian_gateway_bridge.py -q`,
   `python3 agents/librarian/runtime/tests/validate_contracts.py`, and
   `node --test agents/librarian/openclaw-plugin/test.mjs` from the repo root.
3. Install the local plugin using the commands in
   `agents/librarian/openclaw-plugin/README.md`. Set that PC's absolute
   `repoRoot`, private `stateRoot`, `vaultRoot` and OCR-capable `python`.
   Keep `ownerMappings: []` until that PC's dedicated profile and trusted
   sender identity are ready.
4. Runtime captures and SQLite data live under `var/librarian/`, outside Git.
   Copy that private directory separately only if existing local captures must
   be continued on the new PC; preserve file permissions and stop any writer
   before copying. Provider credentials and OpenClaw settings are also local
   machine configuration and are not in this repository.

The original Obsidian Vault is likewise external to this Git repository. Its
path on this PC is `/home/xingzeng/文档/Obsidian/Second_Brain`; configure
the new PC's actual Vault path separately.

## Current PC verification — 2026-09-28

- `agents/librarian/agent.yaml` loads through `pap.spec.load_spec` with no
  proactive jobs. The OpenClaw `librarian` agent has one binding to the
  separate `feishu:librarian` account; its workspace SOUL matches the
  repository profile. The account credential probe passes. DM pairing and
  trusted sender mapping were completed for the first-book run.
- `openclaw plugins inspect pap-librarian-intake --runtime --json` reports
  `loaded`, one typed `message_received` hook, and no diagnostics. The Gateway
  service is running and its CLI RPC probe succeeds. The mapped first-book
  image batch and the worker service have been exercised.
- The current focused pipeline/digital/owner-isolation/native-adapter run
  passed 31 Python tests. Contract validation passed 77 definitions,
  18 entries, 42 positive and 43 negative cases. Earlier runs passed 30
  vision/pipeline/bridge tests, 20 store/digital/command/event/knowledge/native-Koodo
  tests, and two Node plugin tests. These are synthetic tests.
- `ANTHROPIC_API_KEY`, `ANTHROPIC_AUTH_TOKEN`, and `ANTHROPIC_BASE_URL` were
  unset in this shell. The OpenClaw Z.AI credential is a write-only secret
  reference. Direct `openclaw infer model run` and the Librarian `process_capture`
  path both passed with one generated synthetic page through `zai/glm-5.3-flash`.
  The separate §38.1 four-photo accuracy gate remains unverified; the
  first-book photos have been processed and await user review.

## AC-01–26 runtime evidence audit

`Local` means a synthetic executable test of the indicated behavior. It does
not mean the real-photo, live Gateway, upstream, or service acceptance is done.

| AC | Current evidence | Status / remaining proof |
|---|---|---|
| 01–03 | `test_librarian_store.py` capture retry/conflict/same bytes and `test_librarian_gateway_bridge.py` source identity; the production five-image message replay returned the original capture IDs | Live first-book replay verified; §38.1 batch still pending |
| 04 | `test_same_title_two_copies_requires_explicit_catalog_resolution` covers the domain; `test_librarian_worker.py` now rejects automatic binding when multiple copies share one edition without a selected session | Local ambiguity guard; first-book unique copy resolved from photographed ISBN plus supplied EPUB |
| 05 | `test_conflicting_explicit_session_keeps_original_and_observation` | Local; real visible-title extraction pending |
| 06 | `test_session_selection_and_soft_affinity_stay_in_conversation_scope` | Local |
| 07 | `test_unreadable_page_number_keeps_local_trace_and_original`; first-book OCR resolved photographed pp.40, 41, 43 and 44 | Live first-book pages; real 137/139 ambiguity pending |
| 08–09 | `test_catalog_owner_chain_and_session_progress` covers explicit progress evidence | Local; four-photo session pending |
| 10 | `test_trace_crop_uses_oriented_original_and_stays_within_page` renders crops from an EXIF-rotated two-page photo; `test_cross_page_text_link_is_rejected_and_observation_link_keeps_traces_separate` checks direct text links and trace separation | Local geometry; real-photo acceptance pending |
| 11 | `test_uncertain_ordinary_underline_is_saved_without_content_review`; first-book long underlines were aligned to EPUB sentences and saved without per-trace interruption | User accuracy review pending; §38.1 pending |
| 12 | `test_opt_in_symbol_signal_and_important_content_review` | Local |
| 13 | `test_printed_and_margin_punctuation_do_not_trigger_symbol_vocabulary` | Local for correctly typed regions; model misclassification on real photos pending |
| 14 | `test_correction_adds_revision_and_keeps_evidence` | Local |
| 15–16 | New-extractor reconciliation and late-event index tests | Local |
| 17 | `test_object_write_failure_does_not_acknowledge_capture_and_retry_succeeds` injects a failed atomic object write and retries the same key | Local |
| 18 | Invalid JSON, unfinished reply, and `test_provider_timeout_keeps_original_and_records_failed_run` | Local; live provider fault response pending |
| 19–20 | Outbox retry and index rebuild tests | Local |
| 21 | `test_foreign_ids_cannot_read_or_mutate_owner_records` probes foreign trace, capture and candidate IDs; the mapped production search returned one p.41 trace while an unmapped sender had no tool | Local adversarial matrix and mapped tool call passed; real inbound question pending |
| 22 | `test_explicit_annotation_link_groups_trace_without_inventing_authorship` | Local |
| 23 | `test_same_query_returns_common_hits_from_all_three_media` returns physical, WeRead and Koodo SearchHits for one query without upstream-specific objects; 118 actual Koodo notes and 39 actual WeRead records were imported and searched in temporary stores, with replay and raw evidence verified | Three-source contract passed locally; app-driven and periodic live sync pending |
| 24 | The mapped-only `librarian_search` tool returned a production p.41 note with source and page in a trusted-context call. A CLI synthetic agent turn could not resolve the Feishu session route. | Partial: real inbound search-to-answer and evidence-backed reply still pending |
| 25 | `test_source_correction_during_external_write_does_not_publish_promotion` | Local mock; actual knowledge writer pending |
| 26 | `test_candidate_requires_explicit_trigger_and_promotion_confirms_external_write` | Local |

Release evidence remains incomplete. In particular, the §38.1 four-photo
batch, twelve trace groups and later Weber/Parsons retrieval have not been
run. No `release-v0.8` branch or tag should be cut from this state.

Do not use the synthetic photo tests or fixture counts as proof of visual
recognition accuracy or a finished release.
