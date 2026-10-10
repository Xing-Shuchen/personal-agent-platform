# Office v0.9 acceptance baseline

This file records portable verification criteria. Runtime observations, screenshots, selected identities, schedules, device details, and event samples belong under the ignored `var/office-floor/evidence/` directory. A green unit test or a synthetic browser fixture does not replace evidence from the target Gateway.

| Area | Implemented path | Required target evidence before claiming acceptance |
| --- | --- | --- |
| Source and rights | Pinned renderer source hashes and notices; owned map and character recipes | Confirm licensing for any additional imported asset and preserve source hashes. |
| Gateway observer | Selected agent projection, exact read-only grant, paged snapshots, subscriptions, calibration, reconnect and per-session event fences | Observe real external starts, success, failure, idle, instance replacement and interrupted runs. Record only redacted status metadata. |
| Blocking input | Explicit capability state and conservative status mapping | Observe blocking and asynchronous questions, approval, timeout and cancellation with sufficient scope; otherwise show the capability gap. |
| Tools and optional signals | Structured, instance-scoped tool receipts; compaction and handoff projections; no inference from message text | Verify actual start/update/result payloads, compaction pairs and both handoff endpoints before enabling their live claims. |
| PAP tasks | Read-only manifest, schedule and run-ledger projection; recurring occurrences ordered by dispatch time; next-hour grouping uses the viewer clock | Verify a selected job's actual dispatch and completion only after the user authorizes that job and its scheduler. Disabled previews remain conditional. |
| Browser and graphics | Strict CSP, same-origin state and SSE, full DOM roster, scene pagination, seat capacity, reduced motion and bounded graphics recovery | Test real portal authorization and iframe flow, target-browser rendering, GPU failure, foreground frame rate and event-to-visible latency. |
| Privacy | Browser receives an allowlisted FloorState; sensitive run and evidence identifiers are replaced at the response boundary; server keeps original correlation IDs | Audit production assets, responses, logs and browser storage for credentials, and exercise real permission revocation. The authorized API still includes original session keys and instance IDs as the v0.9 contract requires. |

The acceptance procedure and fallback rules are in [`docs/office_specifications_v0.9.md`](../docs/office_specifications_v0.9.md). Keep target-specific observations in ignored local evidence and report unverified capabilities explicitly.
