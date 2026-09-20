"""Tests for OpenClaw invocation and append-only run records."""

import json
import signal
import subprocess
from pathlib import Path

from pap.run import OPENCLAW_EMPTY_FINALIZATION_FALLBACK, _opencode_output, _prompt, invoke, is_retryable, new_run_id, runs
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
    assert captured["env"]["PAP_AGENT_DEFINITION_VERSION"].startswith("sha256:")
    assert captured["env"]["PAP_RUN_ID"] == result.run_id
    assert captured["env"]["PAP_PARENT_OPERATION_ID"] != result.run_id
    assert len(captured["env"]["PAP_PARENT_OPERATION_ID"]) == 26
    assert captured["env"]["PAP_NODE_ID"]
    assert captured["env"]["TRACEPARENT"].startswith("00-")
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


def test_new_run_id_is_a_sortable_ulid():
    earlier = new_run_id(__import__("datetime").datetime.fromisoformat("2026-01-01T00:00:00+00:00"))
    later = new_run_id(__import__("datetime").datetime.fromisoformat("2026-01-01T00:00:01+00:00"))
    assert len(earlier) == len(later) == 26
    assert earlier < later


def test_invoke_job_model_overrides_agent_model(tmp_path):
    spec = load_spec(make_agent(tmp_path))
    captured = {}

    def fake_runner(command, **kwargs):
        captured["command"] = command
        captured["env"] = kwargs["env"]
        return subprocess.CompletedProcess(command, 0, stdout="done\n", stderr="")

    log = tmp_path / "runs.jsonl"
    invoke(root=tmp_path, spec=spec, skill="sample-skill", run_log=log,
           command_runner=fake_runner, model="deepseek/deepseek-v4-pro")
    assert captured["command"][captured["command"].index("--model") + 1] == \
        "deepseek/deepseek-v4-pro"
    assert captured["env"]["PAP_AGENT_MODEL"] == "deepseek/deepseek-v4-pro"
    record = runs(log)[0]
    assert record["model"] == "deepseek/deepseek-v4-pro"
    assert record["provider"] == "deepseek"


def test_opencode_invocation_uses_stdin_json_and_runner_usage(tmp_path, monkeypatch):
    spec = load_spec(make_agent(tmp_path))
    log = tmp_path / "runs.jsonl"
    seen = {}
    monkeypatch.setenv("PAP_OPENCODE_BIN", "/opt/opencode")

    def fake_runner(command, **kwargs):
        seen.update(command=command, cwd=kwargs["cwd"], input=kwargs["input"])
        stdout = "\n".join((
            '{"type":"text","part":{"text":"first "}}',
            '{"type":"text","part":{"text":"second"}}',
            '{"type":"step_finish","part":{"tokens":{"input":12,"output":3},"cost":0}}',
            '{"type":"step_finish","part":{"tokens":{"input":4,"output":2},"cost":0}}',
        ))
        return subprocess.CompletedProcess(command, 0, stdout, "")

    result = invoke(
        root=tmp_path, spec=spec, skill="sample-skill", run_log=log,
        trigger={"type": "manual-job", "job_id": "sample-job"},
        runner_backend="opencode", model="opencode/mimo-v2.5-free", command_runner=fake_runner,
    )
    assert result.response == "first second"
    assert seen["command"] == [
        "/opt/opencode", "run", "--pure", "--format", "json", "--title", "sample/sample-job",
        "--model", "opencode/mimo-v2.5-free",
    ]
    assert seen["cwd"] == tmp_path.resolve()
    assert "Run the 'sample-skill' skill exactly as written." in seen["input"]
    record = runs(log)[0]
    assert record["runner"] == "opencode"
    assert record["model"] == "opencode/mimo-v2.5-free"
    assert record["provider"] == "opencode"
    assert (record["input_tokens"], record["output_tokens"], record["cost"]) == (16, 5, 0)
    assert record["usage"]["model"]["source"] == "opencode.run"


