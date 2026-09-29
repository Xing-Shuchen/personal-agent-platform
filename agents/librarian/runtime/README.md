# Librarian runtime (v0.8 in progress)

This directory implements an early, local slice of
[`SPEC_v0.8_Librarian.md`](../../../docs/SPEC_v0.8_Librarian.md).
`schemas/contracts.schema.json` is the sole model definition; the 18
`<Model>.schema.json` files are entry points into it. The current schema has
77 definitions. The offline package has 42 positive and 43 negative synthetic
fixtures, all 18 model entries, and a validation report. The added definitions
factor existing nested structures into reusable contracts; the unavailable
source-design attachment prevents a name-for-name comparison with its package.

## Physical recognizer handoff

Automatic physical recognition is paused on this PC: the private OpenClaw
configuration sets `physicalWorkerEnabled: false`. Feishu image intake still
stores immutable originals; the digital worker is independent. The image
processor is now the fetched local Bookscan implementation; see
[BOOKSCAN_INTEGRATION.md](BOOKSCAN_INTEGRATION.md) for its adapter, runtime,
evidence and accuracy limits. The pause remains until live review is complete.

The framework entry point is `pipeline.process_capture(lib, owner_id,
capture_id, extractor, extractor_version=...)`. The trusted caller supplies the
owner and capture ID. `extractor(original_bytes)` receives the immutable image
bytes and returns either UTF-8 JSON bytes containing the observation fields,
or `ExtractionOutput(raw, derivative, derivative_width, derivative_height,
operations, observation)`. The second form keeps the recognizer's raw JSON
response separate from adapted `observation` JSON. `derivative` is a PNG with
declared dimensions; operations are `exif_transpose` and/or `uniform_resize`.
Both forms use the EXIF-oriented original as the normalized coordinate space.

The adapted JSON contains only `image_space`, `visible_title`, `pages`,
`printed_regions`, `marks`, `annotations`, `symbols`, `links`, and `warnings`.
Its persisted form is `PageObservation` in `schemas/contracts.schema.json`;
the framework supplies IDs, owner, run linkage, timestamps, and asset refs.
`image_space` dimensions must match the EXIF-oriented original. Bounding boxes
are normalized to `[0, 1]`; each detection belongs to exactly one page region,
and direct text links stay on that page. Unknown text and page numbers remain
null with `basis: unknown`, rather than guessed from EPUB or upload order.
The adapter is responsible for mapping any future recognizer output into these
fields. It is not allowed to claim an owner, run, catalog ID, or trace ID.

The pipeline validates schema, image dimensions, geometry, and references
before normalization. It preserves the original, raw response, derivative,
and failed processing attempt when adapted output is invalid. A changed
`extractor_version` creates an observation requiring reconciliation when a
successful run already exists; it does not overwrite current or corrected
traces. User review and a versioned decision remain necessary for uncertain
marks. The source EPUB may inform an adapter, but its text is not itself
evidence that a mark covers that sentence.

