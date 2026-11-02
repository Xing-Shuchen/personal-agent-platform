"""Delivery destinations in the standalone tasks page."""

import json
import textwrap

import pytest

from scripts.build_tasks_page import build_html


@pytest.fixture
def task_root(tmp_path, monkeypatch):
    agent = tmp_path / "agents/test-agent"
    skill = agent / "profile/skills/test-skill"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("# Test skill\n")
    (agent / "agent.yaml").write_text(textwrap.dedent("""\
        apiVersion: pap/v1
        kind: Agent
        metadata:
          name: test-agent
          description: Test agent.
        spec:
          profile:
            name: test-agent
            source: profile
          proactive:
            enabled: true
            class: conversational
            desired_jobs:
              - name: default-job
                schedule: every 4h
                skill: test-skill
              - name: override-job
                schedule: every 4h
                skill: test-skill
              - name: local-job
                schedule: every 4h
                skill: test-skill
                delivery: local
        """))
    config = tmp_path / "var/config/agents.yaml"
    config.parent.mkdir(parents=True)
    config.write_text(textwrap.dedent("""\
        delivery:
          channel: feishu
          account: default-bot
        agents:
          test-agent:
            enabled: true
            jobs:
              override-job:
                delivery_account: override-bot
        """))
    monkeypatch.setenv("OPENCLAW_CONFIG_PATH", str(tmp_path / "openclaw.json"))
    monkeypatch.setenv("PAP_OPENCLAW_CHANNEL", "feishu")
    monkeypatch.setenv("PAP_OPENCLAW_ACCOUNT", "env-bot")
    return tmp_path


def test_delivery_names_and_local(task_root):
    (task_root / "openclaw.json").write_text(json.dumps({
        "bindings": [{"type": "route", "agentId": "archive",
                      "match": {"channel": "feishu", "accountId": "default-bot"}}],
        "agents": {"entries": {"archive": {"identity": {"name": "档案专员"}}}},
    }))
    html = build_html(task_root)
    assert '<th>Status</th><th>投送渠道</th><th>Output</th>' in html
    assert '飞书 · <small>档案专员</small>' in html
    assert '飞书 · <small>override-bot</small>' in html
    assert '本地（不投送）</td>' in html
    assert '飞书 · 档案专员' in html  # Search text includes the destination.
    assert 'env-bot' not in html


@pytest.mark.parametrize("contents", [None, "{bad json", '{"bindings": null}'])
def test_unavailable_openclaw_falls_back(task_root, contents):
    if contents is not None:
        (task_root / "openclaw.json").write_text(contents)
    html = build_html(task_root)
    assert '飞书 · <small>default-bot</small>' in html
    assert '飞书 · <small>override-bot</small>' in html


@pytest.mark.parametrize("contents", [None, "[bad yaml", "delivery: []\n", "delivery: {account: null}\n"])
def test_optional_defaults_fall_back_to_environment(task_root, contents):
    config = task_root / "var/config/agents.yaml"
    if contents is None:
        config.unlink()
    else:
        config.write_text(contents)
    assert '飞书 · <small>env-bot</small>' in build_html(task_root)
