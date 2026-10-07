from pathlib import Path

import pytest

from pap.cli import _find_spec
from pap.scheduler import due_jobs
from pap.spec import SpecError, load_platform


def _write_sample_agent(tmp_path: Path) -> None:
    agent = tmp_path / "agents" / "sample"
    agent.mkdir(parents=True)
    (agent / "agent.yaml").write_text("""apiVersion: pap/v1
kind: Agent
metadata:
  name: sample
  description: Example agent
spec:
  enabled: false
  profile:
    name: sample
  proactive:
    enabled: false
""", encoding="utf-8")


def test_agent_is_off_until_local_switch_enables_it(tmp_path: Path):
    _write_sample_agent(tmp_path)
    assert load_platform(tmp_path)[0].enabled is False
    assert load_platform(tmp_path)[0].provider_rejection_fallback is None
    with pytest.raises(SpecError, match="disabled"):
        _find_spec(tmp_path, "sample")
    assert due_jobs(tmp_path, reserve=False) == []

    config = tmp_path / "var" / "config"
    config.mkdir(parents=True)
    (config / "agents.yaml").write_text("agents:\n  sample: {enabled: true}\n", encoding="utf-8")
    assert load_platform(tmp_path)[0].enabled is True
    assert load_platform(tmp_path)[0].provider_rejection_fallback is None
    assert _find_spec(tmp_path, "sample").name == "sample"


def test_local_provider_rejection_fallback_reaches_loaded_spec(tmp_path: Path):
    _write_sample_agent(tmp_path)
    config = tmp_path / "var" / "config"
    config.mkdir(parents=True)
    (config / "agents.yaml").write_text(
        "agents:\n  sample: {enabled: true, provider_rejection_fallback: provider/model}\n",
        encoding="utf-8",
    )

    assert load_platform(tmp_path)[0].provider_rejection_fallback == "provider/model"


@pytest.mark.parametrize("fallback", ["notaroute", "a/b/c", '"a /b"'])
def test_local_provider_rejection_fallback_requires_provider_model(tmp_path: Path, fallback: str):
    _write_sample_agent(tmp_path)
    config = tmp_path / "var" / "config"
    config.mkdir(parents=True)
    (config / "agents.yaml").write_text(
        f"agents:\n  sample: {{enabled: true, provider_rejection_fallback: {fallback}}}\n",
        encoding="utf-8",
    )

    with pytest.raises(SpecError, match="provider_rejection_fallback"):
        load_platform(tmp_path)


def test_local_override_rejects_unknown_key(tmp_path: Path):
    _write_sample_agent(tmp_path)
    config = tmp_path / "var" / "config"
    config.mkdir(parents=True)
    (config / "agents.yaml").write_text(
        "agents:\n  sample: {enabled: true, unknown: value}\n", encoding="utf-8"
    )

    with pytest.raises(SpecError, match="unknown override keys"):
        load_platform(tmp_path)


@pytest.mark.parametrize("config_body", [
    "provider_rejection_fallback: provider/model",
    'enabled: "yes", provider_rejection_fallback: provider/model',
])
def test_local_fallback_still_requires_boolean_enabled(tmp_path: Path, config_body: str):
    _write_sample_agent(tmp_path)
    config = tmp_path / "var" / "config"
    config.mkdir(parents=True)
    (config / "agents.yaml").write_text(
        f"agents:\n  sample: {{{config_body}}}\n", encoding="utf-8"
    )

    with pytest.raises(SpecError, match="enabled must be a boolean"):
        load_platform(tmp_path)
