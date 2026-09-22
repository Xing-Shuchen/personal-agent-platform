"""Black-box tests for the World Historian deterministic runtime."""

import json
import os
import sqlite3
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
    assert "thread_id:" in text and "# 手工批注" in text
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


def test_active_thread_titles_orders_newest_first_and_handles_empty_db(tmp_path):
    db = tmp_path / "chronicle.sqlite"
    empty_bundle = tmp_path / "empty.json"
    empty_bundle.write_text("{}", encoding="utf-8")
    initialized = run_runtime(db, "store-bundle", "--json", str(empty_bundle))
    assert initialized.returncode == 0, initialized.stderr

    empty = run_runtime(db, "active-thread-titles")
    assert empty.returncode == 0, empty.stderr
    assert empty.stdout == ""

    bundle = tmp_path / "threads.json"
    bundle.write_text(json.dumps({"threads": [
        {"title": "Old active"},
        {"title": "New active"},
        {"title": "Closed", "status": "closed"},
    ]}), encoding="utf-8")
    stored = run_runtime(db, "store-bundle", "--json", str(bundle))
    assert stored.returncode == 0, stored.stderr
    with sqlite3.connect(db) as conn:
        conn.execute("UPDATE threads SET updated_at = ? WHERE title = ?",
                     ("2026-09-15T01:00:00+00:00", "Old active"))
        conn.execute("UPDATE threads SET updated_at = ? WHERE title = ?",
                     ("2026-09-16T01:00:00+00:00", "New active"))

    titles = run_runtime(db, "active-thread-titles")
    assert titles.returncode == 0, titles.stderr
    assert titles.stdout == "New active\nOld active\n"


def test_personal_link_exists_prints_one_only_for_existing_pair(tmp_path):
    db = tmp_path / "chronicle.sqlite"
    data = sample_bundle()
    data["events"][0]["id"] = "world-event-1"
    data["personal_links"] = [{
        "world_event_ref": "event", "personal_event_id": "personal-1",
        "relation_type": "affected_by", "explanation": "Relevant public context.",
        "confidence": 0.8, "evidence": ["personal-1"],
    }]
    bundle = tmp_path / "link.json"
    bundle.write_text(json.dumps(data), encoding="utf-8")
    stored = run_runtime(db, "store-bundle", "--json", str(bundle))
    assert stored.returncode == 0, stored.stderr

    exists = run_runtime(db, "personal-link-exists", "world-event-1", "personal-1")
    missing = run_runtime(db, "personal-link-exists", "world-event-1", "personal-2")
    assert exists.returncode == 0, exists.stderr
    assert exists.stdout == "1\n"
    assert missing.returncode == 0, missing.stderr
    assert missing.stdout == ""


def test_daily_stats_combines_run_log_and_chronicle_for_requested_day(tmp_path):
    db = tmp_path / "chronicle.sqlite"
    data = sample_bundle()
    data["threads"][0]["id"] = "thread-1"
    data["events"][0]["id"] = "event-1"
    bundle = tmp_path / "daily.json"
    bundle.write_text(json.dumps(data), encoding="utf-8")
    stored = run_runtime(db, "store-bundle", "--json", str(bundle))
    assert stored.returncode == 0, stored.stderr
    with sqlite3.connect(db) as conn:
        for table in ("threads", "events", "claims"):
            conn.execute(f"UPDATE {table} SET created_at = ?", ("2026-09-16T09:00:00+08:00",))
        conn.execute("UPDATE threads SET updated_at = ?", ("2026-09-16T10:00:00+08:00",))

    runs = tmp_path / "runs.jsonl"
    records = [
        {"event": "run.delivery", "run_id": "brief", "delivery": "sent"},
        {"event": "run.completed", "run_id": "brief", "agent_id": "world-historian",
         "completed_at": "2026-09-16T09:00:00+08:00", "status": "success",
         "trigger": {"job_id": "morning-brief"}},
        {"event": "run.completed", "run_id": "stats", "agent_id": "world-historian",
         "completed_at": "2026-09-16T23:59:00+08:00", "status": "timeout",
         "trigger": {"job_id": "daily-stats"}},
        {"event": "run.delivery", "run_id": "stats", "delivery": "silent"},
        {"event": "run.completed", "run_id": "other", "agent_id": "other-agent",
         "completed_at": "2026-09-16T12:00:00+08:00", "status": "success",
         "trigger": {"job_id": "other"}},
    ]
    runs.write_text("".join(json.dumps(record) + "\n" for record in records), encoding="utf-8")

    result = run_runtime(db, "daily-stats", "--day", "2026-09-16", "--runs", str(runs))
    assert result.returncode == 0, result.stderr
    assert result.stdout == (
        "day 2026-09-16\n"
        "runs\n"
        "job daily-stats delivery:silent=1 timeout=1\n"
        "job morning-brief delivery:sent=1 success=1\n"
        "chronicle\n"
        "threads 1\n"
        "events 1\n"
        "claims 1\n"
        "updated-thread thread-1 Example transition normal active\n"
    )


