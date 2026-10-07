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

If the window contains no reportable delta, return exactly `NO_REPLY`. Otherwise
pass the report through `"$PAP_ROOT/.venv/bin/pap" gate --agent world-historian` using a stable window
key, then return a compact simplified-Chinese report only when allowed.

End every daily/weekly report with this fixed footer line:

```text
——回复条目编号或主题，即可让 World Historian 开始长期追踪。
```

Do not start tracking from the trailer itself; tracking only begins when the
user actually replies (the reply is then handled as a `news-capture` seed).
