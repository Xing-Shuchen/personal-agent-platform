"""Tests for scheduler slot reservation and delivery silence."""

import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

from pap.scheduler import tick

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
        return subprocess.CompletedProcess(command, 0, stdout="[SILENT]", stderr="")

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

    # strict contract: the whole response is exactly a marker
    assert _intentional_silence("[SILENT]")
    assert _intentional_silence("SILENT")
    assert _intentional_silence("NO REPLY")
    assert _intentional_silence("NO_REPLY")
    assert _intentional_silence("  [SILENT]  ")

    # drift shapes that previously leaked to delivery (news-follow 2026-09-01):
    # marker as its own last line after a work summary
    assert _intentional_silence("工作集核对完毕：无到期线程。\n[SILENT]")
    assert _intentional_silence("2 deals filtered\n\n[SILENT]")
    # marker as its own first line
    assert _intentional_silence("[SILENT]\n无值得中断的变化")
    # bracketed marker as same-line prefix
    assert _intentional_silence("[SILENT] 无值得中断的变化")

    # a token buried mid-sentence is a genuine report and must deliver
    assert not _intentional_silence("我考虑过保持 [SILENT] 但这里有重要新闻")
    assert not _intentional_silence("silent retry succeeded")
    assert not _intentional_silence("正文最后一句提到 silent 字样")
    assert not _intentional_silence("")
    assert not _intentional_silence("   ")
