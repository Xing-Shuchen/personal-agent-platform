# Librarian v0.8 handoff — 2026-09-28

## Current update — 2026-09-29

Latest scope change: printed underline text is accepted with its current EPUB
punctuation expansion. The private review site now offers a handwriting-only
page with 15 note crops and versioned confirm/edit/reject actions; actual user
decisions are deferred to formal use. The production Vault note is grouped by
EPUB chapter and ordered by matched text offset, with page numbers shown only
as source locators. The current book renders under its second chapter, with
73 hidden trace anchors and no embedded photos or page-group headings. Broad
regression checks now pass 516 Python tests, 16 plugin tests and the offline
contracts. See the audit §§14–15 for exact evidence, the refreshed AC-01–26
matrix and remaining gates.

The older first-book counts and RapidOCR path below describe the 2026-09-28
state, not the current runtime. The user authorized clearing all old physical
image-derived results and replacing that path with Bookscan. The 27 retained
captures have 27 original Bookscan runs and 73 active physical traces; 54
identical duplicate runs were marked duplicate after an audit-page fingerprint
bug. The Vault note was rebuilt in the requested reading-note format, without
original images or visible internal IDs. ISBN 9787208171411 supplies the book
metadata.

The private localhost review site lists all 27 pages. Complete reviews can
now be submitted to versioned Librarian records, and the physical worker then
refreshes the Vault. Production human review remains **0/27 pages**. A
production-data copy passed a test review through Vault refresh; no synthetic
review was written to production. The current audit and scope decisions are in
`docs/audits/LIBRARIAN_AUDIT_2026-09-28.md` §12–13.

The user explicitly deferred ordinary new-photo side-mark discovery and the
EPUB sentence-extension boundary decision for this acceptance pass. These are
waived checks, not claims of implementation or specification compliance. The
separate pp.159/166/171/184 inputs and `source-design.txt` also remain deferred
per the user's earlier instruction. Current broad checks: 511 Python tests,
16 plugin tests and offline contract validation pass; Gateway and plugin are
running. Live human page decisions, real inbound delivery checks and remaining
R1–R4/AC evidence are still needed before release.

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
- Native Koodo and one explicitly selected WeRead book are now configured in
  the live OpenClaw Librarian worker. Its first production sync stored 118
  Koodo and four WeRead traces beside the ten physical traces; a second sync
  in an isolated copy made zero duplicates. All three media returned owner-
  scoped production search results. Digital errors are recorded per source
  and do not stop physical intake. The five-minute live repeat and app-driven
  changes still need observation.
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
4. Verify actual app-driven create/edit/delete and a repeat five-minute
   invocation under the trusted owner for both WeRead and Koodo before claiming
   live sync. Initial production import and isolated replay passed. Only one
   WeRead book is configured; extend the explicit book list to the intended
   scope. Markdown exports remain separate adapters.
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
| 07 | `test_unreadable_page_number_keeps_local_trace_and_original`; first-book OCR now resolves marked text across photographed pp.39–44, including two original-book page numbers on one image | Live first-book pages; real 137/139 ambiguity pending |
| 08–09 | `test_catalog_owner_chain_and_session_progress` covers explicit progress evidence | Local; four-photo session pending |
| 10 | `test_trace_crop_uses_oriented_original_and_stays_within_page` renders crops from an EXIF-rotated two-page photo; `test_cross_page_text_link_is_rejected_and_observation_link_keeps_traces_separate` checks direct text links and trace separation | Local geometry; real-photo acceptance pending |
| 11 | `test_uncertain_ordinary_underline_is_saved_without_content_review`; first-book long underlines were aligned to EPUB sentences and saved without per-trace interruption | User accuracy review pending; §38.1 pending |
| 12 | `test_opt_in_symbol_signal_and_important_content_review` | Local |
| 13 | `test_printed_and_margin_punctuation_do_not_trigger_symbol_vocabulary` | Local for correctly typed regions; model misclassification on real photos pending |
| 14 | `test_correction_adds_revision_and_keeps_evidence` | Local |
| 15–16 | New-extractor reconciliation and late-event index tests; the first-book v3 reprocessing retained earlier traces as superseded revisions, installed ten current traces and refreshed the generated Vault note only after an unchanged-content check | Local and first-book reprocessing; arbitrary user-corrected split/merge still requires reconciliation |
| 17 | `test_object_write_failure_does_not_acknowledge_capture_and_retry_succeeds` injects a failed atomic object write and retries the same key | Local |
| 18 | Invalid JSON, unfinished reply, and `test_provider_timeout_keeps_original_and_records_failed_run` | Local; live provider fault response pending |
| 19–20 | Outbox retry and index rebuild tests | Local |
| 21 | `test_foreign_ids_cannot_read_or_mutate_owner_records` probes foreign trace, capture and candidate IDs; the mapped production search returned one p.41 trace while an unmapped sender had no tool | Local adversarial matrix and mapped tool call passed; real inbound question pending |
| 22 | `test_explicit_annotation_link_groups_trace_without_inventing_authorship` | Local |
| 23 | `test_same_query_returns_common_hits_from_all_three_media` returns physical, WeRead and Koodo SearchHits for one query without upstream-specific objects; production now has 10 physical, 118 Koodo and four WeRead traces with owner-scoped hits for each medium; the separate 39-record WeRead fixture was tested in a temporary store | Initial live sync passed; periodic repeat, wider WeRead coverage and app-driven changes pending |
| 24 | The mapped-only `librarian_search` tool returned a production p.41 note with source and page in a trusted-context call. A CLI synthetic agent turn could not resolve the Feishu session route. | Partial: real inbound search-to-answer and evidence-backed reply still pending |
| 25 | `test_source_correction_during_external_write_does_not_publish_promotion` | Local mock; actual knowledge writer pending |
| 26 | `test_candidate_requires_explicit_trigger_and_promotion_confirms_external_write` | Local |

