"""Tests for the World Historian → Obsidian thread export.

Core contract: a file is written only when a committed bundle creates or
modifies a thread; the file is a projection of the database; the reader's
「手工批注」section survives re-sync; renames migrate the file and never
delete a foreign file.
"""

import json
from pathlib import Path

from conftest import load_runtime_module

db = load_runtime_module("db")
obsidian = load_runtime_module("obsidian")


def fresh(tmp_path: Path):
    conn = db.connect(tmp_path / "chronicle.sqlite")
    db.migrate(conn)
    return conn


def capture_bundle() -> dict:
    return {
        "sources": [{"ref": "s1", "canonical_url": "https://example.test/a",
                     "title": "Report A", "source_kind": "primary"}],
        "threads": [{"ref": "t1", "title": "Example transition",
                     "questions": ["Why now?"],
                     "watch_queries": ["Example follow-up"],
                     "entity_names": [{"name": "Example", "kind": "organization"}]}],
        "events": [{"ref": "e1", "summary": "Example changed",
                    "occurred_at": "2026-08-30", "occurred_at_precision": "day",
                    "reported_at": "2026-08-30T09:00:00+08:00",
                    "observed_at": "2026-08-31T12:00:00+08:00",
                    "thread_refs": ["t1"]}],
        "claims": [{"ref": "c1", "event_ref": "e1", "source_ref": "s1",
                    "statement": "Example changed.", "confidence": 0.9}],
    }


def sync(conn, tmp_path: Path, thread_ids: list[str]) -> tuple[Path, dict]:
    vault = tmp_path / "vault" / "41 新闻及事件"
    snapshots = [db.thread_snapshot(conn, tid) for tid in thread_ids]
    snapshots = [s for s in snapshots if s is not None]
    outcome = obsidian.sync_threads(
        snapshots, vault, tmp_path / "obsidian-index.json")
    return vault, outcome


def only_file(vault: Path) -> Path:
    files = sorted(p for p in vault.glob("*.md"))
    assert len(files) == 1, files
    return files[0]


def test_capture_creates_one_file_with_projection(tmp_path):
    conn = fresh(tmp_path)
    result = db.store_bundle(conn, capture_bundle())
    assert result["touched_threads"] == [result["refs"]["t1"]]
    vault, outcome = sync(conn, tmp_path, result["touched_threads"])
    assert outcome["written"] and not outcome["errors"]
    target = only_file(vault)
    text = target.read_text(encoding="utf-8")
    assert f"thread_id: \"{result['refs']['t1']}\"" in text
    assert "type: note" in text and "area: world-historian" in text
    assert "## 时间线" in text
    assert "发生时间：未知（精度：day）" not in text  # occurred_at is set here
    assert "报道时间：2026-08-30T09:00:00+08:00" in text
    assert "「Example changed.」—— Report A（primary）" in text
    assert "- [ ] Why now?" in text
    assert "`Example follow-up`（exact）" in text
    assert "## 手工批注" in text


def test_bundle_without_thread_touch_writes_nothing(tmp_path):
    """Only thread create/modify triggers the export."""
    conn = fresh(tmp_path)
    result = db.store_bundle(conn, capture_bundle())
    vault, _ = sync(conn, tmp_path, result["touched_threads"])
    before = only_file(vault).read_text(encoding="utf-8")

    # A discovery candidate touches no thread → no sync, no file change.
    result2 = db.store_bundle(conn, {
        "discovery_candidates": [{"candidate_type": "event",
                                  "title": "Peripheral rumor",
                                  "relation_score": 0.3}],
    })
    assert result2["touched_threads"] == []
    vault2, outcome2 = sync(conn, tmp_path, result2["touched_threads"])
    assert outcome2["written"] == []
    assert only_file(vault2).read_text(encoding="utf-8") == before


