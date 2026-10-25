#!/usr/bin/env python3
"""PAP adapter for Personal Historian jobs.

The adapter is intentionally the only bridge between PAP's model turn and the
Historian's canonical store.  It supplies a sealed ContextPack to the model,
then validates and commits the response after the turn.  Configuration stays
local: ``PERSONAL_HISTORIAN_ROOT`` selects the Historian checkout,
``PERSONAL_HISTORIAN_STORE`` its artifact store, and
``PERSONAL_HISTORIAN_WATERMARKS_JSON`` provides collector/reconstruction
watermarks.  Without real watermarks the job is NOT_READY; it never invents
coverage.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys
from typing import Any

import yaml
try:  # Direct Historian maintenance remains usable without PAP installed.
    from paplog import observe as paplog
except ImportError:  # pragma: no cover - exercised only outside PAP runtime
    class _NoLedger:
        @staticmethod
        def event(*_args: Any, **_kwargs: Any) -> None:
            return None
    paplog = _NoLedger()


def _historian_root() -> Path:
    configured = os.environ.get("PERSONAL_HISTORIAN_ROOT")
    if configured:
        return Path(configured).resolve()
    return Path(__file__).resolve().parents[4] / "personal-historian-handoff"


sys.path.insert(0, str(_historian_root()))

# A missing handoff checkout is an unmet readiness condition, not a crash: the
# guarded import lets prepare answer NOT_READY (and complete answer error) with
# a clear reason instead of a ModuleNotFoundError traceback. Note the confusing
# raw error this avoids: this script's own directory contains historian.py,
# which shadows the missing package ("'historian' is not a package").
_HANDOFF_ERROR: str | None = None
try:
    from historian.summarization import (  # noqa: E402
        MIN_CREATION_EVIDENCE,
        ArtifactStore,
        CardLifecycle,
        ContextBuilder,
        SummaryRunStatus,
        ThreadRegistry,
        assess_readiness,
        candidates_for_period,
        complete_period_summary,
        create_thread,
        input_manifest_hash,
        load_policy,
        render_markdown,
        resolve_period,
        seal_with_provenance,
    )
    from historian.summarization.pipeline import parse_model_json  # noqa: E402
    from historian.revisions.store import RevisionStore  # noqa: E402
except ImportError as _import_exc:  # pragma: no cover - environment dependent
    _HANDOFF_ERROR = (
        "personal-historian handoff checkout is not importable at "
        f"PERSONAL_HISTORIAN_ROOT={_historian_root()}: {_import_exc}"
    )


def _read_stdin() -> dict[str, Any]:
    value = json.load(sys.stdin)
    if not isinstance(value, dict):
        raise ValueError("runtime input must be a JSON object")
    return value


def _state_dir() -> Path:
    path = Path(os.environ["PAP_AGENT_STATE_DIR"])
    path.mkdir(parents=True, exist_ok=True)
    return path


def _store() -> ArtifactStore:
    # Canonical artifacts belong to the Historian checkout, never PAP's
    # private run state. Deployments may point this at another Historian-owned
    # volume with PERSONAL_HISTORIAN_STORE.
    return ArtifactStore(os.environ.get("PERSONAL_HISTORIAN_STORE", str(_historian_root() / "summary-artifacts")), domain=os.environ.get("PERSONAL_HISTORIAN_DOMAIN", "personal"))


def _decode_env_json(name: str, expected: type, fallback: Any) -> Any:
    value = os.environ.get(name)
    if not value:
        return fallback
    decoded = json.loads(value)
    if not isinstance(decoded, expected):
        raise ValueError(f"{name} must encode {expected.__name__}")
    return decoded


def _watermarks() -> dict[str, datetime | None] | None:
    raw = _decode_env_json("PERSONAL_HISTORIAN_WATERMARKS_JSON", dict, None)
    if raw is None:
        discovered, watermarks = _discover_collection_state()
        # A reconstruction watermark from the revision journal counts on its
        # own; requiring coverage records too discarded it and reported
        # "watermarks are not configured" although one was found.
        return watermarks if (discovered or watermarks) else None
    result: dict[str, datetime | None] = {}
    for name, value in raw.items():
        if not isinstance(name, str) or (value is not None and not isinstance(value, str)):
            raise ValueError("watermarks must map names to ISO timestamps or null")
        result[name] = datetime.fromisoformat(value.replace("Z", "+00:00")) if value else None
    return result


def _discover_collection_state() -> tuple[list[dict[str, Any]], dict[str, datetime | None]]:
    """Read collector coverage and reconstruction progress from local state.

    Environment JSON remains an explicit override for deployments with remote
    collectors. Local installations need no hand-maintained watermark file:
    coverage runs are read from the configured collection output directory and
    Event reconstruction windows from the append-only revision journal.
    """
    root = Path(os.environ.get("PERSONAL_HISTORIAN_COLLECTION_ROOT", str(_historian_root() / "examples" / "live-run")))
    records: list[dict[str, Any]] = []
    watermarks: dict[str, datetime | None] = {}
    if root.is_dir():
        for path in sorted(root.rglob("coverage.json")):
            try:
                loaded = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            for record in loaded if isinstance(loaded, list) else [loaded]:
                if not isinstance(record, dict):
                    continue
                collector = record.get("collector", {})
                name = collector.get("collector_type") if isinstance(collector, dict) else record.get("collector")
                window = record.get("window", {})
                end = window.get("end") if isinstance(window, dict) else None
                if not isinstance(name, str) or not isinstance(end, str):
                    continue
                try:
                    watermark = datetime.fromisoformat(end.replace("Z", "+00:00"))
                except ValueError:
                    continue
                prior = watermarks.get(name)
                watermarks[name] = watermark if prior is None or watermark > prior else prior
                records.append({"source": name, "status": _coverage_status(record), "note": f"collector coverage from {path.name}"})
    revision_root = Path(os.environ.get("PERSONAL_HISTORIAN_REVISIONS", str(_historian_root() / "revisions")))
    journal = revision_root / "revisions.jsonl"
    if journal.is_file():
        ends: list[datetime] = []
        for line in journal.read_text(encoding="utf-8").splitlines():
            try:
                reason = json.loads(line)["record"]["revision"].get("change_reason", "")
            except (KeyError, TypeError, json.JSONDecodeError):
                continue
            match = re.search(r"over \[[^,]+,([^\)]+)\)", reason)
            if match:
                try:
                    ends.append(datetime.fromisoformat(match.group(1).strip().replace("Z", "+00:00")))
                except ValueError:
                    pass
        if ends:
            watermarks["reconstruction"] = max(ends)
    return records, watermarks


def _coverage_status(record: dict[str, Any]) -> str:
    """Map collector coverage onto the ContextPack vocabulary (§15).

    ``unknown`` must stay ``unknown``.  Zhihu's retention window makes feed
    completeness unknowable, and reporting that as ``poor`` would assert a
    coverage gap the collector never measured — the exact confusion between
    "no evidence" and "evidence of absence" this project forbids.  A failed
    collection is missing data, not poor data.
    """

    status = record.get("status")
    ratio = record.get("coverage_ratio")
    if status == "covered":
        return "complete" if ratio == 1 else "good"
    if status == "partial":
        return "partial"
    if status == "failed":
        return "missing"
    return "unknown"


def _coverage() -> list[dict[str, Any]]:
    override = _decode_env_json("PERSONAL_HISTORIAN_COVERAGE_JSON", list, None)
    if override is not None:
        return override
    records, _ = _discover_collection_state()
    latest: dict[str, dict[str, Any]] = {}
    for record in records:
        latest[record["source"]] = record
    return [latest[key] for key in sorted(latest)]


def _manifest(candidates: list[dict[str, Any]], watermarks: dict[str, datetime | None], coverage: list[dict[str, Any]]) -> dict[str, Any]:
    refs = [candidate["artifact_ref"] for candidate in candidates]
    payload = json.dumps({"refs": refs, "watermarks": {name: value.isoformat() if value else None for name, value in watermarks.items()}, "coverage": coverage}, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "generator": "pap.personal-historian.runtime/v1",
        "input_refs": refs,
        "input_manifest_hash": hashlib.sha256(payload.encode("utf-8")).hexdigest(),
    }


def _context_path(run_id: str) -> Path:
    directory = _state_dir() / "context"
    directory.mkdir(parents=True, exist_ok=True)
    return directory / f"{run_id}.json"


def _prepared_path(run_id: str) -> Path:
    directory = _state_dir() / "prepared"
    directory.mkdir(parents=True, exist_ok=True)
    return directory / f"{run_id}.json"


def _literary_path(summary_id: str) -> Path:
    directory = _state_dir() / "literary"
    directory.mkdir(parents=True, exist_ok=True)
    return directory / f"{summary_id.replace(':', '_')}.md"


def _vault_dir() -> Path | None:
    """Resolve the Second Brain vault without making its config mandatory."""
    configured = os.environ.get("PERSONAL_HISTORIAN_OBSIDIAN_VAULT")
    if configured and configured.strip():
        return Path(configured).expanduser().resolve()
    try:
        repositories = json.loads((_historian_root() / "config" / "repositories.json").read_text(encoding="utf-8"))
        if isinstance(repositories, dict):
            repositories = repositories.get("repositories")
        if not isinstance(repositories, list):
            return None
        for repository in repositories:
            if isinstance(repository, dict) and repository.get("name") == "second-brain":
                path = repository.get("path")
                if isinstance(path, str) and path.strip():
                    return Path(path).expanduser().resolve()
    except (OSError, json.JSONDecodeError, TypeError):
        pass
    return None


def _obsidian_literary_path(period: Any) -> Path | None:
    vault = _vault_dir()
    if vault is None:
        return None
    target = (vault / "Dairies" / str(period.start.year) /
              f"summary_week_{period.label}.md").resolve()
    if vault not in target.parents:
        raise ValueError("literary target escapes the configured Obsidian vault")
    return target


def _missing_week_diaries(period: Any) -> list[str]:
    vault = _vault_dir()
    if vault is None:
        return []
    missing: list[str] = []
    cursor = period.start
    while cursor < period.end_exclusive:
        day = cursor.date()
        diary = vault / "Dairies" / str(day.year) / f"{day.isoformat()}.md"
        try:
            present = diary.is_file() and bool(diary.read_text(encoding="utf-8").strip())
        except OSError:
            present = False
        if not present:
            missing.append(day.isoformat())
        cursor += timedelta(days=1)
    return missing


def _canonical_hash(value: dict[str, Any]) -> str:
    encoded = json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _card_id(event_id: str) -> str:
    return "event-card:" + event_id.split(":", 1)[1]


def _thread_card_id(thread_id: str) -> str:
    return "thread-card:" + thread_id.split(":", 1)[1]


#: How many events one model turn may be asked to card, and how much material it
#: may carry. One turn per event made the cost scale with the number of events
#: (110 for three weeks of history) when it should scale with the amount of
#: material; batching keeps each prompt a sane size while cutting the turns by an
#: order of magnitude.
EVENT_BATCH_MAX = 20
EVENT_BATCH_MAX_CHARS = 120_000


def _pending_event_cards(revisions: RevisionStore, store: ArtifactStore) -> list[dict[str, Any]]:
    """The Event revisions that still need a card, with their fixed identities."""

    pending: list[dict[str, Any]] = []
    for event in revisions.get_current_revisions():
        event_ref = {
            "artifact_id": event["event_id"],
            "revision": event["revision"]["number"],
            "content_hash": _canonical_hash(event),
        }
        card_id = _card_id(event["event_id"])
        current = store.latest(card_id)
        if current and current.get("event_ref") == event_ref and not store.is_stale(card_id):
            continue
        if current and current.get("event_ref") != event_ref:
            # Event revisions live in the v0.1 revision store, outside the
            # summary artifact graph. Bridge that boundary explicitly before
            # asking a model to construct the replacement card.
            store.mark_stale(card_id, reason=f"Event revision changed: {event['event_id']}")
        pending.append({
            "event": event,
            "event_ref": event_ref,
            "event_card_id": card_id,
            "revision": (current["revision"] + 1) if current else 1,
        })
    return pending


def _prepare_event_card(payload: dict[str, Any]) -> dict[str, Any]:
    revisions_root = Path(os.environ.get("PERSONAL_HISTORIAN_REVISIONS", str(_historian_root() / "revisions")))
    revisions = RevisionStore(revisions_root, domain=os.environ.get("PERSONAL_HISTORIAN_DOMAIN", "personal"))
    store = _store()
    pending = _pending_event_cards(revisions, store)
    if not pending:
        return {"status": "not_ready", "reason": "no current Event revision needs an EventCard refresh"}

    batch: list[dict[str, Any]] = []
    characters = 0
    for item in pending:
        size = len(json.dumps(item["event"], ensure_ascii=False))
        if batch and (len(batch) >= EVENT_BATCH_MAX or characters + size > EVENT_BATCH_MAX_CHARS):
            break
        batch.append(item)
        characters += size

    prepared = {
        "kind": "event-batch",
        "cards": [{"event_ref": item["event_ref"], "event_card_id": item["event_card_id"],
                   "revision": item["revision"]} for item in batch],
    }
    _prepared_path(payload["run_id"]).write_text(json.dumps(prepared, ensure_ascii=False), encoding="utf-8")
    return {
        "status": "ready",
        "input_text": (
            f"Create exactly one EventCard JSON object for each of the {len(batch)} Event revisions below, and "
            "return them as {\"event_cards\": [...]}. Each card's event_card_id and revision are fixed and given "
            "with its event; use the given event_ref verbatim. One card per event, no extras.\n\n"
            + json.dumps({"events": [item["event"] for item in batch], "cards": prepared["cards"]},
                         ensure_ascii=False)
        ),
        "metadata": {"event_cards_offered": len(batch), "event_cards_pending": len(pending)},
    }


def _prepare_thread_card(payload: dict[str, Any]) -> dict[str, Any]:
    store = _store()
    registry = ThreadRegistry(store.root)
    cards = [record for record in store.latest_records() if record["artifact_type"] == "historian.event-card.v1"]
    for thread_id in sorted(registry.ids):
        evidence = [card for card in cards if thread_id in card.get("thread_ids", [])]
        if not evidence:
            continue
        card_id = _thread_card_id(thread_id)
        current = store.latest(card_id)
        current_refs = {
            (ref.get("artifact_id"), ref.get("content_hash"))
            for ref in (current or {}).get("evidence_refs", [])
        }
        candidate_refs = {(card["event_card_id"], card["content_hash"]) for card in evidence}
        if current and candidate_refs.issubset(current_refs) and not store.is_stale(card_id):
            continue
        prepared = {"kind": "thread", "thread_id": thread_id, "thread_card_id": card_id,
                    "revision": (current["revision"] + 1) if current else 1,
                    "input_refs": [{"artifact_id": card["event_card_id"], "revision": card["revision"],
                                    "content_hash": card["content_hash"]} for card in evidence]}
        _prepared_path(payload["run_id"]).write_text(json.dumps(prepared, ensure_ascii=False), encoding="utf-8")
        return {"status": "ready", "input_text": "Update exactly one registered ThreadCard. Its immutable identity and revision are fixed below. Return JSON only.\n\n" + json.dumps({"prior_thread_card": current, "event_cards": evidence, **prepared}, ensure_ascii=False)}

    # Bootstrapping: until a thread exists, no thread can be updated.  EventCards
    # that belong to no registered thread are offered as a possible new thread,
    # but only the model may judge whether they show a persistent process (§7);
    # it answers NO_NEW_THREAD when they do not.
    #
    # "Unassigned" means not cited as evidence by any ThreadCard.  EventCards are
    # produced with whatever thread_ids the model supplied — often none — so
    # treating an empty thread_ids list as unassigned would offer the same events
    # again every week and fragment one process into a new thread each time.
    cited: set[str] = set()
    for record in store.latest_records():
        if record["artifact_type"] == "historian.thread-card.v1":
            cited.update(ref.get("artifact_id") for ref in record.get("evidence_refs", []))
    uncovered = [card for card in cards if card["event_card_id"] not in cited]
    if len(uncovered) < MIN_CREATION_EVIDENCE:
        return {"status": "not_ready",
                "reason": f"no registered thread has EventCard evidence, and {len(uncovered)} unassigned "
                          f"event(s) is below the {MIN_CREATION_EVIDENCE} needed as evidence of persistence"}
    prepared = {
        "kind": "thread-creation", "revision": 1,
        "event_card_ids": [card["event_card_id"] for card in uncovered],
        "input_refs": [{"artifact_id": card["event_card_id"], "revision": card["revision"],
                        "content_hash": card["content_hash"]} for card in uncovered],
    }
    _prepared_path(payload["run_id"]).write_text(json.dumps(prepared, ensure_ascii=False), encoding="utf-8")
    return {"status": "ready", "input_text":
            "Propose at most ONE new ThreadCard for these EventCards, or reply exactly NO_NEW_THREAD if they "
            "do not evidence a persistent process (multiple distinct events, cross-period continuity, a "
            "long-running project, or a persistent unresolved issue). One event is activity, not a thread. "
            "Identity and thread_card_id are derived from canonical_name by the Historian, so supply the name "
            "only; cite at least two of these EventCards verbatim as evidence_refs. Return JSON only.\n\n"
            + json.dumps({"event_cards": uncovered, **prepared}, ensure_ascii=False)}


def _current_events() -> list[dict[str, Any]]:
    """The reconstructed Event revisions a summary may reach back to (§10).

    EventCards live in the artifact store but the Events they compress live in
    the v0.1 revision journal, so the adapter supplies them: the Historian then
    decides which of them a period may see, and only ever the exact revision a
    card is bound to.
    """

    root = Path(os.environ.get("PERSONAL_HISTORIAN_REVISIONS", str(_historian_root() / "revisions")))
    domain = os.environ.get("PERSONAL_HISTORIAN_DOMAIN", "personal")
    try:
        return list(RevisionStore(root, domain=domain).get_current_revisions())
    except Exception:
        # An unreadable journal is a coverage gap, not a reason to fail a summary.
        return []


def _prepare_summary(payload: dict[str, Any]) -> dict[str, Any]:
    args = payload["args"]
    kind = args.get("kind")
    selector = args.get("period", "previous")
    if kind not in {"week", "month", "quarter", "halfyear"}:
        return {"status": "error", "error": "summary job needs a supported kind"}
    zone = args.get("timezone", os.environ.get("PERSONAL_HISTORIAN_TIMEZONE", "Asia/Shanghai"))
    if not isinstance(zone, str):
        return {"status": "error", "error": "summary timezone must be a string"}
    period = resolve_period(kind, selector, zone)
    watermarks = _watermarks()
    if watermarks is None:
        return {"status": "not_ready", "reason": "collector/reconstruction watermarks are not configured"}
    if "reconstruction" not in watermarks:
        return {"status": "not_ready", "reason": "reconstruction watermark is unavailable"}
    readiness = assess_readiness(period, watermarks)
    if readiness["status"] != "ready":
        return {"status": "not_ready", "reason": json.dumps(readiness, ensure_ascii=False)}
    store = _store()
    missing_children = _missing_child_summaries(store, period)
    if missing_children:
        return {"status": "not_ready", "reason": "required child summaries are missing: " + ", ".join(missing_children)}
    if kind == "week":
        if _vault_dir() is None:
            return {"status": "not_ready", "reason": "obsidian vault is not configured"}
        missing_diaries = _missing_week_diaries(period)
    candidates = candidates_for_period(store, period, events=_current_events())
    coverage = _coverage()
    policy_path = os.environ.get("PERSONAL_HISTORIAN_POLICY", str(_historian_root() / "config" / "historical-summary-policy.yaml"))
    context = ContextBuilder(domain=store.domain, policy=load_policy(policy_path, kind)).build(
        period=period, candidates=candidates, readiness=readiness, coverage=coverage,
        provenance=_manifest(candidates, watermarks, coverage),
    )
    _context_path(payload["run_id"]).write_text(json.dumps(context, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    # The ContextPack is an execution artifact and may be retained (§4); keeping
    # it in the canonical store is what lets §41 report what the model was
    # actually offered, including when the run then failed.  Artifacts are
    # immutable revisions, so the store allocates the revision: identical content
    # is a no-op and changed content becomes the next revision.
    store.commit(store.allocate(context))
    paplog.event("historian.context_pack.created", subject={"type": "context_pack", "id": context["context_pack_id"]},
                 execution={"run_id": payload["run_id"], "operation_id": payload["run_id"]},
                 attributes={"input_item_count": len(candidates), "estimated_tokens": context.get("token_budget", {}).get("allocated"), "policy": context.get("policy", {})},
                 links=[{"type": "derived_from", "target_type": "artifact", "target_id": ref["artifact_id"]} for ref in context["provenance"]["input_refs"] if isinstance(ref, dict) and ref.get("artifact_id")])
    summary_id = f"summary:{kind}:{period.label}"
    existing = store.latest(summary_id)
    if existing and existing.get("provenance", {}).get("input_manifest_hash") == context["provenance"]["input_manifest_hash"] and not store.is_stale(summary_id):
        return {"status": "not_ready", "reason": "identical summary input is already committed"}
    prepared = {"kind": "summary", "summary_id": summary_id, "revision": (existing["revision"] + 1) if existing else 1}
    _prepared_path(payload["run_id"]).write_text(json.dumps(prepared, ensure_ascii=False), encoding="utf-8")
    metadata = {"context_pack_id": context["context_pack_id"], "period": period.label, "policy_id": context["policy"]["name"], "policy_version": context["policy"]["version"], "idempotency_key": f"{kind}:{period.label}:{context['provenance']['input_manifest_hash']}"}
    if kind == "week":
        metadata["missing_diaries"] = missing_diaries
    return {"status": "ready", "input_text": "Create exactly one PeriodSummary JSON object for this sealed ContextPack. Do not add prose or use evidence outside it. summary_id and revision are fixed below.\n\n" + json.dumps({"context_pack": context, **prepared}, ensure_ascii=False), "metadata": metadata}


def _prepare_literary(payload: dict[str, Any]) -> dict[str, Any]:
    args = payload["args"]
    if args.get("kind") != "week":
        return {"status": "error", "error": "literary rendering currently supports week only"}
    zone = args.get("timezone", os.environ.get("PERSONAL_HISTORIAN_TIMEZONE", "Asia/Shanghai"))
    period = resolve_period("week", args.get("period", "previous"), zone)
    summary_id = f"summary:week:{period.label}"
    summary = _store().latest(summary_id)
    if summary is None:
        return {"status": "not_ready", "reason": f"canonical summary is missing: {summary_id}"}
    if _store().is_stale(summary_id):
        return {"status": "not_ready", "reason": f"canonical summary is stale: {summary_id}"}
    literary_meta = _literary_path(summary_id).with_suffix(".json")
    try:
        previous_render = json.loads(literary_meta.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        previous_render = None
    if isinstance(previous_render, dict) and previous_render.get("summary_hash") == summary["content_hash"]:
        return {"status": "not_ready", "reason": "weekly literary render already committed for this summary revision"}
    prepared = {
        "kind": "literary", "summary_id": summary_id,
        "summary_revision": summary["revision"], "summary_hash": summary["content_hash"],
        "period": period.to_dict(),
    }
    period_data = summary["period"]
    required_properties = {
        "schema_version": 1,
        "week": period_data["label"],
        "type": "ethnography-weekly",
        "status": summary["status"],
        "period_start": period_data["start"][:10],
        "period_end": (datetime.fromisoformat(period_data["end_exclusive"]) - timedelta(days=1)).date().isoformat(),
    }
    _prepared_path(payload["run_id"]).write_text(json.dumps(prepared, ensure_ascii=False), encoding="utf-8")
    return {
        "status": "ready",
        "input_text": (
            "Render this canonical PeriodSummary as one human-facing weekly narrative. "
            "The summary is the factual boundary; return Markdown only.\n\n"
            "Copy these required values verbatim into the YAML Properties:\n\n```yaml\n" +
            yaml.safe_dump(required_properties, sort_keys=False) + "```\n\n" +
            json.dumps({"period_summary": summary}, ensure_ascii=False)
        ),
        "metadata": {
            "period": period.label,
            "idempotency_key": f"literary:{summary_id}:{summary['content_hash']}",
        },
    }


def _missing_child_summaries(store: ArtifactStore, period: Any) -> list[str]:
    child_kind = {"month": "week", "quarter": "month", "halfyear": "quarter"}.get(period.kind.value)
    if child_kind is None:
        return []
    children = [record["summary_id"] for record in store.latest_records() if record["artifact_type"] == "historian.period-summary.v1" and record.get("period", {}).get("kind") == child_kind and _period_inside(record.get("period", {}), period)]
    expected = _expected_children(child_kind, period)
    return sorted(set(expected) - set(children))


def _period_inside(child: dict[str, Any], parent: Any) -> bool:
    try:
        return datetime.fromisoformat(child["start"]) >= parent.start and datetime.fromisoformat(child["end_exclusive"]) <= parent.end_exclusive
    except (KeyError, TypeError, ValueError):
        return False


def _expected_children(kind: str, period: Any) -> list[str]:
    labels: list[str] = []
    cursor = period.start
    while cursor < period.end_exclusive:
        if kind == "week":
            iso = cursor.isocalendar()
            label = f"{iso.year}-W{iso.week:02d}"
        elif kind == "month":
            label = f"{cursor.year}-{cursor.month:02d}"
        else:
            label = f"{cursor.year}-Q{(cursor.month - 1) // 3 + 1}"
        candidate = resolve_period(kind, label, period.timezone)
        if candidate.start >= period.start and candidate.end_exclusive <= period.end_exclusive:
            labels.append(f"summary:{kind}:{label}")
        cursor = candidate.end_exclusive
    return labels


def prepare(payload: dict[str, Any]) -> dict[str, Any]:
    if payload.get("skill") == "historian-literary-renderer":
        return _prepare_literary(payload)
    if payload.get("skill") == "historian-period-summary":
        return _prepare_summary(payload)
    if payload.get("skill") == "historian-event-card":
        return _prepare_event_card(payload)
    if payload.get("skill") == "historian-thread-card":
        return _prepare_thread_card(payload)
    return {"status": "error", "error": "unsupported historian skill"}


def _failure(kind: str, error: Exception) -> dict[str, Any]:
    """Report a failure PAP can classify (§34).

    ``failure_kind`` says whether retrying could help. Anything the Historian
    rejected — a schema violation, an invented reference, a changed identity — is
    deterministic: the same input fails the same way, so §34 forbids retrying it
    blindly. Transient trouble (a timed-out or failed model runner) is reported by
    PAP itself and stays retryable.
    """

    return {"status": "error", "failure_kind": kind, "error": str(error)}


def _provider(model: str | None) -> str | None:
    if not isinstance(model, str) or "/" not in model:
        return None
    provider = model.split("/", 1)[0].strip()
    return provider or None


def _runtime_provenance(input_refs: list[dict[str, Any]], *, manifest_hash: str | None = None) -> dict[str, Any]:
    """Provenance the runtime can actually vouch for.

    A model can write plausible values for the clock, the generator and the input
    manifest hash, but it cannot know them — and staleness detection (§23) rests
    entirely on the manifest hash.  These fields are therefore established here
    and overwrite whatever the model asserted.
    """

    model = os.environ.get("PAP_AGENT_MODEL") or None
    provider = os.environ.get("PAP_AGENT_PROVIDER") or _provider(model)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "generator": "pap.personal-historian.runtime/v1",
        "input_refs": input_refs,
        "input_manifest_hash": manifest_hash or input_manifest_hash(input_refs),
        "model": model,
        "provider": provider,
    }


def complete(payload: dict[str, Any]) -> dict[str, Any]:
    if payload.get("skill") == "historian-literary-renderer":
        return _complete_literary(payload)
    if payload.get("skill") == "historian-event-card":
        return _complete_event_card(payload)
    if payload.get("skill") == "historian-thread-card":
        return _complete_thread_card(payload)
    if payload.get("skill") != "historian-period-summary":
        return {"status": "error", "error": "unsupported historian skill"}
    path = _context_path(str(payload["run_id"]))
    if not path.is_file():
        return {"status": "error", "error": "prepared ContextPack is missing"}
    context = json.loads(path.read_text(encoding="utf-8"))
    try:
        prepared = json.loads(_prepared_path(str(payload["run_id"])).read_text(encoding="utf-8"))
        candidate = parse_model_json(str(payload.get("model_reply", "")))
    except Exception as exc:
        return _failure("model_output", exc)
    if candidate.get("summary_id") != prepared["summary_id"] or candidate.get("revision") != prepared["revision"]:
        return _failure("model_output", ValueError(
            "model changed the fixed PeriodSummary identity or revision"))
    try:
        # The summary's provenance is the sealed ContextPack's, not the model's.
        # Discard the model block wholesale.  Keeping unknown nested fields made
        # a model-authored ``provenance.content_hash`` survive the merge and
        # fail strict schema validation even though provenance is runtime-owned.
        candidate["provenance"] = {}
        candidate = seal_with_provenance(candidate, _runtime_provenance(
            list(context["provenance"]["input_refs"]),
            manifest_hash=context["provenance"]["input_manifest_hash"],
        ))
    except Exception as exc:
        return _failure("validation", exc)
    result = complete_period_summary(context, json.dumps(candidate, ensure_ascii=False), _store())
    if result.status is SummaryRunStatus.SUCCESS:
        summary = result.commit.artifact if result.commit else {}
        rendered = _state_dir() / "rendered"
        rendered.mkdir(parents=True, exist_ok=True)
        (rendered / f"{summary['summary_id'].replace(':', '_')}.md").write_text(render_markdown(summary), encoding="utf-8")
        refs = summary.get("provenance", {}).get("input_refs", [])
        paplog.event("historian.period_summary.generated", subject={"type": "period_summary", "id": summary["summary_id"]},
                     execution={"run_id": payload["run_id"], "operation_id": payload["run_id"]},
                     attributes={"revision": summary["revision"], "model": summary.get("provenance", {}).get("model"), "provider": summary.get("provenance", {}).get("provider")},
                     links=[{"type": "derived_from", "target_type": "artifact", "target_id": ref["artifact_id"]} for ref in refs if isinstance(ref, dict) and ref.get("artifact_id")])
        return {"status": "success", "response": "NO_REPLY", "warnings": list(result.warnings), "metadata": {"result_summary_id": summary["summary_id"], "summary_revision": summary["revision"]}}
    if result.status is SummaryRunStatus.NOT_READY:
        return {"status": "not_ready", "reason": "ContextPack became not ready"}
    if result.status is SummaryRunStatus.FAILED_COMMIT:
        return {"status": "error", "failure_kind": "commit",
                "error": result.error or result.status.value, "warnings": list(result.warnings)}
    return {"status": "error", "failure_kind": "validation",
            "error": result.error or result.status.value, "warnings": list(result.warnings)}


def _complete_literary(payload: dict[str, Any]) -> dict[str, Any]:
    try:
        prepared = json.loads(_prepared_path(str(payload["run_id"])).read_text(encoding="utf-8"))
        reply = str(payload.get("model_reply", "")).strip()
        # Some capable models add a brief compliance acknowledgement before an
        # otherwise valid document. Projection may discard that transport
        # chatter, but it must never attempt to repair or rewrite the prose.
        frontmatter_start = reply.find("---\n")
        if frontmatter_start < 0:
            raise ValueError("literary renderer must return YAML Properties")
        document = reply[frontmatter_start:]
        closing = document.find("\n---", 4)
        if closing < 0:
            raise ValueError("literary renderer returned unterminated YAML Properties")
        properties = yaml.safe_load(document[4:closing])
        if not isinstance(properties, dict):
            raise ValueError("literary renderer Properties must be a mapping")
        summary = _store().latest(prepared["summary_id"])
        if summary is None or summary.get("content_hash") != prepared["summary_hash"]:
            return {"status": "not_ready", "reason": "canonical summary changed during rendering"}
        period_data = summary["period"]
        expected = {
            "schema_version": 1,
            "week": period_data["label"],
            "type": "ethnography-weekly",
            "status": summary["status"],
            "period_start": period_data["start"][:10],
            "period_end": (datetime.fromisoformat(period_data["end_exclusive"]) - timedelta(days=1)).date().isoformat(),
        }
        for key, value in expected.items():
            actual = properties.get(key)
            if hasattr(actual, "isoformat"):
                actual = actual.isoformat()
            if actual != value:
                raise ValueError(f"literary renderer Property {key!r} must equal {value!r}")
        index_keys = ("people", "projects", "topics", "artifacts", "phrases", "scenes", "threads")
        for key in index_keys:
            values = properties.get(key)
            if not isinstance(values, list) or not all(isinstance(value, str) and value.strip() for value in values):
                raise ValueError(f"literary renderer Property {key!r} must be a string list")
        allowed = set(expected) | set(index_keys)
        if set(properties) != allowed:
            raise ValueError("literary renderer returned unknown or missing Properties")
        body = document[closing + 4:].lstrip()
        if not body.startswith("# "):
            raise ValueError("literary renderer narrative must begin with a level-1 heading")
        markdown = document.strip()
        if "```" in markdown or len(markdown) < 200:
            raise ValueError("literary renderer returned an empty or wrapped document")
        forbidden = ("event-card:", "thread-card:", "observation:", "## Basis", "**Status:**")
        leaked = [token for token in forbidden if token in markdown]
        if leaked:
            raise ValueError("literary renderer exposed audit-layer material: " + ", ".join(leaked))
        state_target = _literary_path(prepared["summary_id"])
        state_target.write_text(markdown + "\n", encoding="utf-8")
        period = resolve_period("week", prepared["period"]["label"], prepared["period"]["timezone"])
        vault_target = _obsidian_literary_path(period)
        if vault_target is not None:
            vault_target.parent.mkdir(parents=True, exist_ok=True)
            temporary = vault_target.with_suffix(vault_target.suffix + ".tmp")
            temporary.write_text(markdown + "\n", encoding="utf-8")
            os.replace(temporary, vault_target)
        state_target.with_suffix(".json").write_text(json.dumps({
            "summary_revision": prepared["summary_revision"], "summary_hash": prepared["summary_hash"],
        }, ensure_ascii=False) + "\n", encoding="utf-8")
        return {
            "status": "success", "response": "NO_REPLY",
            "metadata": {
                "result_summary_id": prepared["summary_id"],
                "summary_revision": prepared["summary_revision"],
                "literary_path": str(state_target),
                "obsidian_path": str(vault_target) if vault_target else None,
            },
        }
    except Exception as exc:
        return _failure("model_output", exc)


def _complete_event_card(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate and commit a batch of cards, one per offered Event revision.

    Each card is validated on its own: §33 requires that a model artifact failing
    validation is not committed, and it says nothing about discarding the rest of
    a batch. Rejected cards are reported rather than silently dropped, and a batch
    in which nothing validates is an error so the run cannot look like a no-op.
    """

    try:
        prepared = json.loads(_prepared_path(str(payload["run_id"])).read_text(encoding="utf-8"))
        reply = parse_model_json(str(payload.get("model_reply", "")))
        offered = {item["event_card_id"]: item for item in prepared["cards"]}
        raw_cards = reply.get("event_cards")
        if raw_cards is None and "event_card_id" in reply:
            raw_cards = [reply]  # a batch of one, answered as a bare card
        if not isinstance(raw_cards, list) or not raw_cards:
            raise ValueError("model reply must contain a non-empty 'event_cards' list")
    except Exception as exc:
        return _failure("model_output", exc)

    store = _store()
    lifecycle = CardLifecycle(store)
    committed: list[str] = []
    rejected: list[dict[str, str]] = []
    for card in raw_cards:
        if not isinstance(card, dict):
            rejected.append({"event_card_id": "", "error": "not a JSON object"})
            continue
        identity = str(card.get("event_card_id", ""))
        fixed = offered.get(identity)
        if fixed is None:
            rejected.append({"event_card_id": identity,
                             "error": "not one of the Event revisions that were offered"})
            continue
        if card.get("revision") != fixed["revision"]:
            rejected.append({"event_card_id": identity,
                             "error": "model changed the fixed EventCard revision"})
            continue
        try:
            # The Event revision is the card's input; the runtime states that, not the model.
            sealed = seal_with_provenance(card, _runtime_provenance([dict(fixed["event_ref"])]))
            lifecycle.commit_event_card(sealed, event_ref=fixed["event_ref"])
        except Exception as exc:
            rejected.append({"event_card_id": identity, "error": str(exc)})
        else:
            committed.append(identity)

    missing = sorted(set(offered) - {card.get("event_card_id") for card in raw_cards
                                     if isinstance(card, dict)})
    metadata = {"event_cards_committed": committed, "event_cards_rejected": rejected,
                "event_cards_missing": missing}
    if not committed:
        return {"status": "error", "failure_kind": "validation",
                "error": f"no card in the batch validated; rejected {len(rejected)}",
                "metadata": metadata}
    return {"status": "success", "response": "NO_REPLY", "metadata": metadata}


