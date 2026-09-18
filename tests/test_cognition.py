from __future__ import annotations

import json
from pathlib import Path

from pap.cognition import Index, classify, parse_markdown, segments


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