def test_model_call_records_non_secret_route_profiles(tmp_path, monkeypatch):
    spec = load_spec(make_agent(tmp_path))
    from paplog import observe
    observe.configure(tmp_path / "ledger")
    monkeypatch.setenv("PAP_ROUTING_PROFILE", "low-cost")
    monkeypatch.setenv("PAP_CREDENTIAL_PROFILE", "shared-research")
    monkeypatch.setenv("PAP_WORKLOAD_CLASS", "scheduled-brief")
    invoke(root=tmp_path, spec=spec, skill="sample-skill", run_log=tmp_path / "runs.jsonl",
           runner_backend="opencode", model="opencode/test", command_runner=lambda command, **_: subprocess.CompletedProcess(
               command, 0, '{"type":"step_finish","part":{"tokens":{"input":2,"output":1},"cost":0}}', ""))
    event = observe.get_ledger().query(event="pap.model.call")[0]
    assert {key: event["attributes"][key] for key in ("routing_profile", "credential_profile", "workload_class")} == {
        "routing_profile": "low-cost", "credential_profile": "shared-research", "workload_class": "scheduled-brief"}


def test_openclaw_trajectory_tool_actions_are_linked_to_the_skill(tmp_path, monkeypatch):
    spec = load_spec(make_agent(tmp_path))
    from paplog import observe
    observe.configure(tmp_path / "ledger")
    monkeypatch.setattr("pap.run.trajectory_tools", lambda *_args: [{
        "tool_call_id": "call_1", "name": "web_search",
        "arguments": {"sha256": "sha256:args", "bytes": 5},
        "result": {"sha256": "sha256:result", "bytes": 7},
        "started_at": "2026-09-20T10:00:00+00:00",
        "completed_at": "2026-09-20T10:00:01+00:00", "duration_ms": 1000, "success": True,
    }])
    invoke(root=tmp_path, spec=spec, skill="sample-skill", run_log=tmp_path / "runs.jsonl",
           runner_backend="openclaw", usage_probe=lambda *_: {"input_tokens": 2, "output_tokens": 1},
           command_runner=lambda command, **_: subprocess.CompletedProcess(command, 0, "done", ""))

    events = observe.get_ledger().query(event="pap.tool.call")
    assert [event["phase"] for event in events] == ["started", "completed"]
    assert {event["execution"]["action_id"] for event in events}.__len__() == 1
    assert all(event["execution"]["operation_id"] for event in events)
    assert events[-1]["attributes"]["tool.result"] == {"sha256": "sha256:result", "bytes": 7}
    model = observe.get_ledger().query(event="pap.model.call")[0]
    assert model["kind"] == "action"
    assert model["phase"] == "completed"
    assert model["execution"]["action_id"]


def test_opencode_json_event_parser_accepts_cli_event_shape():
    response, usage = _opencode_output(
        '{"type":"text","part":{"text":"PICKLE"}}\n'
        '{"type":"text","part":{"text":"_OK"}}\n'
        '{"type":"step_finish","part":{"tokens":{"input":213,"output":6},"cost":0}}\n'
    )
    assert response == "PICKLE_OK"
    assert usage == {"input_tokens": 213, "output_tokens": 6, "cost": 0, "source": "opencode.run"}


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


def test_sigterm_is_preserved_as_a_distinct_run_failure(tmp_path):
    spec = load_spec(make_agent(tmp_path))
    from paplog import observe
    observe.configure(tmp_path / "ledger")
    result = invoke(root=tmp_path, spec=spec, skill="sample-skill", run_log=tmp_path / "runs.jsonl",
                    command_runner=lambda command, **_: subprocess.CompletedProcess(command, -signal.SIGTERM, "", ""))
    assert result.status == "failed"
    assert result.failure_kind == f"signal:{signal.SIGTERM}"
    process = observe.get_ledger().query(event="pap.process.exec")[-1]
    assert process["phase"] == "failed"
    assert process["attributes"]["exit_code"] == -signal.SIGTERM


def test_invoke_normalizes_openclaw_empty_finalization_to_no_reply(tmp_path):
    spec = load_spec(make_agent(tmp_path))
    log = tmp_path / "runs.jsonl"

    def fake_runner(command, **kwargs):
        return subprocess.CompletedProcess(command, 0, stdout=OPENCLAW_EMPTY_FINALIZATION_FALLBACK, stderr="")

    result = invoke(root=tmp_path, spec=spec, skill="sample-skill", run_log=log,
                    command_runner=fake_runner)

    assert result.status == "success"
    assert result.response == "NO_REPLY"
    record = runs(log)[0]
    assert record["response_normalization"] == "openclaw-empty-finalization"
    assert record["response"]["chars"] == len("NO_REPLY")
    assert record["raw_response"]["chars"] == len(OPENCLAW_EMPTY_FINALIZATION_FALLBACK)


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


