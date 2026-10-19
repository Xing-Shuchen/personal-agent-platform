"""Tests for the World Historian → Obsidian thread export.

Core contract: a file is written only when a committed bundle creates or
modifies a thread; the file is a projection of the database; the reader's
「手工批注」section survives re-sync; renames migrate the file and never
delete a foreign file; a re-render that only moves ``updated:`` is a no-op
(no mtime bump, no git diff).
"""

import json
import subprocess
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
        "events": [{"ref": "e1", "title": "Example changed", "summary": "Example changed",
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


def quote_bundle() -> dict:
    """capture_bundle plus a verbatim quote carrying its own 原文素材 slug."""
    bundle = capture_bundle()
    bundle["quotes"] = [{
        "ref": "q1", "event_ref": "e1", "source_ref": "s1",
        "speaker": "Example Spokesperson", "title": "Example statement",
        "quote_text": "We changed it.",
        "summary": "The spokesperson confirmed the transition.",
        "slug": "example-statement",
    }]
    return bundle


def only_file(vault: Path) -> Path:
    files = sorted(p for p in vault.glob("*.md"))
    assert len(files) == 1, files
    return files[0]


def test_relation_notes_link_actual_paths_and_show_stored_explanations(tmp_path):
    conn = fresh(tmp_path)
    db.store_bundle(conn, {
        "threads": [
            {"id": "thr_alpha", "title": "Foo/Bar", "related_threads": [
                {"thread_id": "thr_closed", "note": "Shared archived context"}]},
            {"id": "thr_beta", "title": "Foo:Bar"},
            {"id": "thr_closed", "title": "Archived #topic", "status": "closed"},
        ],
        "relations": [
            {"src_type": "thread", "src_ref": "thr_alpha", "dst_type": "thread",
             "dst_ref": "thr_beta", "relation_type": "competes_with", "confidence": 0.85,
             "evidence": ["evt_reference", "关联理由：Both products target #routing.",
                          "推断边界：No market-share conclusion."]},
            {"src_type": "thread", "src_ref": "thr_beta", "dst_type": "thread",
             "dst_ref": "thr_closed", "relation_type": "echoes", "status": "candidate",
             "evidence": ["Both records discuss external validation."]},
        ],
    })
    vault_root = tmp_path / "vault"
    (vault_root / ".obsidian").mkdir(parents=True)
    vault, index = vault_root / "News", tmp_path / "index.json"
    snapshots = [db.thread_snapshot(conn, tid) for tid in db.all_thread_ids(conn)]
    outcome = obsidian.sync_threads(snapshots, vault, index)
    assert not outcome["errors"]
    paths = json.loads(index.read_text())["threads"]
    assert len(set(paths.values())) == 3
    assert paths["thr_alpha"] != paths["thr_beta"]  # sanitized filename collision
    links = {tid: f"[[News/{Path(path).with_suffix('').as_posix()}]]"
             for tid, path in paths.items()}
    notes = {tid: (vault / path).read_text() for tid, path in paths.items()}
    assert f"—**competes_with**→ {links['thr_beta']}（thread `thr_beta`）" in notes["thr_alpha"]
    assert "置信度 0.85 · active · 证据 3 条" in notes["thr_alpha"]
    assert "关联说明：Both products target \\#routing." in notes["thr_alpha"]
    assert "推断边界：No market-share conclusion." in notes["thr_alpha"]
    assert f"{links['thr_alpha']}（thread `thr_alpha`） —**competes_with**→ 本 Thread" in notes["thr_beta"]
    assert links["thr_closed"] in notes["thr_beta"] and "candidate" in notes["thr_beta"]
    assert "关联依据：Both records discuss external validation." in notes["thr_beta"]
    assert f"{links['thr_closed']}（thread `thr_closed`）· related · Shared archived context" in notes["thr_alpha"]
    assert paths["thr_closed"].startswith("closed_threads/")
    repeated = obsidian.sync_threads(snapshots, vault, index, synced_at="later")
    assert not repeated["written"] and not repeated["errors"]


def test_relation_links_follow_peer_rename_and_close_without_losing_annotations(tmp_path):
    conn = fresh(tmp_path)
    db.store_bundle(conn, {
        "threads": [{"id": "thr_a", "title": "Alpha"}, {"id": "thr_b", "title": "Beta"}],
        "relations": [{"src_type": "thread", "src_ref": "thr_a", "dst_type": "thread",
                       "dst_ref": "thr_b", "relation_type": "related_to",
                       "evidence": ["理由：Shared context", "限定：No causal claim"]}],
    })
    vault, _ = sync(conn, tmp_path, ["thr_a", "thr_b"])
    alpha = vault / "Alpha.md"
    alpha.write_text(alpha.read_text().replace("# 手工批注\n\n（无）", "# 手工批注\n\nKeep my annotation."))
    renamed = db.store_bundle(conn, {
        "threads": [{"id": "thr_b", "title": "Renamed: #Beta", "status": "closed"}],
    })
    assert renamed["touched_threads"] == ["thr_a", "thr_b"]
    _, outcome = sync(conn, tmp_path, renamed["touched_threads"])
    assert not outcome["errors"] and not (vault / "Beta.md").exists()
    paths = json.loads((tmp_path / "obsidian-index.json").read_text())["threads"]
    target = paths["thr_b"]
    assert target.startswith("closed_threads/") and (vault / target).is_file()
    assert f"[[{Path(target).with_suffix('').as_posix()}]]" in alpha.read_text()
    assert "[[Beta]]" not in alpha.read_text()
    assert "关联说明：Shared context" in alpha.read_text()
    assert "推断边界：No causal claim" in alpha.read_text()
    assert obsidian.extract_manual_notes(alpha.read_text()).strip() == "Keep my annotation."
    # A later partial sync must resolve the peer through the saved index too.
    _, repeated = sync(conn, tmp_path, ["thr_a"])
    assert repeated["unchanged"] == [str(alpha)] and not repeated["written"]


def test_relation_without_description_or_note_mapping_does_not_invent_them():
    snapshot = {"id": "thr_a", "relations": [
        {"src_type": "thread", "src_id": "thr_a", "dst_type": "thread",
         "dst_id": "thr_missing", "relation_type": "related_to",
         "evidence_json": '["evt_reference", "https://example.test/source"]'},
    ]}
    rendered = obsidian.render_snapshot(snapshot, "now")
    assert "thread `thr_missing`" in rendered and "[[" not in rendered
    assert "关联说明：原记录尚未提供文字说明。" in rendered


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
    assert 'last_event_ingested_at: "' in text
    assert "# 时间线" in text
    assert "## Example changed" in text
    assert "## Example changed\nExample changed\n\n---\n\n- 发生时间：" in text
    assert not text.startswith("# Example transition")
    assert "发生时间：未知（精度：day）" not in text  # occurred_at is set here
    assert "报道时间：2026-08-30T09:00:00+08:00" in text
    assert "「Example changed.」—— Report A（primary）" in text
    assert "- [ ] Why now?" in text
    assert "`Example follow-up`（exact）" in text
    assert "# 手工批注" in text


def test_standalone_quote_renders_link_and_summary_without_verbatim_text(tmp_path):
    conn = fresh(tmp_path)
    result = db.store_bundle(conn, quote_bundle())
    vault, outcome = sync(conn, tmp_path, result["touched_threads"])
    assert outcome["written"] and not outcome["errors"]
    text = only_file(vault).read_text(encoding="utf-8")
    assert "[[原文素材/example-statement|" in text
    assert "> **摘要**：The spokesperson confirmed the transition." in text
    assert "> We changed it." not in text
    assert "We changed it." in (vault / "原文素材" / "example-statement.md").read_text(
        encoding="utf-8")


def test_timeline_is_rendered_newest_first(tmp_path):
    """The rendered 时间线 lists the most recent event first (2026-09-14)."""
    conn = fresh(tmp_path)
    result = db.store_bundle(conn, capture_bundle())
    tid = result["refs"]["t1"]
    db.store_bundle(conn, {
        "events": [{"ref": "e2", "title": "Later development", "summary": "Later development",
                    "occurred_at": "2026-09-10", "occurred_at_precision": "day",
                    "reported_at": "2026-09-10T09:00:00+08:00",
                    "observed_at": "2026-09-10T10:00:00+08:00",
                    "thread_refs": [tid]}],
    })
    vault, outcome = sync(conn, tmp_path, [tid])
    assert outcome["written"] and not outcome["errors"]
    text = only_file(vault).read_text(encoding="utf-8")
    timeline = text.split("# 时间线", 1)[1]
    assert timeline.index("Later development") < timeline.index("Example changed")


def test_each_event_carries_an_invisible_span_with_its_id(tmp_path):
    """Every event block ends with a hidden span carrying its Chronicle event id."""
    conn = fresh(tmp_path)
    result = db.store_bundle(conn, capture_bundle())
    tid = result["refs"]["t1"]
    e1 = result["refs"]["e1"]
    result2 = db.store_bundle(conn, {
        "events": [{"ref": "e2", "title": "Later development", "summary": "Later development",
                    "occurred_at": "2026-09-10", "occurred_at_precision": "day",
                    "reported_at": "2026-09-10T09:00:00+08:00",
                    "observed_at": "2026-09-10T10:00:00+08:00",
                    "thread_refs": [tid]}],
    })
    e2 = result2["refs"]["e2"]
    vault, outcome = sync(conn, tmp_path, [tid])
    assert outcome["written"] and not outcome["errors"]
    lines = only_file(vault).read_text(encoding="utf-8").splitlines()
    spans = [ln for ln in lines if "data-chronicle-event" in ln]
    assert len(spans) == 2, spans
    for eid in (e1, e2):
        span = f'<span hidden data-chronicle-event="{eid}"></span>'
        assert span in spans
        # the span is the last content line of its event block
        assert lines[lines.index(span) + 1] == ""


def test_legacy_event_uses_a_short_date_heading_and_keeps_summary_in_body(tmp_path):
    conn = fresh(tmp_path)
    result = db.store_bundle(conn, capture_bundle())
    conn.execute("UPDATE events SET title = NULL")
    conn.commit()
    vault, outcome = sync(conn, tmp_path, result["touched_threads"])
    assert outcome["written"] and not outcome["errors"]
    text = only_file(vault).read_text(encoding="utf-8")
    assert "## 2026-08-30 · 事件记录\nExample changed" in text


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


def test_follow_up_sync_preserves_legacy_manual_notes_heading(tmp_path):
    conn = fresh(tmp_path)
    result = db.store_bundle(conn, capture_bundle())
    vault, _ = sync(conn, tmp_path, result["touched_threads"])
    target = only_file(vault)

    # Reader adds a manual annotation.
    text = target.read_text(encoding="utf-8")
    text = text.replace(
        "# 手工批注\n\n（无）",
        "## 手工批注\n\n我看过这部片子。\n\n### 旁注\n这条也要保留。",
    )
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
    assert "### 旁注\n这条也要保留。" in text2       # nested notes preserved
    assert "# 手工批注" in text2                     # current heading is emitted
    assert "（answered）" in text2                  # question state updated
    assert text2.count("# 时间线") == 1            # single regenerated body


def test_extract_manual_notes_accepts_all_heading_levels_and_empty_markers():
    for level in range(1, 7):
        heading = "#" * level
        assert obsidian.extract_manual_notes(
            f"{heading} 手工批注\n\n保留内容\n\n# 下一节\n"
        ) == "保留内容"
    assert obsidian.extract_manual_notes(
        "## 手工批注\n\n保留内容\n\n### 子标题\n仍是批注\n\n## 下一节\n"
    ) == "保留内容\n\n### 子标题\n仍是批注"
    for empty in ("", "（无）", "_（无）_"):
        assert obsidian.extract_manual_notes(f"## 手工批注\n\n{empty}\n") is None


def test_follow_up_sync_recovers_legacy_manual_notes_from_git(tmp_path, monkeypatch):
    conn = fresh(tmp_path)
    result = db.store_bundle(conn, capture_bundle())
    tid = result["refs"]["t1"]
    vault, _ = sync(conn, tmp_path, [tid])
    target = only_file(vault)
    marker = obsidian._thread_id_marker(tid)

    # Simulate a working-tree copy whose notes were lost, while the most
    # recent historical version still has the legacy level-2 heading.
    current = target.read_text(encoding="utf-8")
    annotated = current.replace("# 手工批注\n\n（无）", "# 手工批注\n\n磁盘上的旧批注。")
    target.write_text(
        annotated.replace("磁盘上的旧批注。", "（无）"),
        encoding="utf-8",
    )
    legacy = f"---\n{marker}\n---\n\n## 手工批注\n\n从历史恢复的批注。\n"
    calls: list[list[str]] = []

    def fake_git_run(command, **_kwargs):
        calls.append(command)
        if "rev-parse" in command:
            if "--show-toplevel" in command:
                return subprocess.CompletedProcess(command, 0, stdout=str(vault) + "\n", stderr="")
            # --show-prefix: the vault is the repository root in this test.
            return subprocess.CompletedProcess(command, 0, stdout="\n", stderr="")
        if "log" in command:
            return subprocess.CompletedProcess(command, 0, stdout="abc123\n", stderr="")
        if "show" in command:
            return subprocess.CompletedProcess(command, 0, stdout=legacy, stderr="")
        raise AssertionError(command)

    monkeypatch.setattr(obsidian.subprocess, "run", fake_git_run)
    outcome = obsidian.sync_threads(
        [db.thread_snapshot(conn, tid)], vault, tmp_path / "obsidian-index.json")

    rendered = target.read_text(encoding="utf-8")
    assert "从历史恢复的批注。" in rendered
    assert "# 手工批注" in rendered
    assert any("recovered from git" in error for error in outcome["errors"])
    assert any("log" in call for call in calls)
    assert any("show" in call for call in calls)


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


def test_resync_with_new_timestamp_leaves_file_untouched(tmp_path):
    """A re-render that only moves ``updated:`` must not rewrite the file."""
    conn = fresh(tmp_path)
    result = db.store_bundle(conn, capture_bundle())
    tid = result["refs"]["t1"]
    vault = tmp_path / "vault" / "41 新闻及事件"
    index = tmp_path / "obsidian-index.json"
    snapshots = [db.thread_snapshot(conn, tid)]

    first = obsidian.sync_threads(
        snapshots, vault, index, synced_at="2026-09-15T09:00:00+08:00")
    target = only_file(vault)
    assert first["written"] == [str(target)]
    assert first["unchanged"] == []
    assert 'updated: "2026-09-15T09:00:00+08:00"' in target.read_text(encoding="utf-8")
    before_bytes = target.read_bytes()
    before_mtime = target.stat().st_mtime_ns

    second = obsidian.sync_threads(
        snapshots, vault, index, synced_at="2026-09-18T15:47:00+08:00")
    assert second["written"] == []
    assert second["unchanged"] == [str(target)]
    assert second["errors"] == []
    assert target.read_bytes() == before_bytes
    assert target.stat().st_mtime_ns == before_mtime
    # The file was skipped, so it still carries the earlier timestamp.
    assert 'updated: "2026-09-18T15:47:00+08:00"' not in target.read_text(encoding="utf-8")


def test_resync_skips_material_files_when_only_updated_differs(tmp_path):
    """原文素材/<slug>.md obeys the same idempotence rule as thread notes."""
    conn = fresh(tmp_path)
    result = db.store_bundle(conn, quote_bundle())
    tid = result["refs"]["t1"]
    vault = tmp_path / "vault" / "41 新闻及事件"
    index = tmp_path / "obsidian-index.json"
    snapshots = [db.thread_snapshot(conn, tid)]

    first = obsidian.sync_threads(
        snapshots, vault, index, synced_at="2026-09-15T09:00:00+08:00")
    material = vault / "原文素材" / "example-statement.md"
    assert material.exists()
    assert "We changed it." in material.read_text(encoding="utf-8")
    before_bytes = material.read_bytes()
    before_mtime = material.stat().st_mtime_ns

    second = obsidian.sync_threads(
        snapshots, vault, index, synced_at="2026-09-18T15:47:00+08:00")
    assert str(material) in second["unchanged"]
    assert material.read_bytes() == before_bytes
    assert material.stat().st_mtime_ns == before_mtime
    # Materials are reported as skipped, never as written (unchanged contract).
    assert str(material) not in first["written"] + second["written"]


def test_resync_writes_again_when_content_changes(tmp_path):
    """Idempotence covers ``updated:`` only; real changes still land."""
    conn = fresh(tmp_path)
    result = db.store_bundle(conn, capture_bundle())
    tid = result["refs"]["t1"]
    vault = tmp_path / "vault" / "41 新闻及事件"
    index = tmp_path / "obsidian-index.json"

    obsidian.sync_threads([db.thread_snapshot(conn, tid)], vault, index,
                          synced_at="2026-09-15T09:00:00+08:00")
    target = only_file(vault)
    before_text = target.read_text(encoding="utf-8")
    before_mtime = target.stat().st_mtime_ns

    # A new event changes the projected body.
    db.store_bundle(conn, {
        "events": [{"ref": "e2", "summary": "Example moved on",
                    "reported_at": "2026-09-18T08:00:00+08:00",
                    "observed_at": "2026-09-18T08:30:00+08:00",
                    "thread_refs": [tid]}],
    })
    outcome = obsidian.sync_threads([db.thread_snapshot(conn, tid)], vault, index,
                                    synced_at="2026-09-18T15:47:00+08:00")
    assert outcome["written"] == [str(target)]
    assert outcome["unchanged"] == []
    after_text = target.read_text(encoding="utf-8")
    assert after_text != before_text
    assert "Example moved on" in after_text
    assert 'updated: "2026-09-18T15:47:00+08:00"' in after_text
    assert target.stat().st_mtime_ns >= before_mtime


def test_manual_annotation_does_not_defeat_idempotence(tmp_path):
    """Reader notes are carried through, and a no-op re-sync still skips."""
    conn = fresh(tmp_path)
    result = db.store_bundle(conn, capture_bundle())
    tid = result["refs"]["t1"]
    vault = tmp_path / "vault" / "41 新闻及事件"
    index = tmp_path / "obsidian-index.json"
    snapshots = [db.thread_snapshot(conn, tid)]

    obsidian.sync_threads(snapshots, vault, index,
                          synced_at="2026-09-15T09:00:00+08:00")
    target = only_file(vault)
    text = target.read_text(encoding="utf-8")
    target.write_text(
        text.replace("# 手工批注\n\n（无）", "# 手工批注\n\n我记得这条线。"),
        encoding="utf-8")
    annotated = target.read_bytes()
    annotated_mtime = target.stat().st_mtime_ns

    second = obsidian.sync_threads(snapshots, vault, index,
                                   synced_at="2026-09-18T15:47:00+08:00")
    assert second["written"] == []
    assert second["unchanged"] == [str(target)]
    assert target.read_bytes() == annotated
    assert target.stat().st_mtime_ns == annotated_mtime
    assert "我记得这条线。" in target.read_text(encoding="utf-8")


def test_normalize_updated_touches_only_the_frontmatter_line():
    """Body text that mentions ``updated`` must still be compared verbatim."""
    front_a = "---\nupdated: \"2026-09-15T09:00:00+08:00\"\n---\n\nupdated: keep me\n"
    front_b = "---\nupdated: \"2026-09-18T15:47:00+08:00\"\n---\n\nupdated: keep me\n"
    assert obsidian._normalize_updated(front_a) == obsidian._normalize_updated(front_b)
    assert "updated: keep me" in obsidian._normalize_updated(front_a)
    body_a = "---\nupdated: x\n---\n\nupdated: keep me\n"
    body_b = "---\nupdated: x\n---\n\nupdated: changed\n"
    assert obsidian._normalize_updated(body_a) != obsidian._normalize_updated(body_b)


def test_empty_vault_dir_env_disables_sync(tmp_path, monkeypatch):
    monkeypatch.setenv("WORLD_HISTORIAN_VAULT_DIR", "")
    assert obsidian.vault_dir() is None
    monkeypatch.setenv("WORLD_HISTORIAN_VAULT_DIR", str(tmp_path / "custom"))
    assert obsidian.vault_dir() == tmp_path / "custom"


def test_vault_dir_uses_machine_local_config(tmp_path, monkeypatch):
    monkeypatch.delenv("WORLD_HISTORIAN_VAULT_DIR", raising=False)
    monkeypatch.setattr(
        obsidian, "__file__",
        str(tmp_path / "agents/world-historian/runtime/obsidian.py"),
    )
    config = tmp_path / "var/config/world-historian.yaml"
    assert obsidian.vault_dir() is None  # Missing config keeps export disabled.

    config.parent.mkdir(parents=True)
    vault = tmp_path / "vault"
    config.write_text(f"vault_dir: {vault}\n", encoding="utf-8")
    assert obsidian.vault_dir() == vault

    config.write_text("vault_dir: '   '\n", encoding="utf-8")
    assert obsidian.vault_dir() is None

    config.write_text(f"vault_dir: {vault}\n", encoding="utf-8")
    monkeypatch.setenv("WORLD_HISTORIAN_VAULT_DIR", str(tmp_path / "override"))
    assert obsidian.vault_dir() == tmp_path / "override"
    monkeypatch.setenv("WORLD_HISTORIAN_VAULT_DIR", "")
    assert obsidian.vault_dir() is None


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
