# Bookscan image processor in Librarian

The Feishu intake, owner and catalog rules, immutable object store, review
decisions, trace revisions, search index, and Vault renderer remain Librarian
services. `worker.py` now calls `bookscan_adapter.py` for physical image
processing. The adapter runs the fetched `bookscan/` segmentation and
PaddleOCR code in a separate Python interpreter, then submits only an adapted
`PageObservation` to `process_capture`.

The model interpreter is configured as `bookscanPython` in the OpenClaw plugin.
On this PC it is `local-processing/.venv/bin/python`; local model weights live
in `~/.paddlex/official_models/`. The current bookscan configuration,
sample-region manifest and input hashes are in `local-processing/`. The 22
sample photos and the sample EPUB remain on the exploration branch; they are
not needed by the live adapter. Owner-provided EPUBs continue to live under
private `var/librarian/source-books/`. If an EPUB cannot be identified, the
same segment/OCR processor runs without alignment and keeps book and page
context unresolved as needed.

For exact bytes matching an entry in `inputs.sha256`, the adapter uses that
entry's hand-reviewed ROI, rotation, annotation and bracket regions. Other
captures use the full EXIF-oriented image with no preset annotation or bracket
regions. The current processor does not automatically discover handwritten
notes or `「」` endpoints on a new photo. Those regions need a future detector
or explicit review input. This is a limitation of the fetched method, not a
claim that an empty annotation array means there is no handwritten note.

Bookscan groups become separate underline or bracket detections linked to
their photo OCR text. EPUB punctuation expansion, candidate matches and
scores remain in the raw bookscan report for review; expanded EPUB-only words
do not enter the photo-original `printed_text` field. Observed page numbers
are used; interpolated page numbers stay unresolved. The complete bookscan
run, including crops and report files, is retained under private
`var/librarian/bookscan-runs/<owner-hash>/`; originals and crops never enter
the Vault. `PageObservation.raw_output_asset` retains a JSON snapshot, and
the normal evidence chain still references the captured original and the
EXIF-oriented derivative.

Existing RapidOCR/vision observations and corrected traces stay immutable.
A change in bookscan code, configuration or local weights changes the
extractor version. Reprocessing an already completed capture creates a
pending observation for reconciliation; the worker does not silently replace
old traces or user corrections. `physicalWorkerEnabled` remains `false` on
this PC until the new output and pending reviews are accepted for live use.

Verification on 2026-09-29: 173 Librarian/Bookscan Python tests and 16 plugin
tests passed. One exploration photo was processed locally with the real
PaddleOCR weights, and the adapter passed Librarian schema validation in an
isolated Library, producing four underline and two margin-note traces. This
is a runtime smoke check, not measured OCR accuracy; the branch has no
complete human ground truth.
