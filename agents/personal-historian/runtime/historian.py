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

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys
from typing import Any


def _historian_root() -> Path:
    configured = os.environ.get("PERSONAL_HISTORIAN_ROOT")
    if configured:
        return Path(configured).resolve()
    return Path(__file__).resolve().parents[4] / "personal-historian-handoff"


sys.path.insert(0, str(_historian_root()))

from historian.summarization import (  # noqa: E402
    ArtifactStore,
    CardLifecycle,
    ContextBuilder,
    SummaryRunStatus,
    ThreadRegistry,
    assess_readiness,
    candidates_for_period,
    complete_period_summary,
    load_policy,
    render_markdown,
    resolve_period,
)
from historian.summarization.pipeline import parse_model_json  # noqa: E402
from historian.revisions.store import RevisionStore  # noqa: E402


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
        return watermarks if discovered else None
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
    root = Path(os.environ.get("PERSONAL_HISTORIAN_COLLECTION_ROOT", str(_historian_root() / "collection-runs")))
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
                ratio = record.get("coverage_ratio", 0)
                status = "complete" if record.get("status") == "covered" and ratio == 1 else ("partial" if record.get("status") in {"covered", "partial"} else "poor")
                records.append({"source": name, "status": status, "note": f"collector coverage from {path.name}"})
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


def _canonical_hash(value: dict[str, Any]) -> str:
    encoded = json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _card_id(event_id: str) -> str:
    return "event-card:" + event_id.split(":", 1)[1]


def _thread_card_id(thread_id: str) -> str:
    return "thread-card:" + thread_id.split(":", 1)[1]


