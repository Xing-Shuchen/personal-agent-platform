# Librarian runtime (v0.8 in progress)

This directory implements an early, local slice of
[`SPEC_v0.8_Librarian.md`](../../../docs/SPEC_v0.8_Librarian.md).
`schemas/contracts.schema.json` is the sole model definition; the 18
`<Model>.schema.json` files are entry points into it. The current schema has
37 definitions. This does **not** yet satisfy the draft's 77-definition,
42-positive/43-negative-fixture contract package claim.

`store.py` provides owner-scoped Work/Edition/BookInstance registration,
versioned sessions, a content-addressed original object store, all-or-retry
capture acceptance, idempotency, immutable evidence records, and an outbox in
the domain transaction. `pipeline.py` accepts a replaceable extractor that
returns raw JSON bytes. It saves those bytes, validates the observation,
normalizes trace groups, indexes the current revision, supports correction,
and can rebuild the index from traces. Its tests use synthetic bytes and
synthetic observations; it is not a production image extractor.

Run the focused tests from the repo root:

```bash
python -m pytest tests/test_librarian_store.py tests/test_librarian_pipeline.py -q
```

Runtime files belong under `var/librarian/` or another private state
directory. There is no scheduled job or public gateway route yet. The caller
must supply a trusted `owner_id`; passing arbitrary owner strings to these
Python methods is not an authentication mechanism.

Remaining work includes full contract fixtures and semantic checks; batch
resolution and affinity; actual image extraction with annotated-photo tests;
Gateway upload identity and authorization; page/edition conflict handling;
review exceptions and vocabulary; complete command, event, and search
contracts; live WeRead/Koodo adapter mapping; and knowledge promotion.
