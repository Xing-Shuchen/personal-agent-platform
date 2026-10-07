from __future__ import annotations

import json
from pathlib import Path

import pytest

from pap.cognition import Index, classify, main, parse_markdown, segments
from paplog import observe


def write(vault: Path, relative: str, body: str) -> Path:
    path = vault / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


def test_provenance_and_fts_are_conservative(tmp_path: Path):
    vault = tmp_path / "vault"
    write(vault, "Dairies/2026/day.md", "---\ncreated: 2026-01-02\n---\n# 对影成\nknown insight.\n")
    write(vault, "Clippings/web.md", "# Web\nexternal article content.\n")
    index = Index(vault / ".index/cognition/cognition.sqlite3")
    index.build(vault)
    own = index.search("insight")[0]; external = index.search("article")[0]
    assert index.get(own["evidence_id"])["already_synthesized"] == 1
    ext = index.get(external["evidence_id"])
    assert ext["voice"] == "external"
    assert ext["field_provenance"]["permissions"]["supports_user_belief"] == 0
    assert ext["requires_source_verification"] == 1
    index.close()


def test_incremental_rename_edit_delete_and_no_private_status_text(tmp_path: Path):
    vault = tmp_path / "vault"; old = write(vault, "1Project/a.md", "# A\nalpha\n")
    index = Index(vault / ".index/cognition/cognition.sqlite3")
    one = index.build(vault); first = index.search("alpha")[0]["evidence_id"]
    two = index.build(vault); assert two["skipped"] == 1
    new = vault / "1Project/b.md"; old.rename(new)
    index.build(vault); assert index.search("alpha")[0]["evidence_id"].split(":")[0] == first.split(":")[0]
    new.write_text("# A\nbeta\n", encoding="utf-8")
    index.build(vault); assert not index.search("alpha") and index.search("beta")
    new.unlink(); index.build(vault); assert not index.search("beta")
    assert "beta" not in json.dumps(index.status())
    index.close()


def test_missing_vault_preserves_existing_index(tmp_path: Path):
    vault = tmp_path / "vault"
    write(vault, "1Project/a.md", "# A\nalpha\n")
    index = Index(tmp_path / "cognition.sqlite3")
    index.build(vault)
    first = index.search("alpha")
    vault.rename(tmp_path / "moved-vault")

    with pytest.raises(FileNotFoundError, match="Vault directory unavailable"):
        index.build(vault)

    assert index.search("alpha") == first
    index.close()


def test_markdown_boundaries_and_conservative_source_classes():
    meta, body, base = parse_markdown("---\ntype: note\n---\n# One\n> quote\n\n```py\nx=1\n```\n\n|a|b|\n|-|-|\n# Two\n- item [[Target]]\n")
    units = list(segments(body, base))
    assert meta["type"] == "note" and len(units) == 2
    assert "```py" in units[0].text and "|a|b|" in units[0].text
    assert units[1].heading == "Two" and units[1].start < units[1].end
    assert classify("Clippings/a.md", {}, "")["voice"] == "external"
    assert classify("2Area/WeRead Notes/a.md", {}, "")["origin_type"] == "plugin_highlight"
    assert classify("印象笔记/notes/a.md", {"source": "yinxiang"}, "")["voice"] == "unknown"
    assert classify("2Area/41 新闻及事件/原文素材/a.md", {"type": "source-material"}, "")["requires_source_verification"] == 1


def test_typed_adapters_lineage_and_replayable_shadow_packs(tmp_path: Path):
    vault = tmp_path / "vault"
    write(vault, "Dairies/2026/day.md", "# 对影成\nshared mechanism\n# 大事记\nproject constraint\n")
    write(vault, "2Area/WeRead Notes/book.md", "# 高亮划线\nshared mechanism\n# 划线评论\nmy commentary\n")
    write(vault, "2Area/41 新闻及事件/thread.md", "---\nthread_id: thread-1\n---\n# 事件\nshared mechanism update\n# 开放问题\nproject constraint\n")
    index = Index(vault / ".index/cognition/cognition.sqlite3")
    index.build(vault)
    daily = index.search("shared", source_type="diary")[0]
    assert index.get(daily["evidence_id"])["already_synthesized"] == 1
    comment = index.search("commentary", source_type="weread")[0]
    assert index.get(comment["evidence_id"])["voice"] == "self"
    pack_a = index.shadow_pack("serendipity", "stable-run")
    pack_b = index.shadow_pack("serendipity", "stable-run")
    assert pack_a["pack_hash"] == pack_b["pack_hash"] and len(pack_a["candidates"]) <= 8
    intel = index.shadow_pack("intelligence", "stable-intelligence")
    assert intel["schema"] == "intelligence.context-pack.v1" and len(intel["world_deltas"]) <= 10
    index.close()


def test_shadow_pack_write_emits_content_free_artifact_event(tmp_path: Path, capsys):
    vault = tmp_path / "vault"
    write(vault, "Dairies/2026/day.md", "# Note\nshared mechanism\n")
    index = Index(vault / ".index/cognition/cognition.sqlite3")
    index.build(vault)
    index.close()
    observe.configure(tmp_path / "ledger")
    assert main(["--vault", str(vault), "shadow", "serendipity", "--run-id", "shadow-test"]) == 0
    capsys.readouterr()
    event = observe.get_ledger().query(event="pap.context_pack.created")[0]
    assert event["subject"]["id"] == "shadow-test"
    assert event["attributes"]["pack_hash"].startswith("sha256:")
    assert event["attributes"]["bytes"] > 0
    assert "candidates" not in event["attributes"]


def test_index_build_emits_operation_when_pap_runtime_is_explicit(tmp_path: Path, monkeypatch):
    vault = tmp_path / "vault"
    write(vault, "1Project/a.md", "# A\nalpha\n")
    ledger = observe.configure(tmp_path / "ledger")
    monkeypatch.setenv("PAP_RUN_ID", "run-index")
    index = Index(vault / ".index/cognition/cognition.sqlite3")
    index.build(vault)
    index.close()
    events = ledger.query(event="pap.cognition.index")
    assert [event["phase"] for event in events] == ["started", "completed"]
    assert all(event["execution"]["run_id"] == "run-index" for event in events)


def test_index_reads_emit_database_read_actions_when_pap_runtime_is_explicit(tmp_path: Path, monkeypatch):
    vault = tmp_path / "vault"
    write(vault, "1Project/a.md", "# A\nalpha\n")
    ledger = observe.configure(tmp_path / "ledger")
    monkeypatch.setenv("PAP_OBSERVABILITY_DIR", str(tmp_path / "ledger"))
    index = Index(vault / ".index/cognition/cognition.sqlite3")
    index.build(vault)
    index.search("alpha")
    index.close()
    events = ledger.query(event="pap.database.read")
    assert events and {event["phase"] for event in events} == {"started", "completed"}
    reads = ledger.query(event="pap.filesystem.read")
    assert reads and {event["phase"] for event in reads} == {"started", "completed"}
