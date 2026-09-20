# paplog

`paplog` is PAP's local-first Activity & Provenance Ledger. Its canonical
record is the immutable `pap.event.v2` event stream in SQLite, not the legacy
`runs.jsonl` diagnostic log. By default it lives in
`$PAP_OBSERVABILITY_DIR`, then `$XDG_STATE_HOME/pap/ledger`, then
`~/.local/state/pap/ledger` and contains `events.sqlite3`, daily `jsonl/`, and
an on-disk `spool/` for failed writes.

An **operation** has duration and trace parentage (job, skill, process). An
**action** is an external or local read/side effect. A point **event** records
a semantic fact. `links` form the separate provenance graph; they do not reuse
trace parentage. The public API is intentionally small:

```python
from paplog import observe
with observe.operation("pap.job.run", job={"id": "world-historian/news-follow"}):
    with observe.action("pap.model.call", effect="execute", scope="external"):
        observe.event("pap.artifact.created", subject={"type": "event_card", "id": "..."})
```

Resource helpers (`observe.filesystem`, `observe.database`, `observe.http`,
`observe.tool`, and `observe.git`) produce the same action envelope with a
stable resource subject and `action.effect`/`action.scope` metadata.

Trace/run/operation values use `contextvars` and propagate to child commands
through `TRACEPARENT`, `PAP_RUN_ID`, `PAP_PARENT_OPERATION_ID`, `PAP_AGENT`,
`PAP_SKILL`, `PAP_JOB_ID`, and `PAP_NODE_ID`. `paplog exec -- ...` is the
backend-neutral wrapper for cron or direct commands.
When a child emits a direct point event without creating its own scope, paplog
decodes those variables and attaches that event to the parent run and skill
operation; durable child artifacts therefore do not become orphan traces.
The parent also passes its resolved `PAP_OBSERVABILITY_DIR`, so direct children
write to that same local ledger rather than silently selecting another default
state directory.
The operation context assigns `PAP_NODE_ID` before launching a child, rather
than only adding it when the parent event is persisted.
`paplog exec` records a `pap.exec` operation containing a nested
`pap.process.exec` action; non-zero exits and termination signals produce
failed action/operation events while preserving the child return code.

New PAP `run_id` values are sortable 26-character ULIDs. Artifact IDs retain
their readable `art_<type>_` prefix with a sortable ULID suffix. Existing JSONL
fields and OpenClaw session-key composition are unchanged, so operators can use
the same identifiers across legacy diagnostics and the canonical ledger.
Every canonical event receives a valid ULID `event_id`; a malformed legacy
caller-supplied value is replaced at the ledger boundary rather than persisted.

PAP emits scheduler due/dispatch events at `pap.scheduler`, run and model
events at `pap.run.invoke`, artifact lifecycle events at `pap.artifact`, and
Personal Historian ContextPack/PeriodSummary events in its runtime adapter.
Historian telemetry remains in the ledger: it is not automatically converted
into historian evidence.

For OpenClaw-backed runs, PAP additionally reads the runner's existing,
per-session `trajectory_runtime_events` records after the turn.  It translates
only the concrete `tool.call`/`tool.result` lifecycle belonging to PAP's own
session key into `pap.tool.call` actions; tool arguments and results become
hash/size metadata.  It does not infer tools from stdout.  The independently
deployable Historian's real `urllib` reconstruction client similarly emits a
`pap.model.call` action containing a nested `pap.http.request` action.  Its
request body is covered by the same metadata-only content policy.

For scheduled work, `job.id` is always the canonical manifest key
`<agent>/<job>` from due through completion. The human-facing local job name is
kept in the trigger for runner titles only. Timing fields intentionally remain
separate: `schedule_lag_ms` is due-time minus scheduled-time, while
`queue_delay_ms` on `pap.run.started` is start-time minus dispatch-time.
`execution_duration_ms` is the terminal run duration. This avoids treating a
late scheduler poll as queue contention.