def test_runtime_context_policy_identity_reaches_terminal_run_event(tmp_path, monkeypatch):
    spec = load_spec(make_agent(tmp_path))
    runtime_dir = tmp_path / "agents/sample/runtime"
    runtime_dir.mkdir()
    (runtime_dir / "test.py").write_text("# invoked through mocked adapter\n", encoding="utf-8")
    from paplog import observe
    observe.configure(tmp_path / "ledger")
    def fake_runtime(_path, action, _payload, _env):
        if action == "prepare":
            return {"status": "ready", "input_text": "", "metadata": {"context_pack_id": "context-pack:week:2026-W01", "policy_id": "week", "policy_version": "v1"}}
        return {"status": "success", "response": "NO_REPLY", "metadata": {}}
    monkeypatch.setattr("pap.run._runtime_call", fake_runtime)
    result = invoke(root=tmp_path, spec=spec, skill="sample-skill", runtime="test", run_log=tmp_path / "runs.jsonl",
                    command_runner=lambda command, **_: subprocess.CompletedProcess(command, 0, "NO_REPLY", ""))
    terminal = observe.get_ledger().query(run=result.run_id, event="pap.run.completed")[0]
    assert terminal["context"] == {"pack_refs": ["artifact:context-pack:week:2026-W01"], "policy_id": "week", "policy_version": "v1"}


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
    expected_model = spec.model
    expected_provider = (
        expected_model.split("/", 1)[0].strip()
        if isinstance(expected_model, str) and "/" in expected_model
        else None
    )
    assert record["job_id"] == "historian-weekly-summary"
    assert record["period"] == "2026-W37"
    assert record["model"] == expected_model
    assert record["provider"] == expected_provider
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


def test_command_runner_is_model_free_and_normalizes_silence(tmp_path):
    spec = load_spec(make_agent(tmp_path))
    log = tmp_path / "runs.jsonl"
    seen = {}

    def command_only(argv, **kwargs):
        seen.update(argv=argv, cwd=kwargs["cwd"], env=kwargs["env"])
        return subprocess.CompletedProcess(argv, 0, "NO_REPLY\n", "")

    result = invoke(
        root=tmp_path, spec=spec, skill="sample-skill", run_log=log,
        runner_backend="command", command=["deterministic-tool", "update"],
        command_runner=command_only,
    )
    record = runs(log)[0]
    assert result.status == "success"
    assert result.response == "NO_REPLY"
    assert seen["argv"] == ["deterministic-tool", "update"]
    assert seen["cwd"] == tmp_path.resolve()
    assert seen["env"]["PAP_ROOT"] == str(tmp_path.resolve())
    assert seen["env"]["PAP_AGENT_ID"] == "sample"
    assert "PAP_AGENT_MODEL" not in seen["env"]
    assert record["runner"] == "command"
    assert "model" not in record and "provider" not in record
    assert "model" not in record["usage"]
    assert record["input_tokens"] is None


def test_command_failure_is_not_retryable(tmp_path):
    spec = load_spec(make_agent(tmp_path))
    result = invoke(
        root=tmp_path, spec=spec, skill="sample-skill", run_log=tmp_path / "runs.jsonl",
        runner_backend="command", command=["tool"],
        command_runner=lambda argv, **kwargs: subprocess.CompletedProcess(argv, 3, "", "bad input"),
    )
    assert result.status == "failed"
    assert result.failure_kind == "command"
    assert runs(tmp_path / "runs.jsonl")[0]["retryable"] is False


def test_an_agent_on_the_configured_route_omits_the_model_override(tmp_path):
    """Pinning --model is a strict selection and would skip the fallback chain."""

    manifest = make_agent(tmp_path)
    manifest.write_text(
        manifest.read_text(encoding="utf-8") + "  model_fallback: true\n",
        encoding="utf-8",
    )
    spec = load_spec(manifest)
    assert spec.model_fallback is True
    captured = {}

    def fake_runner(command, **kwargs):
        captured["command"] = command
        return subprocess.CompletedProcess(command, 0, stdout="ok\n", stderr="")

    invoke(root=tmp_path, spec=spec, skill="sample-skill", run_log=tmp_path / "runs.jsonl",
           command_runner=fake_runner)
    assert "--model" not in captured["command"]
    record = runs(tmp_path / "runs.jsonl")[0]
    # The run still records the model the spec asked for.
    assert record["model"] == "deepseek/deepseek-flash"


