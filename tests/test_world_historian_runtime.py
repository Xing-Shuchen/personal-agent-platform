"""Black-box tests for the World Historian deterministic runtime."""

import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CLI = REPO / "agents/world-historian/runtime/cli.py"


def run_runtime(db: Path, *args: str):
    env = dict(os.environ, WORLD_HISTORIAN_VAULT_DIR=str(db.parent / "vault"))
    return subprocess.run([sys.executable, str(CLI), "--db", str(db), *args],
                          capture_output=True, text=True, cwd=REPO, env=env)


def sample_bundle():
    return {
        "sources": [{"ref": "official", "canonical_url": "https://example.test/a",
                     "title": "Announcement", "source_kind": "primary"}],
        "threads": [{"ref": "thread", "title": "Example transition",
                     "questions": ["Why now?"], "watch_queries": ["Example follow-up"],
                     "entity_names": [{"name": "Example", "kind": "organization"}]}],
        "events": [{"ref": "event", "summary": "Example changed",
                    "occurred_at": "2026-08-30", "occurred_at_precision": "day",
                    "reported_at": "2026-08-30T09:00:00+08:00",
                    "observed_at": "2026-08-31T12:00:00+08:00",
                    "thread_refs": ["thread"], "entity_names": ["Example"]}],
        "claims": [{"event_ref": "event", "source_ref": "official",
                    "statement": "Example changed.", "confidence": 0.95,
                    "status": "confirmed"}],
    }


def test_store_bundle_is_atomic_and_idempotent(tmp_path):
    db = tmp_path / "chronicle.sqlite"
    bundle = tmp_path / "bundle.json"
    bundle.write_text(json.dumps(sample_bundle()), encoding="utf-8")
    first = run_runtime(db, "store-bundle", "--json", str(bundle))
    assert first.returncode == 0, first.stderr
    second = run_runtime(db, "store-bundle", "--json", str(bundle))
    assert second.returncode == 0, second.stderr
    result = run_runtime(db, "stats")
    counts = json.loads(result.stdout)
    assert counts["threads"] == 1
    assert counts["events"] == 1
    assert counts["claims"] == 1
    assert counts["sources"] == 1


def test_invalid_personal_relation_rolls_back_whole_bundle(tmp_path):
    db = tmp_path / "chronicle.sqlite"
    data = sample_bundle()
    data["personal_links"] = [{"world_event_ref": "event", "personal_event_id": "p1",
                               "relation_type": "search_private_web",
                               "explanation": "bad", "confidence": 0.8}]
    bundle = tmp_path / "bad.json"
    bundle.write_text(json.dumps(data), encoding="utf-8")
    result = run_runtime(db, "store-bundle", "--json", str(bundle))
    assert result.returncode == 2
    counts = json.loads(run_runtime(db, "stats").stdout)
    assert counts["threads"] == 0
    assert counts["events"] == 0


def test_non_default_db_without_vault_env_skips_obsidian(tmp_path):
    """`--db` override with no explicit vault target must not touch the vault."""
    db = tmp_path / "chronicle.sqlite"
    bundle = tmp_path / "bundle.json"
    bundle.write_text(json.dumps(sample_bundle()), encoding="utf-8")
    env = {k: v for k, v in os.environ.items() if k != "WORLD_HISTORIAN_VAULT_DIR"}
    result = subprocess.run(
        [sys.executable, str(CLI), "--db", str(db),
         "store-bundle", "--json", str(bundle)],
        capture_output=True, text=True, cwd=REPO, env=env)
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["obsidian"]["skipped"] is True
    assert "reason" in payload["obsidian"]
    assert not (tmp_path / "vault").exists()


def test_store_bundle_syncs_to_configured_vault(tmp_path):
    db = tmp_path / "chronicle.sqlite"
    bundle = tmp_path / "bundle.json"
    bundle.write_text(json.dumps(sample_bundle()), encoding="utf-8")
    result = run_runtime(db, "store-bundle", "--json", str(bundle))
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    vault = tmp_path / "vault"
    files = sorted(p.name for p in vault.glob("*.md"))
    assert payload["obsidian"]["written"] == [str(vault / files[0])]
    text = (vault / files[0]).read_text(encoding="utf-8")
    assert "thread_id:" in text and "## 手工批注" in text
    assert (tmp_path / "obsidian-index.json").exists()  # index lives next to the DB


def test_roster_formats_orders_and_filters_delivery_threads(tmp_path):
    db = tmp_path / "chronicle.sqlite"
    bundle = tmp_path / "roster.json"
    bundle.write_text(json.dumps({
        "threads": [
            {"title": "Zulu high", "priority": "high"},
            {"title": "Bravo high", "priority": "high"},
            {"title": "Alpha normal", "priority": "normal"},
            {"title": "Zulu normal", "priority": "normal"},
            {"title": "Excluded low", "priority": "low"},
            {"title": "Excluded background", "priority": "background"},
            {"title": "Excluded closed", "priority": "high", "status": "closed"},
        ],
    }), encoding="utf-8")
    stored = run_runtime(db, "store-bundle", "--json", str(bundle))
    assert stored.returncode == 0, stored.stderr

    first = run_runtime(db, "roster")
    second = run_runtime(db, "roster")
    expected = (
        "- 🟥 **Bravo high**（high）\n"
        "- 🟥 **Zulu high**（high）\n"
        "- 🟦 **Alpha normal**（normal）\n"
        "- 🟦 **Zulu normal**（normal）\n"
    )
    assert first.returncode == 0, first.stderr
    assert first.stdout == expected
    assert second.stdout == expected
