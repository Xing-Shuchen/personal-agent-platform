# Librarian v0.8 handoff — 2026-09-28

The requested goal is **not complete**. Development commits are on `main`.
Create `release-v0.8` only after the acceptance evidence below is complete.

## Verified locally

- The canonical contract has 77 definitions, 18 entry schemas, 42 positive
  fixtures and 43 negative fixtures. `python3
  agents/librarian/runtime/tests/validate_contracts.py` passes. The absent
  original `source-design.txt` prevents a source-package comparison.
- Capture storage, sessions, versioned traces, search, digital export parsing,
  transactional events, candidate state, and separated exception queues have
  synthetic tests. The latest broad run passed 319 tests, skipped 71 and
  deselected one existing test requiring unavailable `historian.summarization`.
- The OpenClaw intake plugin reports `loaded`, with one `message_received`
  typed hook and no diagnostics. Both plugin tests pass. On this PC, the
  dedicated `librarian` PAP profile and unbound OpenClaw agent are registered.
  The linked plugin is installed and enabled with `ownerMappings: []`; no
  sender is authorized for automatic intake.
- `runtime/vision.py` sends an EXIF-oriented derivative to a configurable
  Claude Messages endpoint. The pipeline stores the original, derivative,
  transform and raw model JSON. A mocked provider test covers that path and
  failure persistence. The currently configured proxy returns HTTP 404 for
  standard `/v1/messages`; the default local model rejects image input.

## Required before release

1. Obtain the four annotated physical photos for p.159, p.166, p.171 and
   p.184, plus the original `source-design.txt` if it exists. Keep private
   image bytes outside Git. Similarly numbered Evernote `_orphan` files in the
   Vault have not been established as these inputs; `_orphan_171.jpg` was
   visually checked and is unrelated.
2. Configure a vision-capable provider compatible with the image request in
   `runtime/vision.py`. Run extraction against the four real photos and verify
   the twelve trace groups, source regions, `Parsons?`, page attribution,
   progress evidence and later Weber/Parsons retrieval specified in §38.1.
3. With the dedicated Librarian profile now registered on this PC, configure
   an explicit OpenClaw channel/account/sender-to-owner mapping and reload
   Gateway. Verify one real inbound image batch and replay behavior. Leave
   mapping empty until the identity is known.
4. Validate WeRead and Koodo against real upstream payloads and live sync
   behavior. Current adapters cover observed Markdown exports only.
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
   `repoRoot` and private `stateRoot`. Keep `ownerMappings: []` until the
   dedicated profile and trusted sender identity are ready.
4. Runtime captures and SQLite data live under `var/librarian/`, outside Git.
   Copy that private directory separately only if existing local captures must
   be continued on the new PC; preserve file permissions and stop any writer
   before copying. Provider credentials and OpenClaw settings are also local
   machine configuration and are not in this repository.

The original Obsidian Vault is likewise external to Git. Its path on this PC
was `/home/cambricon/documents/Obsidian/Second_Brain`; configure the new PC's
actual Vault path separately.

## Current PC verification — 2026-09-28

- `agents/librarian/agent.yaml` loads through `pap.spec.load_spec` with no
  proactive jobs. `openclaw agents list --json` reports `librarian` with zero
  bindings; its workspace SOUL matches the repository profile.
- `openclaw plugins inspect pap-librarian-intake --runtime --json` reports
  `loaded`, one typed `message_received` hook, and no diagnostics. The Gateway
  service was started and reports healthy, but no mapped sender or live image
  has been exercised. The CLI Gateway RPC probe did not establish a connection.
- Focused Python tests: 25 vision/pipeline/bridge tests and 18
  store/digital/command/event/knowledge tests passed. Contract validation
  passed 77 definitions, 18 entries, 42 positive and 43 negative cases;
  the two Node plugin tests passed. These are synthetic tests.
- `ANTHROPIC_API_KEY`, `ANTHROPIC_AUTH_TOKEN`, and `ANTHROPIC_BASE_URL` are
  unset in this shell. No working vision provider was demonstrated here.

## AC-01–26 runtime evidence audit

`Local` means a synthetic executable test of the indicated behavior. It does
not mean the real-photo, live Gateway, upstream, or service acceptance is done.

| AC | Current evidence | Status / remaining proof |
|---|---|---|
| 01–03 | `test_librarian_store.py` capture retry/conflict/same bytes and `test_librarian_gateway_bridge.py` source identity | Local; live message replay pending |
| 04 | Catalog registration and ambiguity logic in `store.py` | Pending two-edition runtime scenario |
| 05 | `test_conflicting_explicit_session_keeps_original_and_observation` | Local; real visible-title extraction pending |
| 06 | `test_session_selection_and_soft_affinity_stay_in_conversation_scope` | Local |
| 07 | `test_unreadable_page_number_keeps_local_trace_and_original` | Local for unknown page; real 137/139 ambiguity pending |
| 08–09 | `test_catalog_owner_chain_and_session_progress` covers explicit progress evidence | Local; four-photo session pending |
| 10 | `test_trace_crop_uses_oriented_original_and_stays_within_page` renders owner-scoped crops from an EXIF-rotated two-page synthetic photo; derivative mapping and cross-page link checks also pass | Local geometry; real-photo acceptance pending |
| 11 | Trace confidence fields and ordinary mark normalization | Partial; recognition-error runtime scenario pending |
| 12 | `test_opt_in_symbol_signal_and_important_content_review` | Local |
| 13 | `test_printed_and_margin_punctuation_do_not_trigger_symbol_vocabulary` | Local for correctly typed regions; model misclassification on real photos pending |
| 14 | `test_correction_adds_revision_and_keeps_evidence` | Local |
| 15–16 | New-extractor reconciliation and late-event index tests | Local |
| 17 | `test_object_write_failure_does_not_acknowledge_capture_and_retry_succeeds` injects a failed atomic object write and retries the same key | Local |
| 18 | Invalid JSON and unfinished provider reply tests | Partial; provider timeout pending |
| 19–20 | Outbox retry and index rebuild tests | Local |
| 21 | Owner-filtered search, review and evidence reads tested | Partial; adversarial cross-owner reference matrix pending |
| 22 | `test_explicit_annotation_link_groups_trace_without_inventing_authorship` | Local |
| 23 | `test_exports_converge_at_trace_and_retry_is_idempotent` and common search | Local on observed Markdown; real upstream payloads pending |
| 24 | Empty search behavior exists; profile instructs evidence-bound answers | Pending live answer test |
| 25 | `test_source_correction_during_external_write_does_not_publish_promotion` | Local mock; actual knowledge writer pending |
| 26 | `test_candidate_requires_explicit_trigger_and_promotion_confirms_external_write` | Local |

Release evidence remains incomplete. In particular, the §38.1 four-photo
batch, twelve trace groups and later Weber/Parsons retrieval have not been
run. No `release-v0.8` branch or tag should be cut from this state.

Do not use the synthetic photo tests or fixture counts as proof of visual
recognition accuracy or a finished release.