def test_a_job_model_pins_an_agent_with_a_fallback_route(tmp_path):
    """An explicit job selection takes precedence over the route's fallback chain."""

    manifest = make_agent(tmp_path)
    manifest.write_text(
        manifest.read_text(encoding="utf-8") + "  model_fallback: true\n",
        encoding="utf-8",
    )
    spec = load_spec(manifest)
    captured = {}

    def fake_runner(command, **kwargs):
        captured["command"] = command
        return subprocess.CompletedProcess(command, 0, stdout="ok\n", stderr="")

    invoke(root=tmp_path, spec=spec, skill="sample-skill", run_log=tmp_path / "runs.jsonl",
           command_runner=fake_runner, model="zai/glm-5.2")
    assert captured["command"][-2:] == ["--model", "zai/glm-5.2"]


def test_a_pinned_agent_still_receives_its_model(tmp_path):
    spec = load_spec(make_agent(tmp_path))
    assert spec.model_fallback is False
    captured = {}

    def fake_runner(command, **kwargs):
        captured["command"] = command
        return subprocess.CompletedProcess(command, 0, stdout="ok\n", stderr="")

    invoke(root=tmp_path, spec=spec, skill="sample-skill", run_log=tmp_path / "runs.jsonl",
           command_runner=fake_runner)
    assert captured["command"][-2:] == ["--model", "deepseek/deepseek-flash"]


def test_a_provider_refusal_is_recorded_as_non_retryable(tmp_path):
    """§34: the same text fails the same way, so a refusal is never blind-retried."""

    spec = load_spec(make_agent(tmp_path))
    log = tmp_path / "runs.jsonl"
    result = invoke(
        root=tmp_path, spec=spec, skill="sample-skill", run_log=log,
        command_runner=lambda command, **kw: subprocess.CompletedProcess(
            command, 1, stdout="\u26a0\ufe0f call failed.", stderr=""
        ),
        failure_probe=lambda agent_id, run_id: "Output data may contain inappropriate content.",
    )
    assert result.status == "failed"
    assert result.failure_kind == "provider_rejection"
    assert is_retryable(result.failure_kind) is False
    record = runs(log)[0]
    assert record["error"] == "Output data may contain inappropriate content."
    assert record["retryable"] is False


def test_provider_rejection_uses_declared_fallback_once_and_records_provenance(tmp_path):
    manifest = make_agent(tmp_path)
    manifest.write_text(
        manifest.read_text(encoding="utf-8").replace(
            "deepseek/deepseek-flash", "qwen/deepseek-v4.1-flash"
        )
        + "  provider_rejection_fallback: deepseek/deepseek-flash\n",
        encoding="utf-8",
    )
    spec = load_spec(manifest)
    log = tmp_path / "runs.jsonl"
    commands = []

    def fake_runner(command, **kwargs):
        commands.append(command)
        if len(commands) == 1:
            return subprocess.CompletedProcess(command, 1, "refused", "")
        return subprocess.CompletedProcess(command, 0, "fallback reply\n", "")

    result = invoke(
        root=tmp_path, spec=spec, skill="sample-skill", run_log=log,
        command_runner=fake_runner,
        failure_probe=lambda agent_id, run_id: "Output data may contain inappropriate content.",
    )
    assert result.status == "success"
    assert result.response == "fallback reply"
    assert len(commands) == 2
    assert commands[1][-2:] == ["--model", "deepseek/deepseek-flash"]
    events = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()]
    assert [event["event"] for event in events] == ["run.started", "run.fallback", "run.completed"]
    assert events[1]["from"] == "qwen/deepseek-v4.1-flash"
    assert events[1]["to"] == "deepseek/deepseek-flash"
    record = runs(log)[0]
    assert record["model"] == "deepseek/deepseek-flash"
    assert record["provider"] == "deepseek"
    assert record["fallback_from"] == "qwen/deepseek-v4.1-flash"


