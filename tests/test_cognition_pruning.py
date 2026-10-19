"""Incremental pruning uses temporary vaults and deterministic embeddings."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from pap import cognition


PROJECTIONS = {
    "evidence_units": ("evidence_id",),
    "evidence_fts": ("evidence_id",),
    "evidence_embeddings": ("evidence_id",),
    "links": ("left_evidence_id",),
    "derivations": ("derived_evidence_id", "source_evidence_id"),
}
STATE_TABLES = (
    "retrieval_runs", "delivered_connections", "watch_hypotheses",
    "evidence_family_state", "cooldown_state", "candidate_rejections",
)


@pytest.fixture
def vault_index(tmp_path, monkeypatch):
    vault = tmp_path / "vault"
    vault.mkdir()
    monkeypatch.setenv("PAP_VAULT", str(vault))
    monkeypatch.setenv("PAP_CANDIDATE_RETRIEVAL_EMBEDDINGS_ENABLED", "1")
    # Exercise embedding-row deletion without loading a model or using a network.
    monkeypatch.setattr(cognition, "embedding", lambda text: (cognition.TRANSFORMER_MODEL_ID, [1.0, 0.0]))
    index = cognition.Index(cognition.default_index(vault))
    try:
        yield vault, index
    finally:
        index.close()


def write(vault: Path, name: str, text: str) -> Path:
    path = vault / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def snapshot(index, tables):
    return {table: {tuple(row) for row in index.db.execute(f"SELECT * FROM {table}")}
            for table in tables}


def units_for(index, path):
    return index.db.execute("SELECT * FROM evidence_units WHERE source_path=?", (path,)).fetchall()


def assert_no_projections(index, evidence_ids):
    for table, columns in PROJECTIONS.items():
        for row in index.db.execute(f"SELECT {','.join(columns)} FROM {table}"):
            assert evidence_ids.isdisjoint(row), (table, tuple(row))


def assert_pruned_counts(index, result, units, revisions):
    expected = {"pruned_units": units, "pruned_revisions": revisions}
    assert {key: result[key] for key in expected} == expected
    stored = index.db.execute("SELECT counts_json FROM index_generations WHERE generation_id=?",
                              (result["generation"],)).fetchone()[0]
    assert json.loads(stored) == {key: value for key, value in result.items() if key != "generation"}
    status = index.status()
    assert {key: status[key] for key in expected} == expected


def seed_state(index, unit, generation):
    evidence_id, family = unit["evidence_id"], unit["evidence_family_id"]
    index.db.execute("INSERT INTO retrieval_runs VALUES(?,?,?,?)",
                     ("retrieval-test", generation, json.dumps({"evidence_id": evidence_id}), cognition.now()))
    index.db.execute("INSERT INTO delivered_connections VALUES(?,?,?,?,?)",
                     ("pair-test", "delivery-test", None, cognition.now(), "{}"))
    index.db.execute("INSERT INTO watch_hypotheses VALUES(?,?,?,?,?,?)",
                     ("watch-test", "open", evidence_id, "evidence", "{}", cognition.now()))
    index.db.execute("INSERT INTO evidence_family_state(family_id,explore_count,updated_at) VALUES(?,?,?)",
                     (family, 2, cognition.now()))
    index.db.commit()
    index.record_rejection(run_id="retrieval-test", agent="serendipity", candidate_id="candidate-test",
                           evidence_ids=[evidence_id], family_ids=[family, "other-family"],
                           recall_channels=["lexical"], reason_code="OBVIOUS_CONNECTION",
                           anchor_refs=[evidence_id])
    assert all(snapshot(index, STATE_TABLES).values())


def test_edit_prunes_only_superseded_projections_and_preserves_state(vault_index):
    vault, index = vault_index
    changed = write(vault, "1Project/changed.md", "# Weekly\noldalpha [[Target]]\n# Monthly\noldbeta [[Other]]\n")
    write(vault, "2Area/stable.md", "# Weekly\nsteady [[Unchanged]]\n")
    first = index.build(vault)
    assert_pruned_counts(index, first, 0, 0)
    old_units = units_for(index, "1Project/changed.md")
    old_ids = {row["evidence_id"] for row in old_units}
    stable_unit = units_for(index, "2Area/stable.md")[0]
    stable_id = stable_unit["evidence_id"]
    # Also cover a derivation whose source (rather than derived endpoint) is stale.
    index.db.execute("INSERT INTO derivations VALUES(?,?,?,?)",
                     (stable_id, old_units[0]["evidence_id"], "uses_evidence", first["generation"]))
    # Every projection starts populated, including multiple embedding cache keys.
    index.db.execute("INSERT INTO evidence_embeddings VALUES(?,?,?,?,?,?)",
                     (old_units[0]["evidence_id"], "test-other-model", "other-hash", 2, "[0,1]", cognition.now()))
    index.db.commit()
    seed_state(index, old_units[0], first["generation"])
    state = snapshot(index, STATE_TABLES)
    projections = snapshot(index, PROJECTIONS)
    assert all(projections.values())
    stable_rows = {table: {row for row in rows if row[0] == stable_id and not old_ids.intersection(row)}
                   for table, rows in projections.items()}
    first_generation = snapshot(index, ("index_generations",))["index_generations"]

    changed.write_text("# Weekly\nnewalpha [[Target]]\n# Monthly\nnewbeta [[Other]]\n", encoding="utf-8")
    result = index.build(vault)

    assert_pruned_counts(index, result, 2, 1)
    assert_no_projections(index, old_ids)
    new_units = units_for(index, "1Project/changed.md")
    assert len(new_units) == 2
    assert {row["evidence_revision"] for row in new_units} == {2}
    current = snapshot(index, PROJECTIONS)
    for table, rows in stable_rows.items():
        assert rows <= current[table]
        assert len(current[table]) == 3
    for unit in new_units:
        evidence_id = unit["evidence_id"]
        assert index.get(evidence_id)["active"] == 1
        for table in PROJECTIONS:
            assert any(row[0] == evidence_id for row in current[table])
    assert index.search("newalpha") and not index.search("oldalpha")
    assert {(row[0], row[1]) for row in index.db.execute("SELECT document_id,revision FROM document_revisions")} == {
        (new_units[0]["document_id"], 2), (stable_unit["document_id"], 1),
    }
    assert index.db.execute("SELECT count(*) FROM documents WHERE deleted=0").fetchone()[0] == 2
    assert snapshot(index, STATE_TABLES) == state
    assert first_generation <= snapshot(index, ("index_generations",))["index_generations"]

    repeated = index.build(vault)
    assert repeated["skipped"] == 2
    assert_pruned_counts(index, repeated, 0, 0)
    assert snapshot(index, PROJECTIONS) == current
    assert snapshot(index, STATE_TABLES) == state


@pytest.mark.parametrize("keep_other_document", [False, True])
def test_deleted_document_prunes_all_its_evidence_but_keeps_current_revision(vault_index, keep_other_document):
    vault, index = vault_index
    deleted = write(vault, "deleted.md", "# Weekly\nobsolete [[Target]]\n")
    if keep_other_document:
        write(vault, "stable.md", "# Monthly\nsteady [[Other]]\n")
    first = index.build(vault)
    old_unit = units_for(index, "deleted.md")[0]
    seed_state(index, old_unit, first["generation"])
    state = snapshot(index, STATE_TABLES)
    projections = snapshot(index, PROJECTIONS)
    deleted.unlink()

    result = index.build(vault)

    assert_pruned_counts(index, result, 1, 0)
    assert_no_projections(index, {old_unit["evidence_id"]})
    assert not index.search("obsolete")
    document = index.db.execute("SELECT * FROM documents WHERE document_id=?", (old_unit["document_id"],)).fetchone()
    assert document["deleted"] == 1 and document["current_revision"] == 1
    assert index.db.execute("SELECT revision FROM document_revisions WHERE document_id=?",
                            (old_unit["document_id"],)).fetchone()[0] == 1
    current = snapshot(index, PROJECTIONS)
    for table, rows in projections.items():
        assert current[table] == {row for row in rows if row[0] != old_unit["evidence_id"]}
    assert snapshot(index, STATE_TABLES) == state
    assert_pruned_counts(index, index.build(vault), 0, 0)
    assert snapshot(index, PROJECTIONS) == current


def test_unchanged_build_prunes_legacy_inactive_revisions(vault_index):
    vault, index = vault_index
    note = write(vault, "note.md", "# Weekly\nlegacy [[Target]]\n")
    index.build(vault)
    old_unit = units_for(index, "note.md")[0]
    # Simulate a pre-upgrade index retaining several superseded revisions.
    prune = index._prune_superseded
    index._prune_superseded = lambda: {"pruned_units": 0, "pruned_revisions": 0}
    for text in ("intermediate", "current"):
        note.write_text(f"# Weekly\n{text} [[Target]]\n", encoding="utf-8")
        index.build(vault)
    index._prune_superseded = prune
    assert len(units_for(index, "note.md")) == 3
    # Include stale FTS rows that would normally already have been removed.
    index.db.execute("INSERT INTO evidence_fts VALUES(?,?,?,?)",
                     (old_unit["evidence_id"], old_unit["text"], old_unit["heading_path"], "note.md"))
    index.db.commit()

    result = index.build(vault)

    assert result["skipped"] == 1
    assert_pruned_counts(index, result, 2, 2)
    assert_no_projections(index, {old_unit["evidence_id"], old_unit["evidence_family_id"] + ":r2"})
    assert {row["evidence_revision"] for row in units_for(index, "note.md")} == {3}
    assert_pruned_counts(index, index.build(vault), 0, 0)


def test_legacy_tombstone_is_pruned_on_an_unchanged_build(vault_index):
    vault, index = vault_index
    note = write(vault, "note.md", "# Weekly\nlegacy [[Target]]\n")
    index.build(vault)
    unit = units_for(index, "note.md")[0]
    note.unlink()
    index.db.execute("UPDATE documents SET deleted=1")
    index.db.execute("UPDATE evidence_units SET active=0")
    index.db.commit()

    assert_pruned_counts(index, index.build(vault), 1, 0)

    assert_no_projections(index, {unit["evidence_id"]})
    assert_pruned_counts(index, index.build(vault), 0, 0)


def test_pruning_uses_revision_order_rather_than_active_flag(vault_index):
    vault, index = vault_index
    note = write(vault, "note.md", "# Weekly\nolder [[Target]]\n")
    index.build(vault)
    old_unit = units_for(index, "note.md")[0]
    # Simulate old retained rows, including an incorrectly active old revision.
    prune = index._prune_superseded
    index._prune_superseded = lambda: {"pruned_units": 0, "pruned_revisions": 0}
    note.write_text("# Weekly\ncurrent [[Other]]\n", encoding="utf-8")
    index.build(vault)
    index._prune_superseded = prune
    index.db.execute("UPDATE evidence_units SET active=CASE WHEN evidence_revision=1 THEN 1 ELSE 0 END")
    index.db.commit()
    current_unit = next(row for row in units_for(index, "note.md") if row["evidence_revision"] == 2)
    projections = snapshot(index, PROJECTIONS)

    assert_pruned_counts(index, index.build(vault), 1, 1)

    assert_no_projections(index, {old_unit["evidence_id"]})
    current = snapshot(index, PROJECTIONS)
    for table, rows in projections.items():
        assert current[table] == {row for row in rows if row[0] == current_unit["evidence_id"]}
    assert_pruned_counts(index, index.build(vault), 0, 0)


@pytest.mark.parametrize("change", ["edit", "delete"])
def test_failure_after_pruning_rolls_back_all_projections(vault_index, monkeypatch, change):
    vault, index = vault_index
    note = write(vault, "note.md", "# Weekly\noriginal [[Target]]\n")
    first = index.build(vault)
    before = snapshot(index, (*PROJECTIONS, "documents", "document_revisions"))
    if change == "edit":
        note.write_text("# Weekly\nreplacement [[Other]]\n", encoding="utf-8")
    else:
        note.unlink()
    ensure_embeddings = index._ensure_embeddings

    def fail_after_pruning():
        assert_no_projections(index, {next(iter(before["evidence_units"]))[0]})
        raise RuntimeError("injected failure after pruning")

    monkeypatch.setattr(index, "_ensure_embeddings", fail_after_pruning)
    with pytest.raises(RuntimeError, match="injected failure after pruning"):
        index.build(vault)

    assert snapshot(index, before) == before
    assert index.complete_generation() == first["generation"]
    assert index.status()["failed_generations"] == 1
    assert_pruned_counts(index, first, 0, 0)
    # Retry on the same connection also verifies temporary-table cleanup.
    monkeypatch.setattr(index, "_ensure_embeddings", ensure_embeddings)
    assert_pruned_counts(index, index.build(vault), 1, int(change == "edit"))


def test_identical_document_restored_after_deletion_recreates_evidence(vault_index):
    vault, index = vault_index
    text = "# Weekly\nrestored [[Target]]\n"
    note = write(vault, "note.md", text)
    index.build(vault)
    old_unit = units_for(index, "note.md")[0]
    note.unlink()
    assert_pruned_counts(index, index.build(vault), 1, 0)
    note.write_text(text, encoding="utf-8")

    result = index.build(vault)

    assert result["skipped"] == 0
    assert_pruned_counts(index, result, 0, 1)
    restored = units_for(index, "note.md")[0]
    assert restored["document_id"] == old_unit["document_id"]
    assert restored["evidence_revision"] == 2
    assert index.search("restored")[0]["evidence_id"] == restored["evidence_id"]
    assert all(snapshot(index, PROJECTIONS).values())
    assert_pruned_counts(index, index.build(vault), 0, 0)


def test_status_without_completed_generation_defaults_pruning_counts_to_zero(vault_index):
    _, index = vault_index
    assert index.status()["pruned_units"] == 0
    assert index.status()["pruned_revisions"] == 0
    index.db.execute("INSERT INTO index_generations(started_at,status,scanner_version,schema_version) VALUES(?,?,?,?)",
                     (cognition.now(), "COMPLETE", cognition.SCANNER_VERSION, cognition.SCHEMA_VERSION))
    index.db.commit()
    assert index.status()["pruned_units"] == 0
    assert index.status()["pruned_revisions"] == 0