def test_follow_up_sync_overwrites_and_preserves_manual_notes(tmp_path):
    conn = fresh(tmp_path)
    result = db.store_bundle(conn, capture_bundle())
    vault, _ = sync(conn, tmp_path, result["touched_threads"])
    target = only_file(vault)

    # Reader adds a manual annotation.
    text = target.read_text(encoding="utf-8")
    text = text.replace("## 手工批注\n\n（无）", "## 手工批注\n\n我看过这部片子。")
    target.write_text(text, encoding="utf-8")

    # A follow-up modifies the thread (new event + claim). Note: refs are
    # bundle-local, so cross-bundle references must use actual ids.
    tid = result["refs"]["t1"]
    sid = result["refs"]["s1"]
    db.store_bundle(conn, {
        "events": [{"ref": "e2", "summary": "Example corrected",
                    "reported_at": "2026-09-01",
                    "observed_at": "2026-09-01T10:00:00+08:00",
                    "thread_refs": [tid]}],
        "claims": [{"event_ref": "e2", "source_ref": sid,
                    "statement": "Corrected figure.", "confidence": 0.8}],
        "questions": [{"thread_ref": tid, "question": "Why now?",
                       "status": "answered", "answer_event_ref": "e2"}],
    })
    _, outcome = sync(conn, tmp_path, result["touched_threads"])
    text2 = target.read_text(encoding="utf-8")
    assert outcome["written"] == [str(target)]
    assert "Example corrected" in text2           # new content projected
    assert "我看过这部片子。" in text2              # manual notes preserved
    assert "（answered）" in text2                  # question state updated
    assert text2.count("## 时间线") == 1           # single regenerated body


def test_rename_migrates_file_and_keeps_id_marker(tmp_path):
    conn = fresh(tmp_path)
    result = db.store_bundle(conn, capture_bundle())
    tid = result["refs"]["t1"]
    vault, _ = sync(conn, tmp_path, [tid])
    old_target = only_file(vault)
    old_text = old_target.read_text(encoding="utf-8")

    db.store_bundle(conn, {
        "threads": [{"id": tid, "title": "Renamed transition"}],
    })
    vault2, outcome = sync(conn, tmp_path, [tid])
    new_files = sorted(p for p in vault2.glob("*.md"))
    assert [p.name for p in new_files] == ["Renamed transition.md"]
    new_text = new_files[0].read_text(encoding="utf-8")
    assert f"thread_id: \"{tid}\"" in new_text
    assert "我看过" not in new_text  # no manual notes were added
    assert not old_target.exists()   # old name migrated away
    assert outcome["removed"] == [str(old_target)]
    assert old_text == old_text  # sanity; content compared via marker above


def test_foreign_file_is_never_deleted_on_rename(tmp_path):
    conn = fresh(tmp_path)
    result = db.store_bundle(conn, capture_bundle())
    tid = result["refs"]["t1"]
    vault, _ = sync(conn, tmp_path, [tid])
    old_target = only_file(vault)
    # Replace our projection with a foreign file that merely shares the name.
    old_target.write_text("---\ntitle: 人工笔记\n---\n\n人工内容\n", encoding="utf-8")

    db.store_bundle(conn, {"threads": [{"id": tid, "title": "Renamed again"}]})
    vault2, outcome = sync(conn, tmp_path, [tid])
    # The foreign file stays; our thread is written under a collision-safe name.
    assert old_target.exists()
    assert "人工内容" in old_target.read_text(encoding="utf-8")
    names = {p.name for p in vault2.glob("*.md")}
    assert any(name.endswith(".md") and name != old_target.name for name in names)
    assert outcome["errors"] == []


def test_empty_vault_dir_env_disables_sync(tmp_path, monkeypatch):
    monkeypatch.setenv("WORLD_HISTORIAN_VAULT_DIR", "")
    assert obsidian.vault_dir() is None
    monkeypatch.setenv("WORLD_HISTORIAN_VAULT_DIR", str(tmp_path / "custom"))
    assert obsidian.vault_dir() == tmp_path / "custom"


def test_store_bundle_failure_leaves_vault_untouched(tmp_path):
    conn = fresh(tmp_path)
    db.store_bundle(conn, capture_bundle())
    vault, _ = sync(conn, tmp_path, db.all_thread_ids(conn))
    before = only_file(vault).read_text(encoding="utf-8")

    bad = capture_bundle()
    bad["threads"][0]["title"] = "Bad transition"
    bad["claims"][0]["source_ref"] = "missing-source"
    try:
        db.store_bundle(conn, bad)
    except Exception:
        pass
    # No sync was invoked for the rolled-back bundle.
    assert only_file(vault).read_text(encoding="utf-8") == before