def test_provider_rejection_without_declared_fallback_is_single_attempt(tmp_path):
    spec = load_spec(make_agent(tmp_path))
    calls = []

    def fake_runner(command, **kwargs):
        calls.append(command)
        return subprocess.CompletedProcess(command, 1, "", "")

    result = invoke(
        root=tmp_path, spec=spec, skill="sample-skill", run_log=tmp_path / "runs.jsonl",
        command_runner=fake_runner,
        failure_probe=lambda agent_id, run_id: "Output data may contain inappropriate content.",
    )
    assert result.failure_kind == "provider_rejection"
    assert len(calls) == 1


def test_declared_fallback_does_not_run_for_ordinary_runner_failure(tmp_path):
    manifest = make_agent(tmp_path)
    manifest.write_text(
        manifest.read_text(encoding="utf-8").replace(
            "deepseek/deepseek-flash", "qwen/deepseek-v4.1-flash"
        )
        + "  provider_rejection_fallback: deepseek/deepseek-flash\n",
        encoding="utf-8",
    )
    calls = []
    result = invoke(
        root=tmp_path, spec=load_spec(manifest), skill="sample-skill",
        run_log=tmp_path / "runs.jsonl",
        command_runner=lambda command, **kwargs: calls.append(command) or subprocess.CompletedProcess(command, 1, "", "network trouble"),
    )
    assert result.failure_kind == "runner"
    assert len(calls) == 1


def test_failed_provider_rejection_fallback_records_final_failure(tmp_path):
    manifest = make_agent(tmp_path)
    manifest.write_text(
        manifest.read_text(encoding="utf-8").replace(
            "deepseek/deepseek-flash", "qwen/deepseek-v4.1-flash"
        )
        + "  provider_rejection_fallback: deepseek/deepseek-flash\n",
        encoding="utf-8",
    )
    calls = []

    def fake_runner(command, **kwargs):
        calls.append(command)
        return subprocess.CompletedProcess(command, 1, "", "fallback transport failure")

    result = invoke(
        root=tmp_path, spec=load_spec(manifest), skill="sample-skill", run_log=tmp_path / "runs.jsonl",
        command_runner=fake_runner,
        failure_probe=lambda agent_id, run_id: "Output data may contain inappropriate content." if len(calls) == 1 else None,
    )
    assert result.status == "failed"
    assert result.failure_kind == "runner"
    assert len(calls) == 2
    record = runs(tmp_path / "runs.jsonl")[0]
    assert record["model"] == "deepseek/deepseek-flash"
    assert record["fallback_from"] == "qwen/deepseek-v4.1-flash"
    assert record["retryable"] is True


def test_an_openclaw_failure_without_a_recorded_reason_keeps_an_empty_error(tmp_path):
    spec = load_spec(make_agent(tmp_path))
    log = tmp_path / "runs.jsonl"
    result = invoke(
        root=tmp_path, spec=spec, skill="sample-skill", run_log=log,
        command_runner=lambda command, **kw: subprocess.CompletedProcess(
            command, 1, stdout="", stderr=""
        ),
        failure_probe=lambda agent_id, run_id: None,
    )
    assert result.error == ""
    assert result.failure_kind == "runner"
    assert runs(log)[0]["error"] == ""


def test_transport_trouble_stays_retryable(tmp_path):
    spec = load_spec(make_agent(tmp_path))
    log = tmp_path / "runs.jsonl"
    result = invoke(
        root=tmp_path, spec=spec, skill="sample-skill", run_log=log,
        command_runner=lambda command, **kw: subprocess.CompletedProcess(
            command, 1, stdout="", stderr="Connection error."
        ),
        failure_probe=lambda agent_id, run_id: "LLM request timed out.",
    )
    assert result.failure_kind == "runner"
    assert runs(log)[0]["retryable"] is True


def test_opencode_permanent_provider_failure_is_not_retryable(tmp_path):
    spec = load_spec(make_agent(tmp_path))
    log = tmp_path / "runs.jsonl"
    result = invoke(
        root=tmp_path, spec=spec, skill="sample-skill", run_log=log,
        runner_backend="opencode", model="opencode/muse-spark-1.2-contributor-free",
        command_runner=lambda command, **kw: subprocess.CompletedProcess(
            command, 1,
            '{"type":"error","error":{"data":{"responseBody":"RegionError: This model is not available in your country"}}}',
            "",
        ),
    )
    assert result.status == "failed"
    assert result.failure_kind == "provider_rejection"
    assert runs(log)[0]["retryable"] is False
