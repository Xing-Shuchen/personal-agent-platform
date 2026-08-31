"""Black-box tests for the World Historian deterministic runtime."""

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CLI = REPO / "agents/world-historian/runtime/cli.py"


def run_runtime(db: Path, *args: str):
    return subprocess.run([sys.executable, str(CLI), "--db", str(db), *args],
                          capture_output=True, text=True, cwd=REPO)


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
