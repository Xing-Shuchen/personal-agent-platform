"""Tests for scheduler slot reservation and delivery silence."""

import json
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
import pytest

from pap.run import RunResult
from pap.scheduler import GATEWAY_RETRY_MAX_ATTEMPTS, _deliver, tick
from paplog import observe

CST = timezone(timedelta(hours=8))


@pytest.fixture(autouse=True)
def configured_test_delivery(monkeypatch):
    monkeypatch.setenv("PAP_OPENCLAW_CHANNEL", "test-channel")
    monkeypatch.setenv("PAP_OPENCLAW_ACCOUNT", "test-account")


def test_delivery_requires_local_route(monkeypatch):
    from pap.scheduler import _send_message

    monkeypatch.delenv("PAP_OPENCLAW_CHANNEL")
    monkeypatch.delenv("PAP_OPENCLAW_ACCOUNT")
    assert _send_message("hello", run_id="run_test", target="recipient",
                         sender=lambda *args, **kwargs: pytest.fail("unexpected send")) == "unconfigured"


def make_platform(
    root: Path, schedule: str = "* * * * *", *, delivery: str = "local",
    deliver_at: str | None = None, timezone_name: str | None = None,
    notify: dict[str, str] | None = None,
) -> None:
    skill = root / "agents/sample/profile/skills/sample-skill"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text(
        "---\nname: sample-skill\ndescription: Test.\n---\n# Test\n", encoding="utf-8"
    )
    notify_yaml = "".join(
        f"        notify:\n" + "".join(f"          {key}: {value}\n" for key, value in notify.items())
        if notify else ""
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
        delivery: {delivery}
""" + (f"        deliver_at: {deliver_at}\n" if deliver_at else "") + (
            f"        timezone: {timezone_name}\n" if timezone_name else ""
        ) + notify_yaml,
        encoding="utf-8",
    )


def test_not_ready_notify_is_deduped_and_reason_sensitive(tmp_path, monkeypatch):
    make_platform(tmp_path, notify={"channel": "feishu", "account": "diary", "target": "ou_test"})
    monkeypatch.setattr("pap.scheduler.JITTER_MAX_MINUTES", 0)
    now = datetime(2026, 8, 31, 18, 17, tzinfo=CST)
    sent = []

    def sender(command, **kwargs):
        sent.append(command)
        return subprocess.CompletedProcess(command, 0, "", "")

    reasons = iter(["week diaries missing: 2026-08-30", "week diaries missing: 2026-08-30", "week diaries missing: 2026-08-31"])
    monkeypatch.setattr("pap.scheduler.invoke", lambda **kwargs: RunResult(
        run_id="run_" + str(len(sent)), agent_id="sample", skill="sample-skill", status="not_ready",
        returncode=0, response="NOT_READY", error=next(reasons), started_at="", completed_at="", usage={},
    ))
    first = tick(tmp_path, now=now, sender=sender)
    second = tick(tmp_path, now=now + timedelta(minutes=1), sender=sender)
    third = tick(tmp_path, now=now + timedelta(minutes=2), sender=sender)
    assert [item.delivery for item in (first[0], second[0], third[0])] == ["notified", "notified", "notified"]
    assert len(sent) == 2
    assert "2026-08-31" in sent[-1][-1]


def test_success_failed_and_jobs_without_notify_do_not_notify(tmp_path, monkeypatch):
    make_platform(tmp_path)
    monkeypatch.setattr("pap.scheduler.JITTER_MAX_MINUTES", 0)
    now = datetime(2026, 8, 31, 18, 17, tzinfo=CST)

    def sender(*args, **kwargs):
        raise AssertionError("no notification expected")

    assert tick(tmp_path, now=now, command_runner=lambda argv, **kw: subprocess.CompletedProcess(argv, 0, "NOT_READY", "blocked"), sender=sender)[0].delivery == "not-attempted"
    assert tick(tmp_path, now=now + timedelta(minutes=1), command_runner=lambda argv, **kw: subprocess.CompletedProcess(argv, 0, "ok", ""), sender=sender)[0].delivery == "local"
    assert tick(tmp_path, now=now + timedelta(minutes=2), command_runner=lambda argv, **kw: subprocess.CompletedProcess(argv, 1, "", "failed"), sender=sender)[0].delivery == "not-attempted"


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


def test_scheduled_lifecycle_uses_one_canonical_job_id(tmp_path):
    make_platform(tmp_path)
    observe.configure(tmp_path / "ledger")
    now = datetime(2026, 8, 31, 18, 17, tzinfo=CST)
    tick(tmp_path, now=now, command_runner=lambda argv, **_: subprocess.CompletedProcess(argv, 0, "NO_REPLY", ""))
    lifecycle = observe.get_ledger().query(event="pap.*")
    names = {"pap.schedule.due", "pap.schedule.dispatched", "pap.run.started", "pap.run.completed"}
    matching = [item for item in lifecycle if item["event_name"] in names]
    assert {item["job"]["id"] for item in matching} == {"sample/sample-job"}


def test_tick_command_job_does_not_invoke_a_model_runner(tmp_path):
    make_platform(tmp_path)
    manifest = tmp_path / "agents/sample/agent.yaml"
    manifest.write_text(manifest.read_text(encoding="utf-8").replace(
        "        delivery: local", "        delivery: local\n        runner: command\n        command: [tool, update]"
    ), encoding="utf-8")
    now = datetime(2026, 8, 31, 18, 17, tzinfo=CST)
    calls = []
    result = tick(tmp_path, now=now, command_runner=lambda argv, **kw: (calls.append(argv) or subprocess.CompletedProcess(argv, 0, "NO_REPLY", "")))
    assert result[0].run.status == "success"
    assert calls == [["tool", "update"]]


def test_dry_run_does_not_create_scheduler_state(tmp_path):
    make_platform(tmp_path)
    now = datetime(2026, 8, 31, 18, 17, tzinfo=CST)
    result = tick(tmp_path, now=now, dry_run=True)
    assert len(result) == 1
    assert result[0].delivery == "dry-run"
    assert not (tmp_path / "var/state/scheduler-state.json").exists()


def test_deferred_delivery_queues_then_sends_once_at_the_clock(tmp_path, monkeypatch):
    make_platform(
        tmp_path, "0 7 * * *", delivery="user-home", deliver_at="08:00",
        timezone_name="Asia/Shanghai",
    )
    monkeypatch.setattr("pap.scheduler.JITTER_MAX_MINUTES", 0)
    before = datetime(2026, 8, 31, 7, 0, tzinfo=CST)
    monkeypatch.setattr("pap.run._now", lambda: before)
    sent = []

    def runner(command, **kwargs):
        return subprocess.CompletedProcess(command, 0, stdout="morning brief", stderr="")

    def sender(command, **kwargs):
        sent.append(command)
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    first = tick(tmp_path, now=before, command_runner=runner,
                 delivery_target="ou_test", sender=sender)
    queue_path = tmp_path / "var/state/delivery-queue.json"
    assert first[0].delivery == "deferred"
    assert sent == []
    assert json.loads(queue_path.read_text(encoding="utf-8"))["entries"][0]["response"] == "morning brief"

    second = tick(tmp_path, now=before.replace(hour=8), command_runner=runner,
                  delivery_target="ou_test", sender=sender)
    assert second == []
    assert len(sent) == 1
    assert json.loads(queue_path.read_text(encoding="utf-8"))["entries"] == []

    third = tick(tmp_path, now=before.replace(hour=8, minute=1), command_runner=runner,
                 delivery_target="ou_test", sender=sender)
    assert third == []
    assert len(sent) == 1


def test_delivery_at_or_after_clock_delivers_immediately(tmp_path, monkeypatch):
    make_platform(
        tmp_path, "0 8 * * *", delivery="user-home", deliver_at="08:00",
        timezone_name="Asia/Shanghai",
    )
    monkeypatch.setattr("pap.scheduler.JITTER_MAX_MINUTES", 0)
    at_clock = datetime(2026, 8, 31, 8, 0, tzinfo=CST)
    monkeypatch.setattr("pap.run._now", lambda: at_clock)
    sent = []

    def sender(command, **kwargs):
        sent.append(command)
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    result = tick(
        tmp_path, now=at_clock,
        command_runner=lambda command, **kwargs: subprocess.CompletedProcess(command, 0, "on time", ""),
        delivery_target="ou_test", sender=sender,
    )
    assert result[0].delivery == "sent"
    assert len(sent) == 1
    assert not (tmp_path / "var/state/delivery-queue.json").exists()


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


@pytest.mark.parametrize("message", [
    "gateway.auth.token is configured as a secret reference but is unavailable",
    "Lost the connection to OpenClaw",
    "Gateway agent call connection closed; the Gateway may still be running this turn",
    "connect ECONNREFUSED 127.0.0.1",
    "socket hang up",
])
def test_gateway_unavailable_markers(message):
    from pap.scheduler import gateway_unavailable

    assert gateway_unavailable(None, "", message)
    assert gateway_unavailable(message.upper())
    assert not gateway_unavailable(None, "", "ordinary runner failure")
    assert not gateway_unavailable()


@pytest.mark.parametrize("returncode,error,expected_class", [
    (1, "Gateway agent call connection closed", "gateway_unavailable"),
    (1, "ordinary runner failure", ""),
    (0, "Gateway agent call connection closed", ""),
])
def test_settled_run_updates_gateway_failure_class(tmp_path, monkeypatch, returncode, error, expected_class):
    make_platform(tmp_path, "17 18 * * *")
    monkeypatch.setattr("pap.scheduler.JITTER_MAX_MINUTES", 0)
    now = datetime(2026, 8, 31, 18, 17, tzinfo=CST)
    state_path = tmp_path / "state.json"
    state_path.write_text(json.dumps({"jobs": {"sample/sample-job": {
        "last_failure_class": "gateway_unavailable",
    }}}), encoding="utf-8")

    result = tick(tmp_path, now=now, state_path=state_path, command_runner=lambda command, **kwargs:
                  subprocess.CompletedProcess(command, returncode, "NO_REPLY", error))

    assert result[0].run.status == ("failed" if returncode else "success")
    entry = json.loads(state_path.read_text(encoding="utf-8"))["jobs"]["sample/sample-job"]
    assert entry["last_failure_class"] == expected_class


def test_opencode_provider_rejection_is_not_retried(tmp_path, monkeypatch):
    make_platform(tmp_path, "17 18 * * *")
    manifest = tmp_path / "agents/sample/agent.yaml"
    manifest.write_text(manifest.read_text(encoding="utf-8").replace(
        "        delivery: local", "        delivery: local\n        runner: opencode\n        model: opencode/muse-spark-1.2-contributor-free"
    ), encoding="utf-8")
    now = datetime(2026, 8, 31, 18, 17, tzinfo=CST)
    monkeypatch.setattr("pap.scheduler._now", lambda: now)
    monkeypatch.setattr("pap.scheduler.JITTER_MAX_MINUTES", 0)
    calls = []

    def region_blocked(command, **kwargs):
        calls.append(command)
        return subprocess.CompletedProcess(
            command, 1,
            '{"type":"error","error":{"data":{"responseBody":"RegionError"}}}', "",
        )

    first = tick(tmp_path, now=now, command_runner=region_blocked)
    retry = tick(tmp_path, now=now + timedelta(minutes=6), command_runner=region_blocked)
    assert first[0].run.failure_kind == "provider_rejection"
    assert retry == []
    assert len(calls) == 1


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
    monkeypatch.setenv("PAP_OPENCLAW_ACCOUNT", "account_test")
    monkeypatch.setenv("PAP_OPENCLAW_BIN", "/usr/local/bin/openclaw")
    assert _deliver(result, job, target="ou_test", sender=sender) == "sent"
    assert calls == [(
        ["/usr/local/bin/openclaw", "message", "send", "--channel", "feishu",
         "--account", "account_test", "--target", "ou_test", "--message", "hello"],
        {"capture_output": True, "text": True, "timeout": 60},
    )]


def test_delivery_suppresses_leaked_tool_echo():
    result = RunResult(
        run_id="run_test", agent_id="sample", skill="sample-skill", status="success",
        returncode=0,
        response=(
            "Let me verify one candidate delta before deciding on delivery "
            "(whether Buckmaster's call for an independent investigation is already in the record).\n"
            'db = sqlite3.connect("file:/example/personal-agent-platform/'
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

    assert _deliver(result, job, target="ou_test", sender=sender) == "silent"


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


@pytest.mark.parametrize("failure_class,attempts,retryable,minutes_since_finished,expect_due", [
    ("gateway_unavailable", 5, True, 6, True),
    ("gateway_unavailable", GATEWAY_RETRY_MAX_ATTEMPTS, True, 6, False),
    ("", 3, True, 6, False),
    ("gateway_unavailable", 5, False, 6, False),
    ("gateway_unavailable", 5, True, 4, False),
])
def test_failed_slot_retry_budget(tmp_path, monkeypatch, failure_class, attempts, retryable,
                                  minutes_since_finished, expect_due):
    from pap.scheduler import due_jobs

    make_platform(tmp_path, "17 18 * * *")
    monkeypatch.setattr("pap.scheduler.JITTER_MAX_MINUTES", 0)
    slot = datetime(2026, 8, 31, 18, 17, tzinfo=CST)
    now = slot + timedelta(minutes=40)
    state_path = tmp_path / "state.json"
    entry = {
        "last_slot": slot.isoformat(timespec="minutes"),
        "last_status": "failed",
        "last_failure_kind": "runner",
        "last_retryable": retryable,
        "attempts": attempts,
        "last_finished_at": (now - timedelta(minutes=minutes_since_finished)).isoformat(timespec="seconds"),
    }
    if failure_class:
        entry["last_failure_class"] = failure_class
    state_path.write_text(json.dumps({"jobs": {"sample/sample-job": entry}}), encoding="utf-8")

    due = due_jobs(tmp_path, now=now, state_path=state_path, reserve=False)
    assert [item.slot for item in due] == ([slot] if expect_due else [])


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


def test_missing_required_environment_settles_slot_without_retry(tmp_path, monkeypatch):
    make_platform(tmp_path, schedule="15 3 * * *")
    manifest = tmp_path / "agents/sample/agent.yaml"
    manifest.write_text(manifest.read_text().replace('        delivery: local', '        requires_env: [WECHAT_DBROOT, WECHAT_KEYS]\n        delivery: local'))
    monkeypatch.setattr("pap.scheduler.JITTER_MAX_MINUTES", 0)
    for key in ("WECHAT_DBROOT", "WECHAT_KEYS"):
        monkeypatch.delenv(key, raising=False)
    def forbidden(*args, **kwargs):
        pytest.fail("skip must not invoke or deliver")
    now = datetime(2026, 10, 26, 3, 15, tzinfo=CST)
    first = tick(tmp_path, now=now, command_runner=forbidden)
    assert len(first) == 1
    assert first[0].run.status == "skipped"
    assert tick(tmp_path, now=now + timedelta(minutes=6), command_runner=forbidden) == []


@pytest.mark.parametrize("deferred", [False, True])
@pytest.mark.parametrize("override", [False, True])
def test_job_delivery_route(tmp_path, monkeypatch, deferred, override):
    make_platform(tmp_path, "0 7 * * *", delivery="user-home",
                  deliver_at="08:00" if deferred else None,
                  timezone_name="Asia/Shanghai")
    if override:
        manifest = tmp_path / "agents/sample/agent.yaml"
        manifest.write_text(manifest.read_text().replace(
            "        delivery: user-home",
            "        delivery: user-home\n        delivery_target: job-target\n"
            "        delivery_channel: job-channel\n        delivery_account: job-account"))
    monkeypatch.setenv("PAP_OPENCLAW_DELIVERY_TARGET", "global-target")
    monkeypatch.setattr("pap.scheduler.JITTER_MAX_MINUTES", 0)
    before = datetime(2026, 8, 31, 7, 0, tzinfo=CST)
    monkeypatch.setattr("pap.run._now", lambda: before)
    sent = []

    def sender(command, **kwargs):
        sent.append(command)
        return subprocess.CompletedProcess(command, 0, "", "")

    result = tick(tmp_path, now=before, sender=sender,
                  command_runner=lambda command, **kwargs: subprocess.CompletedProcess(
                      command, 0, "morning brief", ""))
    if deferred:
        assert result[0].delivery == "deferred"
        assert sent == []
        entry = json.loads((tmp_path / "var/state/delivery-queue.json").read_text())["entries"][0]
        assert entry["target"] == ("job-target" if override else "global-target")
        assert entry["channel"] == ("job-channel" if override else None)
        assert entry["account"] == ("job-account" if override else None)
        tick(tmp_path, now=before.replace(hour=8), sender=sender)
    else:
        assert result[0].delivery == "sent"
    assert len(sent) == 1
    for flag, expected in [("--target", "job-target" if override else "global-target"),
                           ("--channel", "job-channel" if override else "test-channel"),
                           ("--account", "job-account" if override else "test-account")]:
        assert sent[0][sent[0].index(flag) + 1] == expected


def test_legacy_deferred_delivery_uses_global_route(tmp_path):
    from pap.scheduler import _drain_deferred_deliveries

    queue = tmp_path / "queue.json"
    now = datetime(2026, 8, 31, 8, 0, tzinfo=CST)
    queue.write_text(json.dumps({"entries": [{
        "run_id": "legacy-run", "job_key": "sample/sample-job",
        "response": "legacy brief", "deliver_at": now.isoformat(),
    }]}))
    sent = []

    def sender(command, **kwargs):
        sent.append(command)
        return subprocess.CompletedProcess(command, 0, "", "")

    _drain_deferred_deliveries(queue, now=now, run_log=tmp_path / "runs.jsonl",
                               target="global-target", sender=sender)
    assert len(sent) == 1
    for flag, expected in [("--target", "global-target"),
                           ("--channel", "test-channel"), ("--account", "test-account")]:
        assert sent[0][sent[0].index(flag) + 1] == expected
    assert json.loads(queue.read_text())["entries"] == []