def _normalize_thread_milestones(card: dict[str, Any]) -> list[dict[str, str]]:
    """Flatten only known, losslessly representable milestone object shapes.

    The schema stays strict.  A date is retained alongside its summary; extra
    fields or non-string values need a corrected model reply, not coercion.
    Normalizations become run metadata so this repair remains observable.
    """
    milestones = card.get("milestones")
    if not isinstance(milestones, list):
        return []  # Schema validation names the missing or mistyped list.
    normalized: list[Any] = []
    changes: list[dict[str, str]] = []
    for index, milestone in enumerate(milestones):
        field = f"milestones/{index}"
        if not isinstance(milestone, dict):
            normalized.append(milestone)  # Leave string/type checks to the schema.
            continue
        if set(milestone) - {"date", "summary"}:
            raise ValueError(
                f"{field}: expected only 'summary' and optional 'date'; "
                "extra fields cannot be normalized losslessly; return a milestone string"
            )
        summary = milestone.get("summary")
        if not isinstance(summary, str) or not summary.strip():
            raise ValueError(f"{field}/summary: expected a non-empty string; return a milestone string")
        if "date" in milestone:
            date = milestone["date"]
            if not isinstance(date, str) or not date.strip():
                raise ValueError(f"{field}/date: expected a non-empty string; return a milestone string")
            normalized.append(f"{date}: {summary}")
            operation = "date-summary-to-string"
        else:
            normalized.append(summary)
            operation = "summary-to-string"
        changes.append({"field": field, "operation": operation})
    card["milestones"] = normalized
    return changes


