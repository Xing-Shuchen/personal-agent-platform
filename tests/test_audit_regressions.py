"""Regression tests for defects confirmed in the 2026-10 platform audit.

Each test pins one fixed defect so it cannot silently return:

* a job whose runtime adapter is missing must fail ``pap validate`` and, if it
  slips through, finalize as a non-retryable ``config`` failure — never abort
  the whole tick and strand the other reserved jobs;
* a ``last_tick_at`` in the future (clock jump, ``tick --now`` mistake) must
  not stall the scheduler;
* a manifest job with ``enabled: false`` must stay off for manual runs too;
* deferred deliveries get a bounded retry budget instead of being dropped on
  the first failed send;
* gate decisions are serialized (no duplicate allowances for one dedupe key);
* local config may pin per-job models (tracked manifests stay route-free);
* dry-run previews do not pollute scheduler health statistics;
* JSONL readers tolerate a truncated line;
* paplog emit is fail-open for malformed caller values and never fabricates a
  zero cost.
"""

from __future__ import annotations

import json
import subprocess
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from pap import scheduler as scheduler_mod
from pap.cli import main as cli_main
from pap.gate import decide
from pap.run import invoke, is_retryable, runs
from pap.spec import SpecError, load_platform, load_spec
from pap.state import read_jsonl, save_json

CST = timezone(timedelta(hours=8))


def make_platform(root: Path, *, second_job: bool = False, runtime_job: bool = False) -> None:
    """A synthetic two/three-job platform with command runners (no model calls)."""
    skill_dir = root / "agents/sample/profile/skills/sample-skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nname: sample-skill\ndescription: Test.\n---\n# Test\n", encoding="utf-8")
    jobs = """      - name: healthy-job
        schedule: "17 18 * * *"
        skill: sample-skill
        delivery: local
        runner: command
        command: ["true"]
"""
    if second_job:
        jobs += """      - name: second-job
        schedule: "17 18 * * *"
        skill: sample-skill
        delivery: local
        runner: command
        command: ["true"]
"""
    if runtime_job:
        jobs += """      - name: runtime-job
        schedule: "17 18 * * *"
        skill: sample-skill
        runtime: sample-adapter
        delivery: local
"""
    (root / "agents/sample/agent.yaml").write_text(
        "apiVersion: pap/v1\n"
        "kind: Agent\n"
        "metadata:\n"
        "  name: sample\n"
        "  description: Sample.\n"
        "spec:\n"
        "  profile:\n"
        "    name: sample\n"
        "    source: profile\n"
        "  proactive:\n"
        "    enabled: true\n"
        "    class: ambient\n"
        "    desired_jobs:\n" + jobs,
        encoding="utf-8")


# ---------------------------------------------------------------------------
# runtime adapter misconfiguration


def test_missing_runtime_adapter_fails_platform_validation(tmp_path):
    make_platform(tmp_path, runtime_job=True)  # no runtime/sample-adapter.py
    with pytest.raises(SpecError, match="runtime adapter not found"):
        load_platform(tmp_path)


def test_runtime_adapter_deleted_after_load_finalizes_as_config_failure(tmp_path, monkeypatch):
    """invoke() must not leak an orphan run.started or raise past the tick."""
    make_platform(tmp_path, runtime_job=True)
    adapter = tmp_path / "agents/sample/runtime/sample-adapter.py"
    adapter.parent.mkdir(parents=True)
    adapter.write_text("# present at validate time\n", encoding="utf-8")
    spec = load_spec(tmp_path / "agents/sample/agent.yaml")
    adapter.unlink()  # deleted between validate and dispatch

    run_log = tmp_path / "runs.jsonl"
    result = invoke(root=tmp_path, spec=spec, skill="sample-skill",
                    runtime="sample-adapter", run_log=run_log)
    assert result.status == "failed"
    assert result.failure_kind == "config"
    assert not is_retryable(result.failure_kind)
    events = [json.loads(line)["event"] for line in run_log.read_text().splitlines()]
    assert events.count("run.started") == events.count("run.completed") == 1
    record = runs(run_log)[0]
    assert record["status"] == "failed" and record["retryable"] is False


