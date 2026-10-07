# Bookscan in Librarian

`bookscan_adapter.py` runs the optional `bookscan/` OCR processor in a separate Python interpreter and adapts its output to `PageObservation`. The interpreter is selected by `bookscanPython` in the OpenClaw plugin or `LIBRARIAN_BOOKSCAN_PYTHON` locally. OCR weights and source books stay on the user's machine.

`local-processing/config.yaml` is a generic template. A user may copy it to ignored `local-processing/config.local.yaml` for machine-specific settings, and add ignored `local-processing/manifest.json` and `inputs.sha256` for hand reviewed image regions. Without them, captures use the full oriented image with no preset annotation or bracket regions. This does not imply the page lacks handwriting; uncertain results require review.

Bookscan reports, crops, source books, and trace state live under ignored `var/librarian/`. A processor version change creates a pending observation for reconciliation rather than overwriting a corrected trace.
