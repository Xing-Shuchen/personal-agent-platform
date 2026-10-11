"""Tests for pap.spec — loading and validation of pap/v1 Agent specs."""

import textwrap
from pathlib import Path

import pytest

from pap.spec import SpecError, load_platform, load_spec


def write_agent(root: Path, name: str, body: str) -> Path:
    d = root / "agents" / name
    d.mkdir(parents=True)
    skill = d / "profile" / "skills" / "test-skill"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("# Test skill\n", encoding="utf-8")
    p = d / "agent.yaml"
    p.write_text(textwrap.dedent(body), encoding="utf-8")
    return p


VALID = """
    apiVersion: pap/v1
    kind: Agent
    metadata:
      name: test-agent
      description: A test agent.
    spec:
      profile:
        name: test-agent
        source: profile
      capabilities:
        - personal_context.read
      proactive:
        enabled: true
        class: conversational
        desired_jobs:
          - name: test-pulse
            schedule: every 4h
            skill: test-skill
      state:
        private:
          - notes
"""


def test_valid_spec(tmp_path: Path):
    write_agent(tmp_path, "test-agent", VALID)
    spec = load_spec(tmp_path / "agents" / "test-agent" / "agent.yaml")
    assert spec.name == "test-agent"
    assert spec.proactive_enabled is True
    assert spec.jobs[0].schedule == "every 4h"
    assert spec.jobs[0].skill == "test-skill"
    assert spec.jobs[0].args == {}
    assert spec.jobs[0].model is None
    assert spec.jobs[0].runner == "openclaw"
    assert spec.jobs[0].notify is None
    assert spec.private_state == ["notes"]


def test_provider_rejection_fallback_requires_a_provider_model(tmp_path: Path):
    valid = VALID.replace(
        "      capabilities:",
        "      provider_rejection_fallback: test-provider/test-model\n      capabilities:",
    )
    path = write_agent(tmp_path / "valid", "test-agent", valid)
    assert load_spec(path).provider_rejection_fallback == "test-provider/test-model"

    invalid = valid.replace("test-provider/test-model", "deepseek")
    path = write_agent(tmp_path / "invalid", "test-agent", invalid)
    with pytest.raises(SpecError, match="provider_rejection_fallback"):
        load_spec(path)


def test_job_model_override(tmp_path: Path):
    body = VALID.replace(
        "            skill: test-skill",
        "            skill: test-skill\n            model: test-provider/test-large",
    )
    write_agent(tmp_path, "test-agent", body)
    spec = load_spec(tmp_path / "agents" / "test-agent" / "agent.yaml")
    assert spec.jobs[0].model == "test-provider/test-large"


def test_job_notify_validation_and_loading(tmp_path: Path):
    valid = VALID.replace("            skill: test-skill", """            skill: test-skill
            notify:
              channel: feishu
              account: diary
              target: ou_test""")
    path = write_agent(tmp_path / "valid", "test-agent", valid)
    assert load_spec(path).jobs[0].notify == {"channel": "feishu", "account": "diary", "target": "ou_test"}

    for name, replacement in {
        "non_mapping": "            notify: feishu",
        "missing": "            notify:\n              channel: feishu\n              account: diary",
        "empty": "            notify:\n              channel: feishu\n              account: ''\n              target: ou_test",
    }.items():
        path = write_agent(tmp_path / name, "test-agent", VALID.replace(
            "            skill: test-skill", "            skill: test-skill\n" + replacement,
        ))
        with pytest.raises(SpecError, match="notify"):
            load_spec(path)


@pytest.mark.parametrize("deliver_at", ["08:00", "08:00 tz Asia/Shanghai"])
def test_job_deliver_at_is_loaded(tmp_path: Path, deliver_at: str):
    body = VALID.replace(
        "            skill: test-skill",
        f"            skill: test-skill\n            deliver_at: {deliver_at}",
    )
    path = write_agent(tmp_path, "test-agent", body)
    assert load_spec(path).jobs[0].deliver_at == deliver_at


@pytest.mark.parametrize("deliver_at", ["8:00", "24:00", "08:60", "08:00 UTC", "08:00 tz Not/AZone"])
def test_job_deliver_at_rejects_malformed_values(tmp_path: Path, deliver_at: str):
    body = VALID.replace(
        "            skill: test-skill",
        f"            skill: test-skill\n            deliver_at: {deliver_at}",
    )
    path = write_agent(tmp_path, "test-agent", body)
    with pytest.raises(SpecError, match="deliver_at"):
        load_spec(path)