## Architecture inventory and instrumentation map

PAP's declarative boundary is `agents/*/agent.yaml` (parsed by
`pap.spec.load_platform`). `pap tick` calls `pap.scheduler.tick`, which claims
slots in `var/state/scheduler-state.json`; `pap job run` and `pap invoke` are
the manual entry points. Both converge at `pap.run.invoke`. That runner starts
OpenClaw (`openclaw agent`), Codex, OpenCode, or a manifest `command`; its
single subprocess boundary emits `pap.process.exec`. OpenClaw delivery is
`pap.scheduler._deliver`; actual usage is read from its session/trajectory
SQLite by `pap.usage`. Existing `runs.jsonl`, artifact JSONL, gate state and
Cognition SQLite remain operator/domain state, not canonical paplog storage.

| Concrete boundary | Emitted event(s) |
| --- | --- |
| `due_jobs` / `tick` | `pap.schedule.due`, `pap.schedule.dispatched`, `pap.schedule.skipped` |
| `run.invoke` | nested `pap.run.*`, `pap.agent.invoke`, `pap.skill.invoke`, `pap.model.call`, and OpenClaw trajectory-backed `pap.tool.call` lifecycles |
| configured runner subprocess | `pap.process.exec` action lifecycle |
| `pap.artifact.append` | `pap.artifact.created` plus `derived_from` links |
| World Historian `world-feeds` RSS fetch/ingest command | `pap.http.request` and `pap.database.write` action lifecycles |
| Historian PAP adapter | `historian.context_pack.created`, `historian.period_summary.generated` |
| Historian `GLMChatCompletionsClient` / `DeepSeekChatCompletionsClient` | nested `pap.model.call` and `pap.http.request` action lifecycles |

Personal Historian's own execution is repository-native and independent: its
collectors write Sources/Observations, deterministic derivation writes Derived
Observations, reconstruction writes revisable Events, and the summary pipeline
creates EventCards, ThreadCards, ContextPacks and PeriodSummaries. Its
`historian.summarization.store.ArtifactStore.commit` is the durable semantic
artifact boundary and emits `historian.artifact.created` and
`historian.artifact.updated`. The Historian does not project arbitrary runtime
events into evidence; only explicit domain artifacts retain their selected
`input_refs` provenance.

Content mode defaults to `metadata`: prompts, messages, source bodies and
command output are replaced by hash/size metadata. Recursive key/pattern
redaction always removes credentials, authorization values, cookies, tokens,
passwords, and private keys—even when `PAP_LOG_CONTENT=full`.
Provider/Historian aliases such as `prompt_text`, `source_text`, and
`request_body` receive the same metadata treatment.
This applies equally to inline `KEY=value` fragments in exception messages and
environment-style lists, preventing an otherwise harmless diagnostic field from
becoming a secret bypass.

Provider-reported model costs are retained as-is. For runtimes that expose
tokens but no billed amount, an operator may set `PAPLOG_PRICING_JSON` to a
versioned table such as `{"version":"prices-2026-09","models":{"provider/model":{"input_per_million":2,"output_per_million":4,"currency":"USD"}}}`.
The ledger estimates once at ingest and records `cost.source=estimated` plus
`cost.pricing_version`; without that explicit table, cost remains unknown.

Useful commands:

```bash
paplog query --event 'pap.schedule.*' --since 7d
paplog tail --follow --interval 1
paplog run <run-id>
paplog lineage <artifact-id>
paplog cost --since 7d --group-by provider
paplog jobs --since 7d
paplog reconcile
paplog rebuild-index
paplog doctor
paplog exec --job world-historian/news-follow --agent world-historian -- <command>
```

### Implemented event catalog

