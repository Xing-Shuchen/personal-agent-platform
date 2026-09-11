"""Tests for scheduler slot reservation and delivery silence."""

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


def test_failed_slot_is_retried_after_delay(tmp_path, monkeypatch):
    make_platform(tmp_path, "17 18 * * *")
    now = datetime(2026, 8, 31, 18, 17, tzinfo=CST)
    monkeypatch.setattr("pap.scheduler._now", lambda: now)
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
