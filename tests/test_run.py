"""Tests for OpenClaw invocation and append-only run records."""

import json
import subprocess
from pathlib import Path

from pap.run import _prompt, invoke, runs
from pap.spec import load_spec


def make_agent(root: Path) -> Path:
    agent = root / "agents" / "sample"
    skill = agent / "profile" / "skills" / "sample-skill"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text(
        "---\nname: sample-skill\ndescription: Test skill.\n---\n\n# Test\n",
        encoding="utf-8",
    )
    manifest = agent / "agent.yaml"
    manifest.write_text(
        """apiVersion: pap/v1
kind: Agent
metadata:
  name: sample
  description: Sample agent.
spec:
  profile:
    name: sample
    source: profile
  model: deepseek/deepseek-flash
""",
        encoding="utf-8",
    )
    return manifest


def test_invoke_records_start_and_completion(tmp_path):
    spec = load_spec(make_agent(tmp_path))
    log = tmp_path / "runs.jsonl"
    captured = {}

    def fake_runner(command, **kwargs):
        captured["command"] = command
        captured["cwd"] = kwargs["cwd"]
        captured["env"] = kwargs["env"]
        captured["input"] = kwargs["input"]
        message_file = Path(command[command.index("--message-file") + 1])
        captured["message_file"] = message_file
        captured["message"] = message_file.read_text(encoding="utf-8")
        return subprocess.CompletedProcess(command, 0, stdout="完成\n", stderr="")

    result = invoke(root=tmp_path, spec=spec, skill="sample-skill", input_text="seed",
                    args={"priority": "high"}, run_log=log, command_runner=fake_runner)
    assert result.status == "success"
    assert result.response == "完成"
    assert captured["cwd"] == tmp_path / "agents/sample/profile"
    assert captured["env"]["PAP_AGENT_STATE_DIR"] == str(tmp_path / "var/sample")
    assert captured["command"][:5] == ["openclaw", "agent", "--agent", "sample", "--session-key"]
    assert "--message-file" in captured["command"]
    assert str(captured["message_file"]) != "-"
    assert captured["message"] == _prompt(
        "sample-skill",
        (tmp_path / "agents/sample/profile/skills/sample-skill/SKILL.md").read_text(encoding="utf-8"),
        "seed",
        {"priority": "high"},
    )
    assert not captured["message_file"].exists()
    assert captured["command"][captured["command"].index("--model") + 1] == \
        "deepseek/deepseek-flash"
    assert captured["input"] is None
    lifecycle = [json.loads(line)["event"] for line in log.read_text().splitlines()]
    assert lifecycle == ["run.started", "run.completed"]
    merged = runs(log)
    assert merged[0]["run_id"] == result.run_id
    assert merged[0]["usage"] == {}


def test_invoke_removes_message_file_when_runner_fails(tmp_path):
    spec = load_spec(make_agent(tmp_path))
    captured = {}

    def fake_runner(command, **kwargs):
        captured["message_file"] = Path(command[command.index("--message-file") + 1])
        assert captured["message_file"].is_file()
        raise OSError("OpenClaw unavailable")

    result = invoke(root=tmp_path, spec=spec, skill="sample-skill",
                    run_log=tmp_path / "runs.jsonl", command_runner=fake_runner)

    assert result.status == "failed"
    assert not captured["message_file"].exists()


def test_declared_runtime_can_finish_not_ready_without_model_turn(tmp_path, monkeypatch):
    """Readiness is a normal terminal outcome, not a failed OpenClaw call."""
    root = Path(__file__).parents[1]
    spec = load_spec(root / "agents/personal-historian/agent.yaml")
    monkeypatch.delenv("PERSONAL_HISTORIAN_WATERMARKS_JSON", raising=False)

    def model_must_not_run(*args, **kwargs):
        raise AssertionError("model must not run before readiness is met")

    result = invoke(
        root=root, spec=spec, skill="historian-period-summary",
        args={"kind": "week", "period": "previous"}, runtime="historian",
        run_log=tmp_path / "runs.jsonl", command_runner=model_must_not_run,
    )
    assert result.status == "not_ready"
    assert result.response == "NOT_READY"