`store.py` provides owner-scoped Work/Edition/BookInstance registration,
versioned sessions, scope-limited active session and 90-minute affinity,
a content-addressed original object store, all-or-retry capture acceptance,
idempotency, immutable evidence records, and an outbox in the domain
transaction. `pipeline.py` accepts the replaceable extractor above. It saves
the raw bytes and validates the adapted observation,
checks dimensions against the EXIF-oriented original, records failed runs,
rejects a mark's direct printed-text link when it crosses a page region,
keeps explicit cross-page observation relationships without merging traces,
keeps a valid observation and raw output when catalog context conflicts,
flags a high-confidence visible title that uniquely matches another registered Work,
normalizes trace groups, indexes the current revision, supports correction,
stores a new extractor's observation for reconciliation without replacing
corrected traces,
applies an opt-in versioned symbol vocabulary with exception-only review,
and can rebuild the index from traces. Its tests use synthetic images and
synthetic observations. `vision.py` provides Claude Messages and
OpenAI-compatible Chat Completions image adapters:
it sends an EXIF-oriented, uniformly resized derivative, requests normalized
coordinates, and returns the model text to the pipeline. The derivative,
transform and raw model text are saved with the processing attempt, including
failed validation attempts. Its provider transport has a local mock test; the
timeout path retains the original and records a failed processing run without
creating traces. A timeout has no model response bytes to retain. The
earlier configured Claude endpoint returned HTTP 404 for `/v1/messages`. The
first-book run used local RapidOCR for printed text and OpenClaw's configured
GLM-5.3-Flash only for handwriting crops; its key stayed in the write-only
OpenClaw secret store. The earlier default local model rejected a synthetic
image input. See the
official [Claude vision](https://platform.claude.com/docs/en/build-with-claude/vision)
and [coordinate](https://platform.claude.com/docs/en/build-with-claude/vision-coordinates)
API documentation, and the [Z.AI GLM-5.3-Flash image input format](https://docs.z.ai/guides/vlm/glm-5.3-flash)
for the Chat Completions request shape.
Search accepts text or a structural filter, including textless symbol traces,
and returns the same provenance-bearing hit contract for all three media.
`render_trace_crop` produces an owner-scoped PNG for the current physical trace
from the immutable original after applying its EXIF orientation. It pads the
trace box within its page region, so a facing page is not included. The full
original remains readable separately through `Library.read_trace_evidence`.
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

The historical `ocr.py` adapter runs local RapidOCR on each original, compares printed lines with a
matching owner-provided EPUB, detects long pen strokes, and expands marked
printed text to complete EPUB sentences. Only small handwriting crops go to
the configured OpenClaw image model. Raw OCR boxes, stroke scores and model
responses remain attached to the processing observation. `worker.py` no longer
selects this adapter or the full-page vision fallback for content extraction.
`worker.py` recovers accepted Feishu batches, matches a photographed
ISBN to `source-books/<isbn13>.epub`, registers the book and reading session,
processes all captures through Bookscan, writes a review note under the configured Obsidian
Vault's `2Area/40 学习与阅读/阅读笔记`, and sends one Feishu review message after the
database and Vault write complete. The plugin launches the physical worker after
intake and periodically for recovery only when `physicalWorkerEnabled` is true.
`../openclaw-plugin/recover.mjs` can replay a missed
OpenClaw transcript event through the same authenticated intake path.

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

`koodo_native.py` reads Koodo Reader's local `books.db` and `notes.db` in
SQLite read-only mode. It maps each native note key and book key to stable
Librarian IDs, retains the exact source columns as private JSON evidence, and
keeps Koodo's locator object as a source-native locator rather than calling it
an EPUB CFI. Repeated calls create, update, or retire traces as source records
change. A source edit to a user-corrected trace stays pending until an explicit
`reconcile_koodo_note` choice accepts the source or retains the correction.
The OpenClaw worker now schedules a five-minute read-only sync for the trusted
owner on this PC. Its initial production import stored 118 notes from one book;
an isolated replay, raw evidence, search, and owner isolation passed without
storing private content in Git. An app-driven edit and the live repeat remain
to be observed.

Run a native sync only after assigning the trusted owner and stable source ID:

```bash
PYTHONPATH=. python3 -m agents.librarian.runtime.koodo_native \
  --root var/librarian --owner OWNER_ID --source-id local_koodo \
  --books-db /path/to/koodo-reader/uploads/data/config/books.db \
  --notes-db /path/to/koodo-reader/uploads/data/config/notes.db
```

The two source database paths are machine-specific. An empty source will not retire every known note
unless `--allow-empty-source` is supplied deliberately. Never edit the Koodo
databases from Librarian.

`weread_native.py` reads one WeRead book through the plugin's Agent API using
`/book/bookmarklist` and paginated `/review/list/mine`. It stores native
highlight and review IDs, chapter locators, timestamps, and each complete raw
record as private evidence. The API key is read from
`LIBRARIAN_WEREAD_API_KEY`; it is never stored in the repository. The initial
read-only check on this PC imported 38 highlights and one review into a
temporary Library. Replay created no duplicates, and raw evidence and
owner-scoped search passed. Source edit/delete behavior has synthetic tests;
an actual app-driven change and a live scheduled repeat remain unverified.
The OpenClaw worker on this PC imports one explicitly configured WeRead book
using the private Obsidian plugin data file for its API key. Its first
production sync stored four traces. Other books require adding their IDs to
the worker configuration.

```bash
LIBRARIAN_WEREAD_API_KEY=... PYTHONPATH=. python3 -m agents.librarian.runtime.weread_native \
  --root var/librarian --owner OWNER_ID --source-id personal_weread \
  --book-id BOOK_ID
```

Use a trusted owner and stable account source ID. An empty snapshot requires
`--allow-empty-source` to retire records. Changed source text on a
user-corrected trace stays pending for `reconcile_weread_record`; deletion of
a corrected trace requires reconciliation and does not proceed silently.

Run the focused tests from the repo root:

```bash
PYTHONPATH=. python3 -m pytest tests/test_librarian_store.py tests/test_librarian_pipeline.py tests/test_librarian_digital.py tests/test_librarian_commands.py tests/test_librarian_events.py -q
PYTHONPATH=. python3 -m pytest tests/test_librarian_knowledge.py -q
PYTHONPATH=. python3 -m pytest tests/test_librarian_vision.py -q
```

Once a compatible image endpoint and credential are configured, process an
already accepted capture with Claude Messages:

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

For an OpenAI-compatible Chat Completions image endpoint, set
`LIBRARIAN_VISION_API_KEY` and `LIBRARIAN_VISION_BASE_URL`, then run:

```bash
PYTHONPATH=. python3 -m agents.librarian.runtime.vision \
  --provider chat-completions --root var/librarian \
  --owner OWNER_ID --capture CAPTURE_ID --model IMAGE_MODEL_ID
```

The endpoint must accept `image_url.url` with a PNG data URL and return one
completed text response. OpenClaw write-only secret references are not read
by this Python command; supply a separate runtime credential securely.

For a model already authenticated in OpenClaw, use its direct image inference
command through this runtime's `openclaw` provider:

```bash
PYTHONPATH=. python3 -m agents.librarian.runtime.vision \
  --provider openclaw --root var/librarian --owner OWNER_ID \
  --capture CAPTURE_ID --model zai/glm-5.3-flash
```

This transport passes the EXIF-oriented derivative to `openclaw infer model
run`, verifies the returned model route and stores the model's text exactly
before observation validation. It uses OpenClaw's configured credential and
does not copy it into Librarian. On this PC a synthetic 900×1200 page passed
the live route and `process_capture` created one underline and one margin-note
trace in a temporary Library. This establishes a working provider path, not
accuracy on the four acceptance photos.

Run the offline contract verifier from this directory with
`python3 tests/validate_contracts.py`. It writes
`tests/validation-report.json` and checks the 42/43 examples plus domain
reference links without fetching remote schemas. These examples are synthetic
contract cases, not annotated photos or live platform payloads.

Runtime files belong under `var/librarian/` or another private state
directory. There is no scheduled job or public gateway route yet. The caller
must supply a trusted `owner_id`; passing arbitrary owner strings to these
Python methods is not an authentication mechanism.

The physical worker refreshes a private Bookscan review index at
`var/librarian/review/index.html`. It can also be regenerated without OCR:
`python3 -m agents.librarian.runtime.review_index --root var/librarian --owner <trusted-owner-id>`.
Each link opens the current capture's original `review.html`. Browser decisions
remain local drafts until submitted. Start the private loopback UI with
`python3 -m agents.librarian.runtime.bookscan_review_server --root var/librarian --owner <trusted-owner-id> --vault <vault-path>`.
Open the printed tokenized local URL. Complete all page, line, group and handwriting
decisions, then use **提交复核并入库**. The server checks the immutable Bookscan run,
versions replaced traces and confirmed page numbers, and runs the physical
worker to refresh the Vault note. The original photo and reviewed decision
bundle remain in Librarian's private object store. The CLI
`python3 -m agents.librarian.runtime.bookscan_review_apply --root var/librarian --owner <trusted-owner-id> --bundle reviewed-decisions.json --dry-run`
can preflight an exported review without writes. The localhost page fetches a
current trace snapshot before each submission; a later correction creates a
new version only if that snapshot remains current.

Remaining work includes broader semantic checks; stronger
batch book/page conflict resolution; actual image extraction with annotated-photo tests;
Gateway upload identity and authorization; page/edition conflict handling;
review exception workflows; complete search contracts; live WeRead/Koodo
synchronization; and connection to an actual knowledge service.
