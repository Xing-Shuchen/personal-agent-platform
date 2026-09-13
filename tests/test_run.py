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
    # Hermetic: point discovery at empty state so this test does not depend on
    # whatever the developer happens to have collected locally.  Readiness is
    # unmet because there is no state to read, not because the default path is
    # wrong.
    monkeypatch.setenv("PERSONAL_HISTORIAN_COLLECTION_ROOT", str(tmp_path / "no-collections"))
    monkeypatch.setenv("PERSONAL_HISTORIAN_REVISIONS", str(tmp_path / "no-revisions"))

    def model_must_not_run(*args, **kwargs):
        raise AssertionError("model must not run before readiness is met")

    result = invoke(
        root=root, spec=spec, skill="historian-period-summary",
        args={"kind": "week", "period": "previous"}, runtime="historian",
        run_log=tmp_path / "runs.jsonl", command_runner=model_must_not_run,
    )
    assert result.status == "not_ready"
    assert result.response == "NOT_READY"


def test_run_record_names_the_job_period_and_model(tmp_path):
    """§31: execution metadata PAP owns must reach the run record."""
    root = Path(__file__).parents[1]
    spec = load_spec(root / "agents/personal-historian/agent.yaml")
    run_log = tmp_path / "runs.jsonl"

    def fake_runner(command, **kwargs):
        raise OSError("OpenClaw unavailable")

    invoke(root=root, spec=spec, skill="historian-period-summary",
           args={"kind": "week", "period": "2026-W37", "timezone": "Asia/Shanghai"},
           trigger={"type": "manual-job", "job_id": "historian-weekly-summary"},
           run_log=run_log, command_runner=fake_runner, runtime=None)

    record = runs(run_log)[0]
    assert record["job_id"] == "historian-weekly-summary"
    assert record["period"] == "2026-W37"
    assert record["model"] == "deepseek/deepseek-flash"
    assert record["provider"] == "deepseek"
    # Token counts and cost are not synthesised: PAP cannot observe them.
    assert record["usage"] == {}


# --- §31: model usage the runner reports ----------------------------------------

def _usage_root(tmp_path):
    """A historian-shaped spec, without needing the real agent's runtime."""

    agent = tmp_path / "agents" / "sample"
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
    return load_spec(manifest)


REPORTED = {
    "session_key": "agent:sample:pap-run_x",
    "input_tokens": 106795,
    "output_tokens": 28800,
    "cost": 0.085265796,
    "source": "openclaw.sessions+openclaw.trajectory",
}


def test_reported_usage_reaches_the_run_record(tmp_path):
    """§31's fields are recorded under their own names, not buried in a blob."""

    spec = _usage_root(tmp_path)
    log = tmp_path / "runs.jsonl"

    invoke(
        root=tmp_path, spec=spec, skill="sample-skill", run_log=log,
        command_runner=lambda command, **kw: subprocess.CompletedProcess(command, 0, "ok", ""),
        usage_probe=lambda agent_id, run_id: dict(REPORTED),
    )
    record = runs(log)[0]
    assert record["input_tokens"] == 106795
    assert record["output_tokens"] == 28800
    assert record["cost"] == 0.085265796
    assert record["usage"]["model"]["source"] == "openclaw.sessions+openclaw.trajectory"


def test_unreadable_usage_is_recorded_as_absent_not_as_zero(tmp_path):
    spec = _usage_root(tmp_path)
    log = tmp_path / "runs.jsonl"

    invoke(
        root=tmp_path, spec=spec, skill="sample-skill", run_log=log,
        command_runner=lambda command, **kw: subprocess.CompletedProcess(command, 0, "ok", ""),
        usage_probe=lambda agent_id, run_id: None,
    )
    record = runs(log)[0]
    assert record["input_tokens"] is None
    assert record["output_tokens"] is None
    assert record["cost"] is None
    assert "model" not in record["usage"]


def test_a_failed_model_turn_still_reports_what_it_spent(tmp_path):
    """A run that failed after calling the model still cost money."""

    spec = _usage_root(tmp_path)
    log = tmp_path / "runs.jsonl"

    result = invoke(
        root=tmp_path, spec=spec, skill="sample-skill", run_log=log,
        command_runner=lambda command, **kw: subprocess.CompletedProcess(command, 1, "", "rate limit"),
        usage_probe=lambda agent_id, run_id: dict(REPORTED),
    )
    assert result.status == "failed"
    assert runs(log)[0]["output_tokens"] == 28800


