"""Cognition adapters consume pre-built indexes without rebuilding at runtime."""
from __future__ import annotations

import importlib
import io
import json
import sqlite3
from pathlib import Path
from unittest.mock import Mock

import pytest

from pap.cognition import Index, default_index


@pytest.fixture(params=["intelligence", "serendipity"])
def adapter(request):
    return importlib.import_module(f"agents.{request.param}.runtime.cognition")


@pytest.fixture
def vault(tmp_path, monkeypatch):
    path = tmp_path / "vault"
    path.mkdir()
    # Fixture builds must never load or download an embedding model.
    monkeypatch.setenv("PAP_CANDIDATE_RETRIEVAL_EMBEDDINGS_ENABLED", "0")
    return path


@pytest.fixture
def run_adapter(adapter, vault, monkeypatch, capsys):
    def run(action="prepare", **payload):
        build = Mock(side_effect=AssertionError("runtime must not build the index"))
        monkeypatch.setattr(Index, "build", build)
        monkeypatch.setenv("PAP_VAULT", str(vault))
        monkeypatch.setattr(adapter.sys, "argv", [adapter.__file__, action])
        monkeypatch.setattr(adapter.sys, "stdin", io.StringIO(json.dumps({"run_id": "runtime-test", **payload})))
        assert adapter.main() == 0
        build.assert_not_called()
        output = capsys.readouterr()
        assert output.err == ""
        return json.loads(output.out)

    return run


def seed_index(vault: Path):
    (vault / "plan.md").write_text("# Plan\nA shared mechanism changes a project constraint.\n", encoding="utf-8")
    index = Index(default_index(vault))
    try:
        index.build(vault)
    finally:
        index.close()


@pytest.mark.parametrize("state", ["absent", "empty", "zero-byte", "no-documents", "no-evidence"])
def test_prepare_missing_or_empty_index_is_not_ready(state, vault, run_adapter):
    path = default_index(vault)
    if state == "zero-byte":
        path.parent.mkdir(parents=True)
        path.touch()
    elif state != "absent":
        if state != "empty":
            seed_index(vault)
        index = Index(path)
        try:
            if state == "no-documents":
                index.db.execute("UPDATE documents SET deleted=1")
            elif state == "no-evidence":
                index.db.execute("UPDATE evidence_units SET active=0")
            index.db.commit()
        finally:
            index.close()

    result = run_adapter()

    assert set(result) == {"status", "reason"}
    assert result["status"] == "not_ready"
    assert "pre-built" in result["reason"]
    assert "PAP_VAULT" in result["reason"]
    assert "pap cognition index" in result["reason"]
    if state == "absent":
        assert not path.parent.exists()


def test_prepare_missing_vault_is_not_ready(vault, run_adapter):
    vault.rmdir()

    assert run_adapter() == {
        "status": "not_ready",
        "reason": f"PAP_VAULT is not configured or its directory is missing: {vault}",
    }
    assert not vault.exists()


def test_prebuilt_index_prepare_and_feedback_preserve_wire_contract(adapter, vault, run_adapter):
    seed_index(vault)

    result = run_adapter()

    assert set(result) == {"status", "input_text", "metadata"}
    assert result["status"] == "ready"
    pack = json.loads(result["input_text"].split("\n\n", 1)[1])
    agent = adapter.__name__.split(".")[1]
    assert pack["schema"] == f"{agent}.context-pack.v1"
    assert pack["run_id"] == "runtime-test"
    assert result["metadata"] == {
        "context_pack_id": pack["pack_hash"],
        "index_generation": pack["index_generation"],
        "retrieval_policy": "v0.6",
    }
    reply = '{"decisions": [], "text": "保留模型回复"}'
    assert run_adapter("complete", model_reply=reply) == {
        "status": "success",
        "response": reply,
        "metadata": {
            "context_pack": True,
            "retrieval_feedback": {"seen": 0, "accepted": 0, "rejected": 0},
        },
    }


@pytest.mark.parametrize("error", [FileNotFoundError("index vanished"), sqlite3.OperationalError("database is locked")])
def test_feedback_failure_keeps_model_reply(error, adapter, monkeypatch, run_adapter):
    complete = Mock(side_effect=error)
    monkeypatch.setattr(Index, "complete_retrieval", complete)
    reply = '{"decisions": [{"candidate_id": "candidate-test", "status": "accepted"}]}'

    assert run_adapter("complete", model_reply=reply) == {
        "status": "success",
        "response": reply,
        "metadata": {"context_pack": True, "retrieval_feedback": {"state": "skipped"}},
    }
    complete.assert_called_once_with(
        run_id="runtime-test", agent=adapter.__name__.split(".")[1],
        decisions=json.loads(reply)["decisions"],
    )


def test_prepare_busy_index_is_not_ready(vault, monkeypatch, run_adapter):
    seed_index(vault)
    monkeypatch.setattr(Index, "shadow_pack", Mock(side_effect=sqlite3.OperationalError("database is locked")))

    assert run_adapter() == {
        "status": "not_ready",
        "reason": "cognition index is busy with a concurrent build; this slot was skipped",
    }