def test_one_crashing_job_does_not_strand_the_other_reserved_jobs(tmp_path, monkeypatch):
    make_platform(tmp_path, second_job=True)
    monkeypatch.setattr(scheduler_mod, "JITTER_MAX_MINUTES", 0)
    now = datetime(2026, 10, 10, 18, 17, tzinfo=CST)
    real_invoke = scheduler_mod.invoke

    def crashing_invoke(**kwargs):
        if (kwargs.get("trigger") or {}).get("job_name") == "healthy-job":
            raise RuntimeError("simulated unexpected crash")
        return real_invoke(**kwargs)

    monkeypatch.setattr(scheduler_mod, "invoke", crashing_invoke)
    results = scheduler_mod.tick(tmp_path, now=now)
    by_key = {item.job_key: item for item in results}
    # The crashing job settles as failed + non-retryable ...
    assert by_key["sample/healthy-job"].delivery == "tick-error"
    assert by_key["sample/healthy-job"].run is None
    # ... and the other reserved job still runs in the same tick.
    assert by_key["sample/second-job"].run.status == "success"

    state = json.loads((tmp_path / "var/state/scheduler-state.json").read_text())
    entry = state["jobs"]["sample/healthy-job"]
    assert entry["last_status"] == "failed"
    assert entry["last_retryable"] is False
    log = (tmp_path / "var/state/runs.jsonl").read_text()
    assert "tick.job_error" in log
    # The next minute does not re-run the settled job.
    monkeypatch.setattr(scheduler_mod, "invoke", real_invoke)
    assert scheduler_mod.tick(tmp_path, now=now + timedelta(minutes=1)) == []


# ---------------------------------------------------------------------------
# scheduler stall protection


def test_runtime_adapter_prepare_timeout_is_retryable(tmp_path, monkeypatch):
    """A slow prepare is transient trouble (§34): kind 'timeout', retryable."""
    make_platform(tmp_path, runtime_job=True)
    adapter = tmp_path / "agents/sample/runtime/sample-adapter.py"
    adapter.parent.mkdir(parents=True)
    adapter.write_text("import time\ntime.sleep(30)\n", encoding="utf-8")
    spec = load_spec(tmp_path / "agents/sample/agent.yaml")
    monkeypatch.setenv("PAP_RUNTIME_TIMEOUT_SECONDS", "1")
    result = invoke(root=tmp_path, spec=spec, skill="sample-skill",
                    runtime="sample-adapter", run_log=tmp_path / "runs.jsonl")
    assert result.status == "failed"
    assert result.failure_kind == "timeout"
    assert is_retryable(result.failure_kind)


def test_future_last_tick_at_does_not_stall_the_scheduler(tmp_path, monkeypatch):
    make_platform(tmp_path)
    monkeypatch.setattr(scheduler_mod, "JITTER_MAX_MINUTES", 0)
    state_path = tmp_path / "var/state/scheduler-state.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    now = datetime(2026, 10, 10, 18, 17, tzinfo=CST)
    save_json(state_path, {"version": 1, "jobs": {},
                           "last_tick_at": (now + timedelta(days=80)).isoformat(timespec="seconds")})
    due = scheduler_mod.due_jobs(tmp_path, now=now, state_path=state_path, reserve=False)
    assert [item.key for item in due] == ["sample/healthy-job"]


# ---------------------------------------------------------------------------
# disabled jobs stay off everywhere


def test_manual_run_of_a_disabled_job_is_rejected(tmp_path, capsys):
    make_platform(tmp_path)
    manifest = tmp_path / "agents/sample/agent.yaml"
    manifest.write_text(
        manifest.read_text(encoding="utf-8").replace(
            '        command: ["true"]', '        command: ["true"]\n        enabled: false'),
        encoding="utf-8")
    assert cli_main(["job", "run", "sample/healthy-job", "--root", str(tmp_path)]) == 2
    assert "disabled" in capsys.readouterr().err
    assert not (tmp_path / "var/state/runs.jsonl").exists()


def test_manual_run_of_an_enabled_job_still_works(tmp_path):
    make_platform(tmp_path)
    assert cli_main(["job", "run", "sample/healthy-job", "--root", str(tmp_path)]) == 0


# ---------------------------------------------------------------------------
# deferred delivery retries


def _queue(tmp_path: Path, deliver_at: datetime) -> Path:
    path = tmp_path / "delivery-queue.json"
    save_json(path, {"version": 1, "entries": [{
        "run_id": "run_1", "job_key": "sample/healthy-job", "response": "morning brief",
        "deliver_at": deliver_at.isoformat(),
        "created_at": deliver_at.isoformat(timespec="seconds"),
    }]})
    return path