def test_no_usage_is_read_when_no_model_turn_was_attempted(tmp_path):
    """A run that never reached the model has no usage, and is not probed."""

    spec = _usage_root(tmp_path)
    probed = []

    def missing(command, **kwargs):
        raise FileNotFoundError("openclaw not found")

    invoke(
        root=tmp_path, spec=spec, skill="sample-skill", run_log=tmp_path / "runs.jsonl",
        command_runner=missing,
        usage_probe=lambda agent_id, run_id: probed.append(run_id),
    )
    assert probed == []


def test_a_substituted_runner_does_not_reach_for_a_real_openclaw(tmp_path):
    """Tests replace the runner; usage must not be read behind the stub's back."""

    spec = _usage_root(tmp_path)
    commands = []

    def only_the_turn(command, **kwargs):
        commands.append(command)
        return subprocess.CompletedProcess(command, 0, "ok", "")

    invoke(root=tmp_path, spec=spec, skill="sample-skill",
           run_log=tmp_path / "runs.jsonl", command_runner=only_the_turn)
    assert [command[1] for command in commands] == ["agent"]


# --- §41: usage is visible without opening the JSON -----------------------------

def test_the_run_list_shows_usage_and_admits_when_it_is_unknown():
    from pap.cli import _usage_column

    assert _usage_column({"input_tokens": 106795, "output_tokens": 28800, "cost": 0.085}) == \
        "tokens=106795/28800 cost=0.085"
    assert _usage_column({"input_tokens": 10, "output_tokens": 2}) == "tokens=10/2 cost=?"
    assert _usage_column({}) == "tokens=? cost=?"


# --- §34: retry classification -------------------------------------------------

def test_only_transient_trouble_is_retryable():
    from pap.run import is_retryable
    # §34 names provider timeout, transient network failure, rate limit and
    # temporary model failure as retryable.
    assert is_retryable("timeout")
    assert is_retryable("runner")
    # ...and says not to blindly retry rejected output.
    for kind in ("validation", "model_output", "commit", "runtime", "launch", ""):
        assert not is_retryable(kind), kind


def test_a_runner_failure_is_recorded_as_retryable(tmp_path):
    root = Path(__file__).parents[1]
    spec = load_spec(root / "agents/personal-historian/agent.yaml")

    def failing_runner(command, **kwargs):
        return subprocess.CompletedProcess(command, 1, "", "rate limit exceeded")

    result = invoke(root=root, spec=spec, skill="historian-period-summary",
                    args={"kind": "week", "period": "2026-W37"}, run_log=tmp_path / "runs.jsonl",
                    command_runner=failing_runner, runtime=None)
    assert result.status == "failed"
    assert result.failure_kind == "runner"
    assert runs(tmp_path / "runs.jsonl")[0]["retryable"] is True


def test_a_timeout_is_recorded_as_retryable(tmp_path):
    root = Path(__file__).parents[1]
    spec = load_spec(root / "agents/personal-historian/agent.yaml")

    def timing_out(command, **kwargs):
        raise subprocess.TimeoutExpired(command, 1)

    result = invoke(root=root, spec=spec, skill="historian-period-summary",
                    args={"kind": "week", "period": "2026-W37"}, run_log=tmp_path / "runs.jsonl",
                    command_runner=timing_out, runtime=None)
    assert result.failure_kind == "timeout"
    assert runs(tmp_path / "runs.jsonl")[0]["retryable"] is True


def test_a_missing_runner_is_not_retryable(tmp_path):
    root = Path(__file__).parents[1]
    spec = load_spec(root / "agents/personal-historian/agent.yaml")

    def missing(command, **kwargs):
        raise FileNotFoundError("openclaw not found")

    result = invoke(root=root, spec=spec, skill="historian-period-summary",
                    args={"kind": "week", "period": "2026-W37"}, run_log=tmp_path / "runs.jsonl",
                    command_runner=missing, runtime=None)
    assert result.failure_kind == "launch"
    # Retrying cannot install a missing binary.
    assert runs(tmp_path / "runs.jsonl")[0]["retryable"] is False