`pap.schedule.due`, `pap.schedule.dispatched`, `pap.schedule.skipped`, `pap.run.started`,
`pap.run.completed`, `pap.run.failed`, `pap.agent.invoke`, `pap.skill.invoke`, `pap.operation.abandoned`,
`pap.exec` and nested `pap.process.exec` (started/completed/failed action phases), `pap.model.call`,
`pap.tool.call`, `pap.http.request`,
`pap.model.fallback`, `pap.artifact.created`, and `pap.message.send` describe PAP execution.
Resource actions include `pap.filesystem.read`, `pap.filesystem.write`, and
`pap.database.read`/`pap.database.write` where the corresponding PAP
boundaries are instrumented.
`pap.context_pack.created` records a durable Cognition context-pack write with
metadata and evidence links only.
`historian.context_pack.created`, `historian.period_summary.generated`,
`historian.artifact.created`, and `historian.artifact.updated` describe actual
Historian durable transitions. `historian.event_revision.created`,
`historian.event_revision.updated`, and `historian.event_revision.withdrawn`
record append-only reconstructed Event revisions and their lifecycle. Other
`historian.event_revision.persist`, `historian.event_revision.withdraw`,
`historian.derivation.count`, `historian.derivation.frequency`,
`historian.derivation.discontinuity`, `historian.derivation.absence`, and
`historian.reconstruction.events` describe explicit Historian operation
boundaries when PAP observability is enabled. Other names are not reserved by
this release.

SQLite failure is fail-open: events are spooled where possible and application
execution continues; the JSONL mirror is also attempted on this path.
`paplog reconcile` imports valid spool records and
quarantines malformed ones; it re-applies central redaction before importing a
record, including spools from earlier releases. `paplog rebuild-index` recreates
the disposable artifact-link, run, operation, action, and model-usage
projections from canonical events.

`paplog jobs` groups canonical scheduler and run lifecycle events by the stable
`<agent>/<job>` identity, showing due, dispatched, started, terminal counts and
the latest observed scheduling timestamps. Use `paplog query --job …` when the
underlying events are needed.

`paplog run <run-id>` renders the recorded span hierarchy rather than a flat
event list: run operations contain Agent operations, which contain skill
operations and their subprocess/model actions. Point events appear beneath the
scope whose span they inherit. Its token and cost footer aggregates all model
calls in the run rather than only the final call.

Run records carry SHA-256 definition versions for both the parsed Agent
manifest and the invoked `SKILL.md`, so the same artifact or model action can
be compared across configuration and skill changes.
When a Historian runtime prepares a ContextPack, the terminal run record also
names its artifact reference and the selected policy ID/version, without
copying the pack body.

`paplog artifacts` includes both PAP and Personal Historian durable artifact,
context-pack, and reconstructed Event-revision events by default; pass
`--event` to narrow it to a namespace.

`paplog lineage <id> --depth 3` traverses both generated-from and
derived-from directions through canonical provenance links. Traversal is
bounded and cycle-safe; use `--depth 1` for immediate neighbors only.

`paplog scheduler` derives scheduled, dispatched, missed, late, failed, and
abandoned counts plus median schedule lag, queue delay, execution duration,
observed cadence, and detected tracking-frequency inversions.

`paplog models` aggregates model-call events by provider/model with token
counts (including cache/reasoning breakdowns in the projection),
routing/credential/workload labels, cost, retries, latency, errors, and
fallback counts; use
`paplog query --event 'pap.model.*'` for raw call and fallback records.

`paplog failures` accepts the common query filters (for example
`--run <run-id> --since 1d`) and limits output to error, failed, or abandoned
outcomes.

Non-zero child exits retain their exit code on `pap.process.exec`. A signal
termination is additionally classified on the enclosing run as `signal:<n>`
(for example `signal:15` for `SIGTERM`), making an interrupted run diagnosable
without stdout/stderr capture.

