# Librarian runtime (v0.8 in progress)

This directory implements an early, local slice of
[`SPEC_v0.8_Librarian.md`](../../../docs/SPEC_v0.8_Librarian.md).
`schemas/contracts.schema.json` is the sole model definition; the 18
`<Model>.schema.json` files are entry points into it. The current schema has
59 definitions. This does **not** yet satisfy the draft's 77-definition,
42-positive/43-negative-fixture contract package claim.

`store.py` provides owner-scoped Work/Edition/BookInstance registration,
versioned sessions, scope-limited active session and 90-minute affinity,
a content-addressed original object store, all-or-retry capture acceptance,
idempotency, immutable evidence records, and an outbox in the domain
transaction. `pipeline.py` accepts a replaceable extractor that
returns raw JSON bytes. It saves those bytes, validates the observation,
checks dimensions against the EXIF-oriented original, records failed runs,
normalizes trace groups, indexes the current revision, supports correction,
applies an opt-in versioned symbol vocabulary with exception-only review,
and can rebuild the index from traces. Its tests use synthetic images and
synthetic observations; it is not a production image extractor.

`commands.py` validates the thirteen command names and their payload shapes,
then executes the supported MVP commands with owner/actor checks and an
idempotent receipt in the same database transaction. Capture commands resolve
trusted upload references, recheck bytes on retry, and allow user resolution
before or after extraction. Knowledge candidate commands remain explicitly
unimplemented.

`events.py` publishes the transactional outbox with stable event IDs and
deduplicates consumer handling in a local transaction. The trace projection
uses the current trace revision so an older event cannot roll back the search
index. The nine event payloads are validated against the canonical schema.

`digital.py` parses the WeRead and Koodo Markdown exports observed in this
Vault into the same `ReadingTrace` contract. It stores the whole original
export, uses source record IDs for replay safety, and requires reconciliation
when a source record changes. This is an export adapter, not live platform
sync. The local smoke check parsed 26 highlights from one WeRead export, 151
highlight/comment records from another, and 20 Koodo highlights; these counts
are parser observations, not a complete platform-format acceptance test.

Run the focused tests from the repo root:

```bash
PYTHONPATH=. python3 -m pytest tests/test_librarian_store.py tests/test_librarian_pipeline.py tests/test_librarian_digital.py tests/test_librarian_commands.py tests/test_librarian_events.py -q
```

Runtime files belong under `var/librarian/` or another private state
directory. There is no scheduled job or public gateway route yet. The caller
must supply a trusted `owner_id`; passing arbitrary owner strings to these
Python methods is not an authentication mechanism.

Remaining work includes full contract fixtures and semantic checks; stronger
batch book/page conflict resolution; actual image extraction with annotated-photo tests;
Gateway upload identity and authorization; page/edition conflict handling;
review exception workflows; complete search
contracts; live WeRead/Koodo synchronization; and knowledge promotion.