def test_lifecycle_candidates_apply_stale_thresholds_and_priority_rules(tmp_path):
    db = tmp_path / "chronicle.sqlite"
    bundle = tmp_path / "lifecycle.json"
    bundle.write_text(json.dumps({
        "threads": [
            {"id": "no-event", "title": "No event", "status": "active"},
            {"id": "high-stale", "title": "High stale", "status": "active",
             "priority": "high"},
            {"id": "normal-stale", "title": "Normal stale", "status": "active",
             "priority": "normal"},
            {"id": "low-stale", "title": "Low stale", "status": "active",
             "priority": "low"},
            {"id": "idle-background", "title": "Idle background", "status": "active",
             "priority": "background"},
            {"id": "normal-recent", "title": "Normal recent", "status": "active",
             "priority": "normal"},
            {"id": "high-very-stale", "title": "High very stale", "status": "active",
             "priority": "high"},
        ],
        "events": [
            {"id": "high-event", "summary": "High", "occurred_at": "2026-09-13",
             "occurred_at_precision": "day", "observed_at": "2026-09-13T00:00:00",
             "thread_refs": ["high-stale"]},
            {"id": "normal-event", "summary": "Normal", "occurred_at": "2026-09-09",
             "occurred_at_precision": "day", "observed_at": "2026-09-09T00:00:00",
             "thread_refs": ["normal-stale"]},
            {"id": "low-event", "summary": "Low", "occurred_at": "2026-09-02",
             "occurred_at_precision": "day", "observed_at": "2026-09-02T00:00:00",
             "thread_refs": ["low-stale"]},
            {"id": "background-event", "summary": "Background", "occurred_at": "2026-08-20",
             "occurred_at_precision": "day", "observed_at": "2026-08-20T00:00:00",
             "thread_refs": ["idle-background"]},
            {"id": "recent-event", "summary": "Recent", "occurred_at": "2026-09-16",
             "occurred_at_precision": "day", "observed_at": "2026-09-16T00:00:00",
             "thread_refs": ["normal-recent"]},
            {"id": "very-stale-event", "summary": "Very stale", "occurred_at": "2026-08-18",
             "occurred_at_precision": "day", "observed_at": "2026-08-18T00:00:00",
             "thread_refs": ["high-very-stale"]},
        ],
    }), encoding="utf-8")
    stored = run_runtime(db, "store-bundle", "--json", str(bundle))
    assert stored.returncode == 0, stored.stderr

    result = run_runtime(db, "lifecycle-candidates", "--now", "2026-09-17T00:00:00")
    assert result.returncode == 0, result.stderr
    assert result.stdout == (
        "DEMOTE\thigh-stale\tHigh stale\tnormal\n"
        "DEMOTE\thigh-very-stale\tHigh very stale\tnormal\n"
        "DEMOTE\tlow-stale\tLow stale\tbackground\n"
        "CLOSE\tno-event\tNo event\n"
        "DEMOTE\tnormal-stale\tNormal stale\tlow\n"
    )