When available, model calls retain the non-secret routing, credential-profile,
and workload-class identifiers from `PAP_ROUTING_PROFILE`,
`PAP_CREDENTIAL_PROFILE`, and `PAP_WORKLOAD_CLASS`. This makes `paplog cost
--group-by routing-profile` and `--group-by credential-profile` useful without
recording credentials themselves.

## Handoff and migration notes

The canonical envelope is defined in
[`paplog/pap.event.v2.schema.json`](../paplog/pap.event.v2.schema.json). The
SQLite database is created lazily under the local ledger directory; upgrading
an existing checkout is non-destructive because all projection tables are
created with `IF NOT EXISTS` and can be recreated with `paplog rebuild-index`.
Every persisted record carries `schema`, ULID `event_id`, timestamps,
`event_name`, `kind`, trace identity, execution identity, attributes, links,
and privacy metadata; operation/action records additionally carry `phase`,
outcome, duration, and exception fields when applicable.

Existing `runs.jsonl`, scheduler state, artifact JSONL, OpenClaw trajectory
data, and Historian journals remain in their original locations. No cron,
OpenClaw, Hermes, or direct-run command must be rewritten: use `paplog exec --`
for a backend-neutral wrapper, or let the instrumented PAP runner emit events
in-process. Set `PAP_OBSERVABILITY_DIR` when a job needs an explicit ledger
location; otherwise the local XDG state directory is used. Set
`PAPLOG_SHARED_ROOT` (or `PAP_ROOT`) for an independently installed Personal
Historian process to locate PAP's shared implementation. If neither is
available, the Historian bridge falls back to a side-effect-free no-op so a
standalone Historian wheel remains runnable; telemetry is enabled as soon as a
shared PAP root is configured.

## Significant file map

PAP owns the implementation: `paplog/core.py` contains the canonical SQLite,
JSONL, spool, redaction, identity, and projections layer; `paplog/observe.py`
contains the contextvars API and operation/action/resource helpers;
`paplog/cli.py` contains the operator commands; and
`paplog/pap.event.v2.schema.json` is the envelope schema. PAP integration
points are `pap/run.py`, `pap/scheduler.py`, `pap/artifact.py`, and
`pap/cognition.py`. PAP tests live in `tests/test_paplog.py` alongside the
updated runner, scheduler, artifact, and cognition tests.

Personal Historian keeps only a small bridge in `paplog/__init__.py` and an
explicit policy boundary in `historian/paplog_projection.py`. Its semantic
instrumentation is in `historian/revisions/store.py`,
`historian/summarization/store.py`, `historian/derivation/engine.py`, and
`historian/reconstruction/engine.py`, with focused coverage in
`tests/test_paplog.py`, `tests/test_paplog_projection.py`, and the revision
tests. The bridge resolves PAP via `PAPLOG_SHARED_ROOT`/`PAP_ROOT` or the
co-located source checkout and does not copy runtime telemetry into evidence.

## Verification handoff

From the PAP checkout:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. .venv/bin/python -m pytest -q -p no:cacheprovider
```

From the Personal Historian checkout:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m pytest -q -p no:cacheprovider
```

The current suites cover nested sync/async propagation, subprocess context,
non-zero exits and signals, stale-operation abandonment, WAL/concurrent writes,
spool reconciliation, central redaction, content policy, scheduler timing and
frequency inversion, model fallback/cost accounting, artifact links, rebuildable
projections, and Historian revision/derivation/reconstruction boundaries.

## Deliberately deferred

There is no central service, network dependency, OTLP exporter, dashboard, or
cross-device ledger synchronizer. PAP's OpenClaw tool boundary and Historian's
LLM HTTP boundary are instrumented where the repositories expose stable,
attributable records. Other uninstrumented collector/runtime internals do not
have a shared adapter and are not inferred from stdout or blanket-wrapped.
Personal Historian source collectors similarly retain only explicit semantic
artifact, revision, derivation, and reconstruction boundaries. These choices
preserve local-first execution and the rule that runtime telemetry does not
automatically become personal-history evidence.