def _prepare_event_card(payload: dict[str, Any]) -> dict[str, Any]:
    revisions_root = Path(os.environ.get("PERSONAL_HISTORIAN_REVISIONS", str(_historian_root() / "revisions")))
    revisions = RevisionStore(revisions_root, domain=os.environ.get("PERSONAL_HISTORIAN_DOMAIN", "personal"))
    store = _store()
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
        next_revision = (current["revision"] + 1) if current else 1
        prepared = {"kind": "event", "event_ref": event_ref, "event_card_id": card_id, "revision": next_revision}
        _prepared_path(payload["run_id"]).write_text(json.dumps(prepared, ensure_ascii=False), encoding="utf-8")
        return {"status": "ready", "input_text": "Create exactly one EventCard JSON object for this Event revision. Its event_card_id and revision are fixed below; use event_ref verbatim.\n\n" + json.dumps({"event": event, **prepared}, ensure_ascii=False)}
    return {"status": "not_ready", "reason": "no current Event revision needs an EventCard refresh"}


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
        prepared = {"kind": "thread", "thread_id": thread_id, "thread_card_id": card_id, "revision": (current["revision"] + 1) if current else 1}
        _prepared_path(payload["run_id"]).write_text(json.dumps(prepared, ensure_ascii=False), encoding="utf-8")
        return {"status": "ready", "input_text": "Update exactly one registered ThreadCard. Its immutable identity and revision are fixed below. Return JSON only.\n\n" + json.dumps({"prior_thread_card": current, "event_cards": evidence, **prepared}, ensure_ascii=False)}
    return {"status": "not_ready", "reason": "no registered thread has EventCard evidence"}


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
    candidates = candidates_for_period(store, period)
    coverage = _coverage()
    policy_path = os.environ.get("PERSONAL_HISTORIAN_POLICY", str(_historian_root() / "config" / "historical-summary-policy.yaml"))
    context = ContextBuilder(domain=store.domain, policy=load_policy(policy_path, kind)).build(
        period=period, candidates=candidates, readiness=readiness, coverage=coverage,
        provenance=_manifest(candidates, watermarks, coverage),
    )
    _context_path(payload["run_id"]).write_text(json.dumps(context, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary_id = f"summary:{kind}:{period.label}"
    existing = store.latest(summary_id)
    if existing and existing.get("provenance", {}).get("input_manifest_hash") == context["provenance"]["input_manifest_hash"] and not store.is_stale(summary_id):
        return {"status": "not_ready", "reason": "identical summary input is already committed"}
    prepared = {"kind": "summary", "summary_id": summary_id, "revision": (existing["revision"] + 1) if existing else 1}
    _prepared_path(payload["run_id"]).write_text(json.dumps(prepared, ensure_ascii=False), encoding="utf-8")
    return {"status": "ready", "input_text": "Create exactly one PeriodSummary JSON object for this sealed ContextPack. Do not add prose or use evidence outside it. summary_id and revision are fixed below.\n\n" + json.dumps({"context_pack": context, **prepared}, ensure_ascii=False), "metadata": {"context_pack_id": context["context_pack_id"], "period": period.label, "idempotency_key": f"{kind}:{period.label}:{context['provenance']['input_manifest_hash']}"}}


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
    if payload.get("skill") == "historian-period-summary":
        return _prepare_summary(payload)
    if payload.get("skill") == "historian-event-card":
        return _prepare_event_card(payload)
    if payload.get("skill") == "historian-thread-card":
        return _prepare_thread_card(payload)
    return {"status": "error", "error": "unsupported historian skill"}


def complete(payload: dict[str, Any]) -> dict[str, Any]:
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
        if candidate.get("summary_id") != prepared["summary_id"] or candidate.get("revision") != prepared["revision"]:
            raise ValueError("model changed the fixed PeriodSummary identity or revision")
    except Exception as exc:
        return {"status": "error", "error": str(exc)}
    result = complete_period_summary(context, json.dumps(candidate, ensure_ascii=False), _store())
    if result.status is SummaryRunStatus.SUCCESS:
        summary = result.commit.artifact if result.commit else {}
        rendered = _state_dir() / "rendered"
        rendered.mkdir(parents=True, exist_ok=True)
        (rendered / f"{summary['summary_id'].replace(':', '_')}.md").write_text(render_markdown(summary), encoding="utf-8")
        return {"status": "success", "response": "NO_REPLY", "warnings": list(result.warnings), "metadata": {"result_summary_id": summary["summary_id"], "summary_revision": summary["revision"]}}
    if result.status is SummaryRunStatus.NOT_READY:
        return {"status": "not_ready", "reason": "ContextPack became not ready"}
    return {"status": "error", "error": result.error or result.status.value, "warnings": list(result.warnings)}


def _complete_event_card(payload: dict[str, Any]) -> dict[str, Any]:
    try:
        prepared = json.loads(_prepared_path(str(payload["run_id"])).read_text(encoding="utf-8"))
        card = parse_model_json(str(payload.get("model_reply", "")))
        if card.get("event_card_id") != prepared["event_card_id"] or card.get("revision") != prepared["revision"]:
            raise ValueError("model changed the fixed EventCard identity or revision")
        CardLifecycle(_store()).commit_event_card(card, event_ref=prepared["event_ref"])
    except Exception as exc:
        return {"status": "error", "error": str(exc)}
    return {"status": "success", "response": "NO_REPLY"}


def _complete_thread_card(payload: dict[str, Any]) -> dict[str, Any]:
    try:
        store = _store()
        prepared = json.loads(_prepared_path(str(payload["run_id"])).read_text(encoding="utf-8"))
        card = parse_model_json(str(payload.get("model_reply", "")))
        if (card.get("thread_id") != prepared["thread_id"] or card.get("thread_card_id") != prepared["thread_card_id"] or card.get("revision") != prepared["revision"]):
            raise ValueError("model changed the fixed ThreadCard identity or revision")
        CardLifecycle(store, ThreadRegistry(store.root)).commit_thread_card(card)
    except Exception as exc:
        return {"status": "error", "error": str(exc)}
    return {"status": "success", "response": "NO_REPLY"}


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in {"prepare", "complete"}:
        raise SystemExit("usage: historian.py prepare|complete")
    output = prepare(_read_stdin()) if sys.argv[1] == "prepare" else complete(_read_stdin())
    print(json.dumps(output, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
