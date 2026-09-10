"""End-to-end tests: pap CLI (validate + gate) and scripts/install_agents.py."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]


def run(args, cwd=REPO):
    return subprocess.run([sys.executable, "-m", "pap.cli"] + args,
                          capture_output=True, text=True, cwd=cwd)


def test_validate_repo_specs():
    """The four shipped agents must validate out of the box."""
    r = run(["validate", "--root", str(REPO)])
    assert r.returncode == 0, r.stderr
    assert "agent spec(s) valid." in r.stdout
    for name in ("serendipity", "intelligence", "red-team", "world-historian"):
        assert f"OK {name}" in r.stdout


def test_validate_json_output():
    r = run(["validate", "--root", str(REPO), "--json"])
    assert r.returncode == 0
    data = json.loads(r.stdout)
    assert {d["name"] for d in data} == {
        "serendipity", "intelligence", "red-team", "world-historian", "compiler-news"
    }


def test_validate_invalid_spec_fails(tmp_path):
    bad = tmp_path / "agents" / "broken"
    bad.mkdir(parents=True)
    (bad / "agent.yaml").write_text("apiVersion: pap/v1\nkind: Nope\n", encoding="utf-8")
    r = run(["validate", "--root", str(tmp_path)])
    assert r.returncode == 1
    assert "INVALID" in r.stderr


def test_gate_cli_allow_and_deny(tmp_path):
    db = tmp_path / "db.json"
    # priority 95 passes both daytime (>=70) and quiet-hours (>=90) bars.
    r1 = subprocess.run(
        [sys.executable, "-m", "pap.cli", "gate", "--agent", "a", "--dedupe-key", "k1",
         "--priority", "95", "--db", str(db)],
        capture_output=True, text=True, cwd=REPO)
    assert r1.returncode == 0, r1.stdout + r1.stderr
    assert json.loads(r1.stdout)["allowed"] is True

    # Immediate repeat with same key -> denied (exit 1).
    r2 = subprocess.run(
        [sys.executable, "-m", "pap.cli", "gate", "--agent", "a", "--dedupe-key", "k1",
         "--priority", "95", "--db", str(db)],
        capture_output=True, text=True, cwd=REPO)
    assert r2.returncode == 1, r2.stdout + r2.stderr
    assert "dedupe" in json.loads(r2.stdout)["reason"]


def test_gate_cli_message_audited(tmp_path):
    db = tmp_path / "db.json"
    subprocess.run(
        [sys.executable, "-m", "pap.cli", "gate", "--agent", "a", "--dedupe-key", "k",
         "--priority", "10", "--message", "candidate text", "--db", str(db)],
        capture_output=True, text=True, cwd=REPO)
    log_lines = (tmp_path / "gate-log.jsonl").read_text().splitlines()
    recs = [json.loads(l) for l in log_lines]
    assert any(rec.get("type") == "message-preview" and rec["message"] == "candidate text"
               for rec in recs)


def test_install_agents_list_only():
    r = subprocess.run(
        [sys.executable, "scripts/install_agents.py", "--list-only"],
        capture_output=True, text=True, cwd=REPO)
    assert r.returncode == 0, r.stderr
    assert "agent: serendipity" in r.stdout
    assert "15 0,8,10,12,14,16,18,20,22 * * *" in r.stdout
    assert "agent: intelligence" in r.stdout
    assert "no platform jobs (proactive disabled)" in r.stdout
    assert "platform job world-follow-high" in r.stdout
    assert "cron create" not in r.stdout
    assert "OpenClaw workspace:" in r.stdout
    assert "workspace-serendipity" in r.stdout
    assert ".hermes" not in r.stdout


def test_install_agents_rejects_bad_openclaw_home():
    r = subprocess.run(
        [sys.executable, "scripts/install_agents.py", "--apply",
         "--openclaw-home", "/nonexistent-dir"],
        capture_output=True, text=True, cwd=REPO)
    assert r.returncode == 1
    assert "not found" in r.stderr
