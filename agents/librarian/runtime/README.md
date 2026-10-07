# Librarian runtime

This directory implements the reading evidence contracts in [SPEC_v0.8_Librarian.md](../../../docs/SPEC_v0.8_Librarian.md). `schemas/contracts.schema.json` is the canonical model; the individual model schemas are entry points.

`store.py` owns the transactional, owner-scoped catalog, immutable originals, reading sessions, captures, traces, and domain events. `pipeline.py` validates extraction output, preserves raw evidence and revisions, and sends uncertain observations to review. `commands.py` validates user actions and produces idempotent receipts. `knowledge.py` keeps candidates separate from approved knowledge objects. `digital.py`, `koodo_native.py`, and `weread_native.py` import explicitly configured digital sources.

Physical image processing is optional. `bookscan_adapter.py` runs the processor in a separate interpreter and adapts its result to `PageObservation`; see [BOOKSCAN_INTEGRATION.md](BOOKSCAN_INTEGRATION.md). The `physicalWorkerEnabled` OpenClaw setting controls background processing. A trusted owner mapping is required before the gateway accepts an image or exposes owner-scoped search. Configure paths and credentials locally under `var/` or in ignored service settings. Source books, photos, crops, databases, and review records must not enter Git.

The local schema and pipeline tests use synthetic fixtures. They verify data contracts and state transitions; they do not establish OCR accuracy for a new user's books.