Release evidence remains incomplete. In particular, the §38.1 four-photo
batch, twelve trace groups and later Weber/Parsons retrieval have not been
run. No `release-v0.8` branch or tag should be cut from this state.

Do not use the synthetic photo tests or fixture counts as proof of visual
recognition accuracy or a finished release.

## 2026-09-28 audit remediation update

The independent audit is in `docs/audits/LIBRARIAN_AUDIT_2026-09-28.md`.
Its findings describe the prior implementation; this section records the
subsequent code and production checks without treating the audit as passed.

- F01: the worker now scans all photos for an EPUB identity, then uses the
  configured OpenClaw image model when none is found. An accepted interior
  photo with unknown book/page persists a partial observation and trace even
  without a Vault. The generic route has a synthetic test; a real incoming
  interior-only batch remains unverified.
- F02/F03: cross-photo page inference and EPUB sentence expansion were
  removed. OCR v5 stores photographed text regions and keeps the EPUB hash in
  its version identity. The first-book production worker reprocessed all five
  captures through normal versioned reconciliation: 10 active physical
  traces, three with unresolved pages. The p.39 first underline now begins
  “正是帕森斯” and ends at “社会学思想的核心构成部分。”
  OCR remains incomplete on some other underlines, especially pp.40 and 44;
  their Vault entries are marked for review. This is not a visual accuracy
  acceptance claim.
- F04: automatic catalog recognition now records soft affinity instead of
  selected session state. A narrowly scoped worker migration demoted the one
  legacy production scope and recorded it in `legacy_affinity_repairs`.
- F05: digital source config is bound to one owner. The plugin fails closed
  for multiple distinct configured owners until per-owner storage and routing
  exist. The local single-owner config validates.
- F06: batch faults are isolated in per-batch status files; physical and
  digital work run with separate nonblocking locks and distinct schedules.
  Bad-first/good-second and mode separation tests pass. Live slow-source and
  repeated-trigger timing still need observation.
