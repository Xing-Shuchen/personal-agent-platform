# Librarian runtime (v0.8 in progress)

This directory implements an early, local slice of
[`SPEC_v0.8_Librarian.md`](../../../docs/SPEC_v0.8_Librarian.md).
`schemas/contracts.schema.json` is the sole model definition; the 18
`<Model>.schema.json` files are entry points into it. The current schema has
77 definitions. The offline package has 42 positive and 43 negative synthetic
fixtures, all 18 model entries, and a validation report. The added definitions
factor existing nested structures into reusable contracts; the unavailable
source-design attachment prevents a name-for-name comparison with its package.

`store.py` provides owner-scoped Work/Edition/BookInstance registration,
versioned sessions, scope-limited active session and 90-minute affinity,
a content-addressed original object store, all-or-retry capture acceptance,
idempotency, immutable evidence records, and an outbox in the domain
transaction. `pipeline.py` accepts a replaceable extractor that
returns raw JSON bytes. It saves those bytes, validates the observation,
checks dimensions against the EXIF-oriented original, records failed runs,
keeps a valid observation and raw output when catalog context conflicts,
flags a high-confidence visible title that uniquely matches another registered Work,
normalizes trace groups, indexes the current revision, supports correction,
stores a new extractor's observation for reconciliation without replacing
corrected traces,
applies an opt-in versioned symbol vocabulary with exception-only review,
and can rebuild the index from traces. Its tests use synthetic images and
synthetic observations. `vision.py` provides a Claude Messages image adapter:
it sends an EXIF-oriented, uniformly resized derivative, requests normalized
coordinates, and returns the model text to the pipeline. The derivative,
transform and raw model text are saved with the processing attempt, including
failed validation attempts. Its provider transport has a local mock test; the
current configured endpoint returns HTTP 404 for `/v1/messages`, so live
image recognition has not been verified. The current default local model also
rejected a synthetic image input; configure a vision-capable model and endpoint
before enabling processing. See the official [Claude vision](https://platform.claude.com/docs/en/build-with-claude/vision)
and [coordinate](https://platform.claude.com/docs/en/build-with-claude/vision-coordinates)
API documentation for the request shape and resize behavior.
Search accepts text or a structural filter, including textless symbol traces,
and returns the same provenance-bearing hit contract for all three media.
`review.py` exposes separate owner-scoped queues for processed captures with
unresolved catalog context and important traces whose recognized content is
uncertain. Ordinary low-confidence marks do not enter the content queue. A
user correction closes content review only after every uncertain field has
been explicitly checked, including checks made across successive revisions.

`commands.py` validates the thirteen command names and their payload shapes,
then executes the supported MVP commands and candidate approval/rejection with
owner/actor checks and an idempotent receipt in the same database transaction.
Capture commands resolve
trusted upload references, recheck bytes on retry, and allow user resolution
before or after extraction.

`knowledge.py` keeps candidates separate from knowledge objects. An enabled
`promote_candidate` symbol creates only a pending candidate; ordinary
highlights do not. Approval checks exact current trace revisions. Promotion
requires an idempotent external knowledge writer to confirm persistence before
the candidate and success event advance. Trace corrections or capture
resolutions supersede stale pending candidates; a symbol-triggered candidate
is recreated against the new trace revision without carrying an old inferred
claim forward. PAP has no configured writer yet.

`gateway_bridge.py` accepts bounded staged image bytes over a trusted local
stdin protocol and executes `reading.capture.ingest`. The linked OpenClaw
plugin in `../openclaw-plugin/` maps a concrete channel/account/sender to an
owner and forwards only staged `image/*` media with stable message/item IDs.
It requires an explicit owner mapping before live capture intake.

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
PYTHONPATH=. python3 -m pytest tests/test_librarian_knowledge.py -q
PYTHONPATH=. python3 -m pytest tests/test_librarian_vision.py -q
```

Once a Claude-compatible Messages endpoint and credential are configured,
process an already accepted capture with:

```bash
PYTHONPATH=. python3 -m agents.librarian.runtime.vision \
  --root var/librarian --owner OWNER_ID --capture CAPTURE_ID --model MODEL_ID
```

Set `ANTHROPIC_API_KEY` (or the deployment's `ANTHROPIC_AUTH_TOKEN`) and
optionally `ANTHROPIC_BASE_URL` in the local environment. The command sends
image content to the configured provider. API keys use `x-api-key`; auth tokens
use `Authorization: Bearer`. Choose a vision model whose native
resolution accommodates the derivative; provider-side downscaling is rejected
to preserve coordinate mapping. Do not treat a successful API response as the
annotated-photo acceptance result.

Run the offline contract verifier from this directory with
`python3 tests/validate_contracts.py`. It writes
`tests/validation-report.json` and checks the 42/43 examples plus domain
reference links without fetching remote schemas. These examples are synthetic
contract cases, not annotated photos or live platform payloads.

Runtime files belong under `var/librarian/` or another private state
directory. There is no scheduled job or public gateway route yet. The caller
must supply a trusted `owner_id`; passing arbitrary owner strings to these
Python methods is not an authentication mechanism.

Remaining work includes broader semantic checks; stronger
batch book/page conflict resolution; actual image extraction with annotated-photo tests;
Gateway upload identity and authorization; page/edition conflict handling;
review exception workflows; complete search contracts; live WeRead/Koodo
synchronization; and connection to an actual knowledge service.
