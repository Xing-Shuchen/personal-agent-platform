"""Tests for scheduler slot reservation and delivery silence."""

import json
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

from pap.run import RunResult
from pap.scheduler import _deliver, tick

CST = timezone(timedelta(hours=8))


def make_platform(root: Path, schedule: str = "* * * * *") -> None:
    skill = root / "agents/sample/profile/skills/sample-skill"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text(
        "---\nname: sample-skill\ndescription: Test.\n---\n# Test\n", encoding="utf-8"
    )
    (root / "agents/sample/agent.yaml").write_text(
        f"""apiVersion: pap/v1
kind: Agent
metadata:
  name: sample
  description: Sample.
spec:
  profile:
    name: sample
    source: profile
  proactive:
    enabled: true
    class: ambient
    desired_jobs:
      - name: sample-job
        schedule: "{schedule}"
        skill: sample-skill
        delivery: local
""",
        encoding="utf-8",
    )


def test_tick_claims_slot_once(tmp_path):
    make_platform(tmp_path)
    now = datetime(2026, 8, 31, 18, 17, tzinfo=CST)
    calls = []

    def fake_runner(command, **kwargs):
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, stdout="NO_REPLY", stderr="")

    first = tick(tmp_path, now=now, command_runner=fake_runner)
    second = tick(tmp_path, now=now, command_runner=fake_runner)
    assert len(first) == 1
    assert first[0].delivery == "silent"
    assert second == []
    assert len(calls) == 1


def test_dry_run_does_not_create_scheduler_state(tmp_path):
    make_platform(tmp_path)
    now = datetime(2026, 8, 31, 18, 17, tzinfo=CST)
    result = tick(tmp_path, now=now, dry_run=True)
    assert len(result) == 1
    assert result[0].delivery == "dry-run"
    assert not (tmp_path / "var/state/scheduler-state.json").exists()


def test_slot_jitter_is_stable_and_stays_within_five_minutes():
    from pap.scheduler import _jitter_minutes

    slot = datetime(2026, 8, 31, 18, 17, tzinfo=CST)
    first = _jitter_minutes("test-seed", "sample/sample-job", slot)
    assert first == _jitter_minutes("test-seed", "sample/sample-job", slot)
    assert -5 <= first <= 5


def test_negative_jitter_can_dispatch_before_the_nominal_slot(tmp_path, monkeypatch):
    from pap.scheduler import due_jobs

    make_platform(tmp_path, "17 18 * * *")
    slot = datetime(2026, 8, 31, 18, 17, tzinfo=CST)
    monkeypatch.setattr("pap.scheduler._jitter_minutes", lambda *_: -5)

    due = due_jobs(tmp_path, now=slot - timedelta(minutes=5), reserve=False)
    assert [(item.slot, item.jitter_minutes) for item in due] == [(slot, -5)]


def test_positive_jitter_delays_dispatch_after_the_nominal_slot(tmp_path, monkeypatch):
    from pap.scheduler import due_jobs

    make_platform(tmp_path, "17 18 * * *")
    slot = datetime(2026, 8, 31, 18, 17, tzinfo=CST)
    monkeypatch.setattr("pap.scheduler._jitter_minutes", lambda *_: 5)

    assert due_jobs(tmp_path, now=slot + timedelta(minutes=4), reserve=False) == []
    due = due_jobs(tmp_path, now=slot + timedelta(minutes=5), reserve=False)
    assert [(item.slot, item.jitter_minutes) for item in due] == [(slot, 5)]


def test_failed_slot_is_retried_after_delay(tmp_path, monkeypatch):
    make_platform(tmp_path, "17 18 * * *")
    now = datetime(2026, 8, 31, 18, 17, tzinfo=CST)
    monkeypatch.setattr("pap.scheduler._now", lambda: now)
    monkeypatch.setattr("pap.scheduler.JITTER_MAX_MINUTES", 0)
    calls = []

    def failing_runner(command, **kwargs):
        calls.append(command)
        return subprocess.CompletedProcess(command, 1, stdout="", stderr="failed")

    first = tick(tmp_path, now=now, command_runner=failing_runner)
    retry = tick(tmp_path, now=now + timedelta(minutes=6), command_runner=failing_runner)
    assert first[0].run.status == "failed"
    assert retry[0].slot == first[0].slot
    assert len(calls) == 2


def test_intentional_silence_marker_shapes():
    from pap.scheduler import _intentional_silence

    # OpenClaw's contract: the whole response is exactly NO_REPLY.
    assert _intentional_silence("NO_REPLY")
    assert not _intentional_silence("NO REPLY")
    assert not _intentional_silence("工作集核对完毕：无到期线程。\nNO_REPLY")
    assert not _intentional_silence("[SILENT]")
    assert not _intentional_silence("")
    assert not _intentional_silence("   ")