- F07/F08: automatic reconciliation rejects user-corrected, knowledge-bound,
  split/merged groups and nondefault normalizer configs. A unique group may
  gain a newly detected mark. Trace/observation/outbox commits precede index
  projection; index faults leave durable evidence and retry repairs the index
  without rerunning extraction. Wider correction and digital projection
  paths still need fault-injection review.
- The first-book Vault note now follows the existing WeRead Notes layout:
  metadata, page-grouped `# 高亮划线`, `# 读书笔记`, 📌/💭 entries and timestamps.
  It remains in `2Area/40 学习与阅读/阅读笔记/`; original images remain in the
  Librarian store. Existing generated text is upgraded only after an exact
  unchanged-content comparison. Hidden HTML spans retain trace IDs.

Verification after these changes: 78 Python Librarian tests, five Node plugin
tests and the 77-definition contract validator passed. Gateway configuration
validated and the restarted service was active. The separate pp.159/166/171/184
acceptance photos and `source-design.txt` remain deferred by the user; no
release branch or tag was created. Session command integration, authorized
evidence opening, real inbound search-tool usage, and app-driven digital sync
changes remain outside the verified set.

The previously submitted real Feishu p.39 question did reach the agent and
receive a reply, but its trajectory used shell `exec` to inspect the private
store instead of `librarian_search`. It therefore does not count as the trusted
search-tool acceptance. The dedicated agent now has an OpenClaw per-agent
tool allowlist containing only `librarian_search`, and its SOUL explicitly
forbids shell/file inspection for reading-history answers. Configuration
validation and Gateway restart passed. A new real incoming question is still
needed to verify the tool is exposed with the trusted sender context and used
for the reply; do not mark AC-24 complete from the earlier answer.

## 2026-09-28 late Feishu burst and rendering update

The owner sent 22 individual scans after a text instruction, including
upside-down pages. All 22 image messages were durably accepted. The former
worker processed some as separate batches before the fix and sent redundant
review notices. The plugin now delays processing until uploads have been quiet
for 60 seconds; the worker also skips captures newer than 45 seconds and groups
nearby single-image messages in one conversation into a stable review batch.
The group is replayable without altering the immutable source message IDs.

OCR v6 uses several printed lines to identify the supplied EPUB from interior
pages, detects upside-down scans using the isolated page header number,
analyzes those pages upright, and maps all boxes back to original coordinates.
A scoped reconciliation path accepts that orientation correction only when
the old traces are uncorrected, the EPUB match is strong, a new mark exists,
and no knowledge candidate depends on the old trace. Other group changes
still require review. One prior scan remains in `RECONCILIATION_REQUIRED`.

The current `社会理论二十讲.md` in the requested Vault folder has one WeRead-style
metadata section, 68 highlighted excerpts, 13 handwritten note entries and
five unreadable-mark placeholders: 86 active trace anchors in total. There are
no original photos in the Vault folder. The grouped worker status reports
76 traces from the 22 new captures, 47 with unresolved page labels and one
reconciliation issue; the earlier five captures contribute ten traces, three
with unresolved page labels. These numbers are a review queue, not a claim of
accurate page assignment or mark recognition. The single-note migration
verified each prior generated block against its exact historical trace
revisions before replacing it, so user-edited blocks fail closed.

The dedicated agent now allows `librarian_search`, `librarian_session` and
the harmless `session_status` fallback. Adding the new session tool initially
invalidated OpenClaw plugin capability consent, causing every agent message
to fail before reply. `openclaw plugins enable pap-librarian-intake
--accept-capabilities` restored the plugin. A later real Feishu `？` message
produced a reply without the prior “No callable tools” error. Actual
`librarian_search` and `librarian_session` tool use from real inbound messages
is still unverified. Authorized original-image opening is still absent.

Verification: 83 Python Librarian tests, six Node plugin tests, contract
validator (77 definitions / 18 entries / 42 positive / 43 negative),
`openclaw config validate`, and Gateway startup passed. The separate
pp.159/166/171/184 acceptance set and `source-design.txt` remain deferred.

## 2026-09-29 debugging continuation