def test_deferred_delivery_retries_then_sends(tmp_path, monkeypatch):
    monkeypatch.setenv("PAP_OPENCLAW_CHANNEL", "test-channel")
    monkeypatch.setenv("PAP_OPENCLAW_ACCOUNT", "test-account")
    deliver_at = datetime(2026, 10, 10, 8, 0, tzinfo=CST)
    path = _queue(tmp_path, deliver_at)
    run_log = tmp_path / "runs.jsonl"
    attempts = []

    def failing_then_ok(command, **kwargs):
        attempts.append(command)
        code = 1 if len(attempts) < 2 else 0
        return subprocess.CompletedProcess(command, code, "", "")

    now = deliver_at + timedelta(minutes=1)
    scheduler_mod._drain_deferred_deliveries(
        path, now=now, run_log=run_log, target="ou_test", sender=failing_then_ok)
    entries = json.loads(path.read_text())["entries"]
    assert len(entries) == 1 and entries[0]["attempts"] == 1  # requeued, not dropped
    assert "deferred-retrying" in run_log.read_text()

    # Before retry_after the entry waits; after it, the retry sends.
    scheduler_mod._drain_deferred_deliveries(
        path, now=now + timedelta(minutes=1), run_log=run_log,
        target="ou_test", sender=failing_then_ok)
    assert len(attempts) == 1  # still inside the retry delay
    scheduler_mod._drain_deferred_deliveries(
        path, now=now + scheduler_mod.DELIVERY_RETRY_DELAY, run_log=run_log,
        target="ou_test", sender=failing_then_ok)
    assert len(attempts) == 2
    assert json.loads(path.read_text())["entries"] == []
    assert "deferred-sent" in run_log.read_text()


def test_deferred_delivery_expires_after_the_retry_budget(tmp_path, monkeypatch):
    monkeypatch.setenv("PAP_OPENCLAW_CHANNEL", "test-channel")
    monkeypatch.setenv("PAP_OPENCLAW_ACCOUNT", "test-account")
    deliver_at = datetime(2026, 10, 10, 8, 0, tzinfo=CST)
    path = _queue(tmp_path, deliver_at)
    run_log = tmp_path / "runs.jsonl"

    def always_fails(command, **kwargs):
        return subprocess.CompletedProcess(command, 1, "", "")

    now = deliver_at
    for step in range(scheduler_mod.MAX_DELIVERY_ATTEMPTS):
        scheduler_mod._drain_deferred_deliveries(
            path, now=now + timedelta(minutes=5 * step + 1), run_log=run_log,
            target="ou_test", sender=always_fails)
    assert json.loads(path.read_text())["entries"] == []
    assert "deferred-expired" in run_log.read_text()


# ---------------------------------------------------------------------------
# gate serialization


def test_concurrent_gate_decisions_allow_one_delivery_per_key(tmp_path):
    db = tmp_path / "gate-state.json"
    allowed = []
    barrier = threading.Barrier(8)

    def ask():
        barrier.wait()
        decision = decide("sample", "concept:key", 95, db_path=db)
        if decision.allowed:
            allowed.append(decision)

    threads = [threading.Thread(target=ask) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert len(allowed) == 1
    state = json.loads(db.read_text())
    assert state["agents"]["sample"]["delivered"]["concept:key"]


# ---------------------------------------------------------------------------
# local per-job model overrides


def _model_job_platform(root: Path) -> None:
    """Platform whose job uses the default (openclaw) runner and may take a model."""
    skill_dir = root / "agents/sample/profile/skills/sample-skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nname: sample-skill\ndescription: Test.\n---\n# Test\n", encoding="utf-8")
    (root / "agents/sample/agent.yaml").write_text(
        "apiVersion: pap/v1\n"
        "kind: Agent\n"
        "metadata:\n"
        "  name: sample\n"
        "  description: Sample.\n"
        "spec:\n"
        "  profile:\n"
        "    name: sample\n"
        "    source: profile\n"
        "  proactive:\n"
        "    enabled: true\n"
        "    class: ambient\n"
        "    desired_jobs:\n"
        "      - name: pulse-job\n"
        '        schedule: "17 18 * * *"\n'
        "        skill: sample-skill\n"
        "        delivery: local\n",
        encoding="utf-8")


def test_local_config_pins_a_job_model_without_touching_the_manifest(tmp_path):
    _model_job_platform(tmp_path)
    config = tmp_path / "var/config"
    config.mkdir(parents=True)
    (config / "agents.yaml").write_text(
        "agents:\n"
        "  sample:\n"
        "    enabled: true\n"
        "    jobs:\n"
        "      pulse-job: {model: test-provider/test-model}\n",
        encoding="utf-8")
    spec = load_platform(tmp_path)[0]
    assert spec.jobs[0].model == "test-provider/test-model"
    # The tracked manifest itself stays route-free.
    assert "model" not in (tmp_path / "agents/sample/agent.yaml").read_text(encoding="utf-8")