def test_job_codex_runner(tmp_path: Path):
    body = VALID.replace(
        "            skill: test-skill",
        "            skill: test-skill\n            runner: codex",
    )
    write_agent(tmp_path, "test-agent", body)
    spec = load_spec(tmp_path / "agents" / "test-agent" / "agent.yaml")
    assert spec.jobs[0].runner == "codex"


def test_job_opencode_runner_requires_a_provider_model(tmp_path: Path):
    cases = [
        ("            runner: opencode", "required for runner"),
        ("            runner: opencode\n            model: mimo-v2.5-free", "<provider>/<model>"),
        ("            runner: opencode\n            model: opencode/", "<provider>/<model>"),
        ("            runner: opencode\n            model: opencode/mimo-v2.5-free\n            command: [tool]", "only be set"),
    ]
    for i, (replacement, message) in enumerate(cases):
        path = write_agent(tmp_path / str(i), "test-agent", VALID.replace(
            "            skill: test-skill", "            skill: test-skill\n" + replacement
        ))
        with pytest.raises(SpecError, match=message):
            load_spec(path)

    path = write_agent(tmp_path / "valid-opencode", "test-agent", VALID.replace(
        "            skill: test-skill",
        "            skill: test-skill\n            runner: opencode\n            model: opencode/mimo-v2.5-free",
    ))
    job = load_spec(path).jobs[0]
    assert job.runner == "opencode"
    assert job.model == "opencode/mimo-v2.5-free"


def test_command_runner_validation_and_loading(tmp_path: Path):
    command = "            runner: command\n            command: [python3, -c, 'print(1)']"
    cases = [
        ("            runner: command", "required for runner"),
        ("            command: [python3]", "only be set"),
        (command + "\n            runtime: adapter", "cannot be set"),
        (command + "\n            model: x/y", "cannot be set"),
    ]
    for i, (replacement, message) in enumerate(cases):
        path = write_agent(tmp_path / str(i), "test-agent", VALID.replace("            skill: test-skill", "            skill: test-skill\n" + replacement))
        with pytest.raises(SpecError, match=message):
            load_spec(path)
    path = write_agent(tmp_path / "valid", "test-agent", VALID.replace("            skill: test-skill", "            skill: test-skill\n" + command))
    job = load_spec(path).jobs[0]
    assert job.runner == "command"
    assert job.command == ["python3", "-c", "print(1)"]


def test_proactive_disabled(tmp_path: Path):
    body = VALID.replace("enabled: true", "enabled: false").replace(
        "        desired_jobs:\n          - name: test-pulse\n"
        "            schedule: every 4h\n            skill: test-skill\n", "")
    write_agent(tmp_path, "test-agent", body)
    spec = load_spec(tmp_path / "agents" / "test-agent" / "agent.yaml")
    assert spec.proactive_enabled is False
    assert spec.jobs == []


def test_desired_jobs_without_enabled_rejected(tmp_path: Path):
    body = VALID.replace("enabled: true", "enabled: false")
    write_agent(tmp_path, "test-agent", body)
    with pytest.raises(SpecError, match="desired_jobs set but enabled is false"):
        load_spec(tmp_path / "agents" / "test-agent" / "agent.yaml")


@pytest.mark.parametrize("missing", ["apiVersion", "kind", "metadata", "spec"])
def test_missing_top_level(tmp_path: Path, missing: str):
    body = VALID
    lines = [l for l in body.splitlines()
             if not l.strip().startswith(missing + ":")]
    body = "\n".join(lines)
    write_agent(tmp_path, "test-agent", body)
    with pytest.raises(SpecError):
        load_spec(tmp_path / "agents" / "test-agent" / "agent.yaml")


def test_bad_api_version(tmp_path: Path):
    write_agent(tmp_path, "test-agent", VALID.replace("pap/v1", "pap/v2"))
    with pytest.raises(SpecError, match="apiVersion"):
        load_spec(tmp_path / "agents" / "test-agent" / "agent.yaml")


def test_bad_kind(tmp_path: Path):
    write_agent(tmp_path, "test-agent", VALID.replace("kind: Agent", "kind: Widget"))
    with pytest.raises(SpecError, match="kind"):
        load_spec(tmp_path / "agents" / "test-agent" / "agent.yaml")


def test_invalid_name(tmp_path: Path):
    write_agent(tmp_path, "test-agent", VALID.replace("name: test-agent", "name: Bad_Name"))
    with pytest.raises(SpecError, match="metadata.name"):
        load_spec(tmp_path / "agents" / "test-agent" / "agent.yaml")