def _complete_thread_card(payload: dict[str, Any]) -> dict[str, Any]:
    try:
        store = _store()
        prepared = json.loads(_prepared_path(str(payload["run_id"])).read_text(encoding="utf-8"))
        if prepared.get("kind") == "thread-creation":
            return _complete_thread_creation(payload, prepared, store)
        card = parse_model_json(str(payload.get("model_reply", "")))
        if (card.get("thread_id") != prepared["thread_id"] or card.get("thread_card_id") != prepared["thread_card_id"] or card.get("revision") != prepared["revision"]):
            raise ValueError("model changed the fixed ThreadCard identity or revision")
        normalizations = _normalize_thread_milestones(card)
        card = seal_with_provenance(card, _runtime_provenance(list(prepared["input_refs"])))
        CardLifecycle(store, ThreadRegistry(store.root)).commit_thread_card(card)
    except Exception as exc:
        return _failure("validation", exc)
    return {"status": "success", "response": "NO_REPLY",
            "metadata": {"output_normalizations": normalizations}}


#: The model's escape hatch when the offered events do not evidence a thread.
NO_NEW_THREAD = "NO_NEW_THREAD"


def _complete_thread_creation(payload: dict[str, Any], prepared: dict[str, Any],
                              store: ArtifactStore) -> dict[str, Any]:
    """Create at most one thread, with identity derived by the Historian (§7)."""

    reply = str(payload.get("model_reply", "")).strip()
    if reply == NO_NEW_THREAD:
        # Declining is a legitimate outcome, not a failure: one week of events
        # often shows activity rather than a persistent process.
        return {"status": "success", "response": NO_NEW_THREAD,
                "metadata": {"thread_created": None}}
    card = parse_model_json(reply)
    if card.get("revision") != prepared["revision"]:
        raise ValueError("model changed the fixed ThreadCard revision")
    normalizations = _normalize_thread_milestones(card)
    registry = ThreadRegistry(store.root)
    provenance = _runtime_provenance(list(prepared["input_refs"]))
    # The runtime owns provenance (§21); the model only drafts it.  Seal the
    # draft *before* create_thread() validates it, because that validation runs
    # against the schema and would otherwise reject a card whose provenance is
    # missing the runtime-owned fields (input_manifest_hash, ...) that the seal
    # below is about to supply.  Identity and content_hash are recomputed inside
    # create_thread(), so the card is sealed once more afterwards.
    card = seal_with_provenance(card, provenance)
    created = create_thread(card, registry=registry,
                            known_event_card_ids=prepared["event_card_ids"])
    created = seal_with_provenance(created, provenance)
    CardLifecycle(store, registry).commit_thread_card(created)
    return {"status": "success", "response": "NO_REPLY",
            "metadata": {"thread_created": created["thread_id"],
                         "thread_card_id": created["thread_card_id"],
                         "output_normalizations": normalizations}}


def main() -> int:
    if _HANDOFF_ERROR is not None and len(sys.argv) == 2 and sys.argv[1] in {"prepare", "complete"}:
        payload = ({"status": "not_ready", "reason": _HANDOFF_ERROR} if sys.argv[1] == "prepare"
                   else {"status": "error", "error": _HANDOFF_ERROR})
        print(json.dumps(payload, ensure_ascii=False))
        return 0
    if len(sys.argv) != 2 or sys.argv[1] not in {"prepare", "complete"}:
        raise SystemExit("usage: historian.py prepare|complete")
    output = prepare(_read_stdin()) if sys.argv[1] == "prepare" else complete(_read_stdin())
    print(json.dumps(output, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