@pytest.mark.parametrize("override,match", [
    ("jobs: {nope: {model: p/m}}", "unknown job"),
    ("jobs: {pulse-job: {route: p/m}}", "unknown job override keys"),
    ("jobs: {pulse-job: {model: '  '}}", "non-empty string"),
])
def test_invalid_job_overrides_are_rejected(tmp_path, override, match):
    _model_job_platform(tmp_path)
    config = tmp_path / "var/config"
    config.mkdir(parents=True)
    (config / "agents.yaml").write_text(
        f"agents:\n  sample:\n    enabled: true\n    {override}\n", encoding="utf-8")
    with pytest.raises(SpecError, match=match):
        load_platform(tmp_path)


def test_command_runner_jobs_cannot_take_a_model_override(tmp_path):
    make_platform(tmp_path)
    config = tmp_path / "var/config"
    config.mkdir(parents=True)
    (config / "agents.yaml").write_text(
        "agents:\n  sample: {enabled: true, jobs: {healthy-job: {model: p/m}}}\n",
        encoding="utf-8")
    with pytest.raises(SpecError, match="runner 'command'"):
        load_platform(tmp_path)


# ---------------------------------------------------------------------------
# dry-run hygiene


def test_dry_run_preview_emits_no_schedule_due_events(tmp_path, monkeypatch):
    from paplog import observe

    make_platform(tmp_path)
    monkeypatch.setattr(scheduler_mod, "JITTER_MAX_MINUTES", 0)
    observe.configure(tmp_path / "ledger")
    now = datetime(2026, 10, 10, 18, 17, tzinfo=CST)
    scheduler_mod.due_jobs(tmp_path, now=now, reserve=False)
    assert observe.get_ledger().query(event="pap.schedule.due") == []
    scheduler_mod.due_jobs(tmp_path, now=now, reserve=True)
    assert len(observe.get_ledger().query(event="pap.schedule.due")) == 1


# ---------------------------------------------------------------------------
# JSONL reader tolerance


def test_read_jsonl_skips_a_truncated_line(tmp_path):
    path = tmp_path / "runs.jsonl"
    path.write_text('{"event":"run.started","run_id":"a"}\n{"event": "run.comp\n'
                    '{"event":"run.completed","run_id":"a","status":"success"}\n',
                    encoding="utf-8")
    records = read_jsonl(path)
    assert [record["event"] for record in records] == ["run.started", "run.completed"]
    assert runs(path)[0]["status"] == "success"


# ---------------------------------------------------------------------------
# paplog fail-open contract


def test_emit_survives_malformed_timestamp_and_unserializable_attributes(tmp_path):
    from paplog import observe

    ledger = observe.configure(tmp_path / "ledger")
    event = ledger.emit({
        "event_name": "pap.test.event",
        "timestamp": "not-a-timestamp",
        "attributes": {"path": Path("/tmp/example")},
    })
    assert isinstance(event["timestamp"], str)
    datetime.fromisoformat(event["timestamp"])  # replaced, not raised
    stored = ledger.query(event="pap.test.event")
    assert len(stored) == 1


def test_pricing_estimator_never_fabricates_zero_cost(tmp_path, monkeypatch):
    from paplog import observe

    pricing = tmp_path / "pricing.json"
    pricing.write_text(json.dumps({
        "version": "v1",
        "models": {"test-provider/test-model": {"input_per_million": 10,
                                                "output_per_million": 20}},
    }), encoding="utf-8")
    monkeypatch.setenv("PAPLOG_PRICING_JSON", str(pricing))
    ledger = observe.configure(tmp_path / "ledger")
    absent = ledger.emit({
        "event_name": "pap.model.call",
        "attributes": {"provider": "test-provider", "requested_model": "test-model",
                       "input_tokens": None, "output_tokens": None},
    })
    assert "cost.amount" not in absent["attributes"]
    measured = ledger.emit({
        "event_name": "pap.model.call",
        "attributes": {"provider": "test-provider", "requested_model": "test-model",
                       "input_tokens": 1000, "output_tokens": 500},
    })
    assert measured["attributes"]["cost.amount"] == pytest.approx(0.02)
    assert measured["attributes"]["cost.source"] == "estimated"


# ---------------------------------------------------------------------------
# corrupt scheduler state surfaces clearly


def test_status_reports_corrupt_scheduler_state(tmp_path, capsys):
    make_platform(tmp_path)
    state_path = tmp_path / "var/state/scheduler-state.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text("{not json", encoding="utf-8")
    assert cli_main(["status", "--root", str(tmp_path), "--state", str(state_path)]) == 2
    assert "unreadable" in capsys.readouterr().err
