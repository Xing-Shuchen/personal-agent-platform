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
  typed hook and no diagnostics. Both plugin tests pass. Its `ownerMappings`
  is empty, and no Librarian agent/profile is registered locally.
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
3. Register the dedicated Librarian profile, then configure an explicit
   OpenClaw channel/account/sender-to-owner mapping and reload Gateway. Verify
   one real inbound image batch and replay behavior. Leave mapping empty until
   the identity is known.
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

Do not use the synthetic photo tests or fixture counts as proof of visual
recognition accuracy or a finished release.
