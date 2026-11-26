# Bookscan in Librarian

`bookscan_adapter.py` runs the optional `bookscan/` OCR processor in a separate Python interpreter and adapts its output to `PageObservation`. The interpreter is selected by `bookscanPython` in the OpenClaw plugin or `LIBRARIAN_BOOKSCAN_PYTHON` locally. OCR weights and source books stay on the user's machine.

`local-processing/config.yaml` is a generic template. A user may copy it to ignored `local-processing/config.local.yaml` for machine-specific settings, and add ignored `local-processing/manifest.json` and `inputs.sha256` for hand reviewed image regions. Without them, captures use the full oriented image with no preset annotation or bracket regions. This does not imply the page lacks handwriting; uncertain results require review.

Bookscan reports, crops, source books, and trace state live under ignored `var/librarian/`. A processor version change creates a pending observation for reconciliation rather than overwriting a corrected trace.

## Optional remote OCR

Set `models.remote_command` in the ignored local configuration to an argument
list that starts `python -u -m bookscan.remote_ocr --config <worker-config>` on
the compute host, for example through SSH. The worker config selects local
model paths and `device: gpu:0`; it must not contain `remote_command` itself.
`models.remote_timeout` sets the response timeout in seconds (default 120).

The worker stays loaded for one processing run. Only lossless PNG images and
OCR geometry/text cross its standard input/output; EPUB alignment, evidence,
review and databases remain local. Model hashes come from the worker's actual
weights. Transport failures surface as processing errors; there is no silent
switch to different models. Keep compute environments, weights and working
caches on fast storage; use archive disks for cold copies and backups.