@pytest.mark.parametrize("sched", ["every 4x", "daily", "every"])
def test_invalid_schedule(tmp_path: Path, sched: str):
    body = VALID.replace("schedule: every 4h", f"schedule: {sched}")
    write_agent(tmp_path, "test-agent", body)
    with pytest.raises(SpecError, match="schedule"):
        load_spec(tmp_path / "agents" / "test-agent" / "agent.yaml")


@pytest.mark.parametrize("sched", ["every 30m", "every 2h", "every 1d", "09:00", "cron 0 9 * * *"])
def test_valid_schedules(tmp_path: Path, sched: str):
    body = VALID.replace("schedule: every 4h", f"schedule: {sched}")
    write_agent(tmp_path, "test-agent", body)
    spec = load_spec(tmp_path / "agents" / "test-agent" / "agent.yaml")
    assert spec.jobs[0].schedule == sched


def test_raw_cron_and_job_args(tmp_path: Path):
    body = VALID.replace("schedule: every 4h", "schedule: 17 */2 * * *").replace(
        "            skill: test-skill",
        "            skill: test-skill\n            args:\n              priority: high",
    )
    write_agent(tmp_path, "test-agent", body)
    spec = load_spec(tmp_path / "agents" / "test-agent" / "agent.yaml")
    assert spec.jobs[0].schedule == "17 */2 * * *"
    assert spec.jobs[0].args == {"priority": "high"}


def test_bad_job_args(tmp_path: Path):
    body = VALID.replace("skill: test-skill", "skill: test-skill\n            args: nope")
    write_agent(tmp_path, "test-agent", body)
    with pytest.raises(SpecError, match="args"):
        load_spec(tmp_path / "agents" / "test-agent" / "agent.yaml")


def test_duplicate_job_names(tmp_path: Path):
    dup = ("          - name: test-pulse\n            schedule: every 4h\n"
           "            skill: test-skill\n")
    body = VALID.replace(dup, dup + dup)
    write_agent(tmp_path, "test-agent", body)
    with pytest.raises(SpecError, match="duplicate job"):
        load_spec(tmp_path / "agents" / "test-agent" / "agent.yaml")


def test_bad_delivery(tmp_path: Path):
    body = VALID.replace("skill: test-skill", "skill: test-skill\n            delivery: snapchat")
    write_agent(tmp_path, "test-agent", body)
    with pytest.raises(SpecError, match="delivery"):
        load_spec(tmp_path / "agents" / "test-agent" / "agent.yaml")


def test_bad_class(tmp_path: Path):
    body = VALID.replace("class: conversational", "class: aggressive")
    write_agent(tmp_path, "test-agent", body)
    with pytest.raises(SpecError, match="proactive.class"):
        load_spec(tmp_path / "agents" / "test-agent" / "agent.yaml")


def test_duplicate_capabilities(tmp_path: Path):
    body = VALID.replace(
        "      capabilities:\n        - personal_context.read\n",
        "      capabilities:\n        - personal_context.read\n        - personal_context.read\n")
    write_agent(tmp_path, "test-agent", body)
    with pytest.raises(SpecError, match="duplicates"):
        load_spec(tmp_path / "agents" / "test-agent" / "agent.yaml")


def test_load_platform_multiple_and_sorted(tmp_path: Path):
    write_agent(tmp_path, "zeta", VALID.replace("test-agent", "zeta"))
    write_agent(tmp_path, "alpha", VALID.replace("test-agent", "alpha"))
    specs = load_platform(tmp_path)
    assert [s.name for s in specs] == ["alpha", "zeta"]


def test_load_platform_duplicate_names(tmp_path: Path):
    # Two directories, same metadata.name -> rejected.
    p1 = write_agent(tmp_path, "dir-a", VALID)
    d2 = tmp_path / "agents" / "dir-b"
    d2.mkdir(parents=True)
    skill = d2 / "profile/skills/test-skill"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("# Test skill\n", encoding="utf-8")
    (d2 / "agent.yaml").write_text(p1.read_text(encoding="utf-8"), encoding="utf-8")
    with pytest.raises(SpecError, match="duplicate agent names"):
        load_platform(tmp_path)


def test_load_platform_empty(tmp_path: Path):
    (tmp_path / "agents").mkdir()
    with pytest.raises(SpecError, match="no agent.yaml"):
        load_platform(tmp_path)


def test_load_platform_rejects_missing_job_skill(tmp_path: Path):
    manifest = write_agent(tmp_path, "test-agent", VALID)
    (manifest.parent / "profile/skills/test-skill/SKILL.md").unlink()
    with pytest.raises(SpecError, match="skill file not found"):
        load_platform(tmp_path)
