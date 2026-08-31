---
name: news-synthesize
description: Produce a daily or weekly change-only historical synthesis from the Chronicle rather than a generic news list.
---

# Synthesize the Chronicle

Use Chronicle state for the requested daily or weekly window. Report only
material change:

- threads with substantive updates;
- corrections, disputes, or superseded early reports;
- new relations or causal chains;
- candidate threads worth activating;
- threads that became meaningfully dormant;
- new World-to-Self links;
- one clearly labelled historical judgment.

Omit unchanged threads. Distinguish facts from interpretations and attach
inspectable source/evidence anchors. Read
[the report bundle fields](references/report-bundle.md) and persist
the report before delivery.

If the window contains no reportable delta, return exactly `[SILENT]`. Otherwise
pass the report through `"$PAP_ROOT/.venv/bin/pap" gate --agent world-historian` using a stable window
key, then return a compact simplified-Chinese report only when allowed.