def test_requests_silence_when_no_reply_is_a_standalone_line():
    from pap.scheduler import _requests_silence

    assert _requests_silence("NO_REPLY")
    assert _requests_silence("NO_REPLY\n（扫描窗口 2026-09-11 14:10→15:10：无值得打断的开发项）")
    assert _requests_silence("扫描完成。\nNO_REPLY\n无需发送。")
    assert not _requests_silence("今日增量：git 提交 3 条")
    assert not _requests_silence("NO_REPLY 后附内容")


def test_delivery_uses_openclaw_gateway(monkeypatch):
    result = RunResult(
        run_id="run_test", agent_id="sample", skill="sample-skill", status="success",
        returncode=0, response="hello", error="", started_at="", completed_at="", usage={},
    )
    job = type("Job", (), {"delivery": "user-home"})()
    calls = []

    def sender(command, **kwargs):
        calls.append((command, kwargs))
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setenv("PAP_OPENCLAW_CHANNEL", "feishu")
    monkeypatch.setenv("PAP_OPENCLAW_ACCOUNT", "feishu4")
    monkeypatch.setenv("PAP_OPENCLAW_BIN", "/usr/local/bin/openclaw")
    assert _deliver(result, job, target="ou_test", sender=sender) == "sent"
    assert calls == [(
        ["/usr/local/bin/openclaw", "message", "send", "--channel", "feishu",
         "--account", "feishu4", "--target", "ou_test", "--message", "hello"],
        {"capture_output": True, "text": True, "timeout": 60},
    )]


def test_delivery_suppresses_leaked_tool_echo():
    result = RunResult(
        run_id="run_test", agent_id="sample", skill="sample-skill", status="success",
        returncode=0,
        response=(
            "Let me verify one candidate delta before deciding on delivery "
            "(whether Buckmaster's call for an independent investigation is already in the record).\n"
            'db = sqlite3.connect("file:/home/xingzeng/personal-agent-platform/'
            'var/world-historian/chronicle.sqlite?mode=ro", uri=True)'
        ),
        error="", started_at="", completed_at="", usage={},
    )
    job = type("Job", (), {"delivery": "user-home"})()

    def sender(*args, **kwargs):
        raise AssertionError("leaked output must not be sent")

    assert _deliver(result, job, target="ou_test", sender=sender) == "leaked-suppressed"


def test_delivery_suppresses_openclaw_missing_final_summary_fallback():
    result = RunResult(
        run_id="run_test", agent_id="sample", skill="sample-skill", status="success",
        returncode=0,
        response=(
            "The tool run finished, but no final summary was produced. "
            "I did not repeat any completed actions."
        ),
        error="", started_at="", completed_at="", usage={},
    )
    job = type("Job", (), {"delivery": "user-home"})()

    def sender(*args, **kwargs):
        raise AssertionError("OpenClaw fallback text must not be sent")

    assert _deliver(result, job, target="ou_test", sender=sender) == "leaked-suppressed"


def test_delivery_suppresses_no_reply_with_model_prose():
    result = RunResult(
        run_id="run_test", agent_id="sample", skill="sample-skill", status="success",
        returncode=0,
        response="NO_REPLY\n扫描窗口：无值得打断的开发项。",
        error="", started_at="", completed_at="", usage={},
    )
    job = type("Job", (), {"delivery": "user-home"})()

    def sender(*args, **kwargs):
        raise AssertionError("NO_REPLY with prose must not be sent")

    assert _deliver(result, job, target="ou_test", sender=sender) == "silence-suppressed"


def test_delivery_sends_normal_chinese_brief():
    result = RunResult(
        run_id="run_test", agent_id="sample", skill="sample-skill", status="success",
        returncode=0, response="今日增量：git 提交 3 条；重构出 9 个事件；commit abc123",
        error="", started_at="", completed_at="", usage={},
    )
    job = type("Job", (), {"delivery": "user-home"})()
    calls = []

    def sender(command, **kwargs):
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    assert _deliver(result, job, target="ou_test", sender=sender) == "sent"
    assert calls