The owner-supplied EPUB still serves as printed-text alignment evidence; local
RapidOCR now runs first for interior pages even without an EPUB. The full-page
vision model is a fallback when local OCR finds no mark. OCR v7 also separates
a visible top header page number from marginal pagination: a real photo with
top `23` and marginal `41` now yields page 23, while a different photo with
only marginal `39` and `40` retains its vertical split. The formal worker
reprocessed the existing batches, superseded historical traces through the
normal reconciliation path and updated the Vault note. It still reports 47
unresolved page labels in the 22-photo group, three in the older group and
one mark-group conflict; these require review rather than page inference.

All 86 active physical traces now have a Work binding. Three captures had
older all-unknown resolutions despite a later trusted ISBN fingerprint. The
worker bound those traces to the existing session from stored evidence,
revising them without another OCR or model call. Their immutable originals and
observations were retained. The current owner has 208 active traces and 208
index rows. A production database query for `帕森斯` returns revised trace
hits; book/page queries for `社会理论二十讲` return one hit on page 39 and two on
page 23 with `index_state=ready`. A validation error that had rejected
`SearchHit` revisions above one was fixed after this live query exposed it.

`librarian_search` now accepts optional title and printed page fields in
addition to text. The SOUL and running Gateway have been updated. The agent
also has an owner-scoped `librarian_evidence` tool that makes a temporary crop
within the original page region, sends it to the bound conversation and
deletes the temporary file; original photos remain outside the Vault. Tool
scope, crop and delivery behavior passed local tests, but no post-change real
Feishu inbound turn has invoked search, session or evidence yet. The owner was
asked to send a page-39 question followed by an evidence request, so AC-24 and
the user-visible evidence gate stay open.

Failed batches now use persisted finite backoff and stop after three attempts;
a changed model or EPUB resets the exhausted retry state. Koodo and WeRead
both completed a scheduled unchanged sync after Gateway restart (118 and four
source records respectively). App-driven create/edit/delete and outage
recovery remain unverified. Correction notifications now deduplicate by trace
state; the worker sent one new notice for each historical review group after
the v7 revision. User-side delivery has not been confirmed.

Verification at this point: 95 Python Librarian tests, seven Node plugin
tests, the 77-definition contract validator, OpenClaw config validation and
an active Gateway. The worktree is clean and no release tag or branch exists.
The four-photo §38.1 acceptance set and `source-design.txt` remain deferred by
the owner; the full v0.8 audit is not closed.

The personal symbol vocabulary now has a durable configuration snapshot on
each new ProcessingRun, separate from normalizer and extractor versions.
Reprocessing with different mappings under the same vocabulary label requires
review; an identical snapshot can reconcile across extractor versions.
One-to-one mark replacements write explicit `supersedes` TraceRelations. This
is locally verified, while legacy vocabulary runs without snapshots and
ambiguous group changes remain review-only. The full F07 gate stays open.
The one remaining first-book conflict is a genuine 5-to-8 mark change on
`capture_92f01023e12541aeb64c135ec543a6ba`; the new observation includes
upper-page ink absent from the old active traces. It needs an explicit review
decision, not an automatic overwrite.
<!-- 2026-09-29: librarian_review is an owner-bound, read-only tool for pending extraction conflicts. Production has one latest pending capture, capture_92f01023e12541aeb64c135ec543a6ba. The proposed v7 projection is three grouped underlines from eight marks versus five old traces; candidate text has omissions. Do not auto-accept. Tool capability must be accepted before Gateway restart. -->
<!-- 2026-09-29 later: v8 currently has five latest pending captures; see the audit addendum. A real Feishu review request reached librarian at 07:30 CST, but trajectory tools contained only session_status and the agent replied with stale failure context. The agent's global coding profile filtered plugin tools despite tools.allow. Local OpenClaw config now uses librarian-only tools.profile=minimal with tools.alsoAllow for the four librarian tools; config and OpenClaw's effective policy resolver confirm the intended five-tool set. Gateway restarted at 07:35 CST. Await a second real inbound turn to verify tool invocation. -->