def test_a_rejected_run_is_not_retried_but_transient_trouble_is(tmp_path):
    """§34: never blindly retry output the Historian already rejected."""
    from pap.scheduler import due_jobs

    make_platform(tmp_path, "17 18 * * *")
    slot = datetime(2026, 8, 31, 18, 17, tzinfo=CST)
    state_path = tmp_path / "state.json"

    for retryable, expect_due in ((False, False), (True, True)):
        with (tmp_path / "state.json").open("w", encoding="utf-8") as handle:
            json.dump({"jobs": {"sample/sample-job": {
                "last_slot": slot.isoformat(timespec="minutes"),
                "last_status": "failed",
                "last_retryable": retryable,
                "attempts": 1,
                # The scheduler measures the retry delay from when the run finished.
                "last_finished_at": (slot + timedelta(minutes=1)).isoformat(timespec="seconds"),
            }}}, handle)
        # Retrying stays within the same slot period.
        due = due_jobs(tmp_path, now=slot + timedelta(minutes=10), state_path=state_path, reserve=False)
        assert bool(due) is expect_due, f"last_retryable={retryable}"


def test_a_pre_existing_failed_slot_without_a_classification_is_not_retried(tmp_path):
    """State written before failures were classified must not be retried blindly."""
    from pap.scheduler import due_jobs

    make_platform(tmp_path, "17 18 * * *")
    slot = datetime(2026, 8, 31, 18, 17, tzinfo=CST)
    state_path = tmp_path / "state.json"
    state_path.write_text(json.dumps({"jobs": {"sample/sample-job": {
        "last_slot": slot.isoformat(timespec="minutes"),
        "last_status": "failed",
        "attempts": 1,
        "last_finished_at": (slot + timedelta(minutes=1)).isoformat(timespec="seconds"),
    }}}), encoding="utf-8")
    assert due_jobs(tmp_path, now=slot + timedelta(minutes=10), state_path=state_path, reserve=False) == []


def test_a_disabled_job_is_declared_but_never_due(tmp_path):
    """§40 stages a rollout: a job may exist and be auditable without running."""
    from pap.scheduler import due_jobs
    from pap.spec import load_spec

    make_platform(tmp_path, "17 18 * * *")
    spec_path = tmp_path / "agents/sample/agent.yaml"
    spec_path.write_text(spec_path.read_text(encoding="utf-8").replace(
        "        delivery: local", "        delivery: local\n        enabled: false"), encoding="utf-8")
    spec = load_spec(spec_path)
    assert spec.jobs[0].enabled is False

    now = datetime(2026, 8, 31, 18, 17, tzinfo=CST)
    assert due_jobs(tmp_path, now=now, reserve=False) == []


def test_a_staged_rollout_keeps_the_declaration_visible(tmp_path):
    """Disabling must not delete the job, or enabling would need rewriting it."""
    from pap.spec import load_spec

    make_platform(tmp_path, "17 18 * * *")
    spec_path = tmp_path / "agents/sample/agent.yaml"
    spec_path.write_text(spec_path.read_text(encoding="utf-8").replace(
        "        delivery: local", "        delivery: local\n        enabled: false"), encoding="utf-8")
    spec = load_spec(spec_path)
    assert [job.name for job in spec.jobs] == ["sample-job"]
    assert spec.jobs[0].schedule == "17 18 * * *"


def test_enabled_must_be_a_boolean(tmp_path):
    from pap.spec import SpecError, load_spec

    make_platform(tmp_path, "17 18 * * *")
    spec_path = tmp_path / "agents/sample/agent.yaml"
    spec_path.write_text(spec_path.read_text(encoding="utf-8").replace(
        "        delivery: local", "        delivery: local\n        enabled: maybe"), encoding="utf-8")
    try:
        load_spec(spec_path)
    except SpecError:
        return
    raise AssertionError("a non-boolean `enabled` must be rejected")


def test_jobs_are_enabled_by_default(tmp_path):
    from pap.spec import load_spec

    make_platform(tmp_path, "17 18 * * *")
    spec = load_spec(tmp_path / "agents/sample/agent.yaml")
    assert spec.jobs[0].enabled is True


def test_the_historian_jobs_are_all_scheduled():
    """The owner chose to run the whole rollout at once rather than staged.

    §40 allows staging through the `enabled` flag; this pins the decision that was
    actually taken, so a future change to it is deliberate.
    """
    from pap.spec import load_spec

    spec = load_spec(Path(__file__).parents[1] / "agents/personal-historian/agent.yaml")
    states = {job.name: job.enabled for job in spec.jobs}
    assert {name for name, enabled in states.items() if enabled} == {
        "historian-event-card-refresh", "historian-thread-weekly-update",
        "historian-weekly-summary", "historian-monthly-summary",
        "historian-quarterly-summary", "historian-halfyear-summary",
        "historian-weekly-literary-render",
    }
    assert states["historian-weekly-literary-render"] is True
