from __future__ import annotations

from pathlib import Path
import sqlite3

import pytest

from agents.librarian.runtime.store import Library, LibrarianError


MIGRATIONS = Path(__file__).resolve().parents[1] / "agents/librarian/runtime/migrations"


def test_pre_v4_digital_bindings_backfill_only_unambiguous_sources(tmp_path):
    root = tmp_path / "old-library"
    root.mkdir()
    with sqlite3.connect(root / "librarian.sqlite") as db:
        for version in range(1, 4):
            migration = next(MIGRATIONS.glob(f"{version:04d}_*.sql"))
            db.executescript(migration.read_text(encoding="utf-8"))
        for owner, source, key in (("owner_a", "shared", "a"),
                                   ("owner_b", "shared", "b"),
                                   ("owner_a", "unique", "c")):
            db.execute("INSERT INTO koodo_native_records VALUES(?,?,?,?,?,?,?,?,?)",
                       (owner, source, key, "book", "trace-" + key,
                        "sha-" + key, "active", None, None))
        db.execute("INSERT INTO weread_native_records VALUES(?,?,?,?,?,?,?,?,?)",
                   ("owner_b", "unique", "mark", "book", "trace-w",
                    "sha-w", "active", None, None))
    with Library(root) as lib:
        bindings = {(row["kind"], row["source_id"], row["owner_id"])
                    for row in lib.db.execute("SELECT * FROM digital_source_owners")}
        assert bindings == {("koodo", "unique", "owner_a"),
                            ("weread", "unique", "owner_b")}
        assert lib.db.execute("SELECT COUNT(*) FROM koodo_native_records").fetchone()[0] == 3
        with lib.transaction():
            with pytest.raises(LibrarianError) as ambiguous:
                lib.bind_digital_source("owner_a", "koodo", "shared")
            assert ambiguous.value.code == "UNAUTHORIZED"
            with pytest.raises(LibrarianError) as foreign:
                lib.bind_digital_source("owner_b", "koodo", "unique")
            assert foreign.value.code == "UNAUTHORIZED"
    with Library(root) as reopened:
        assert reopened.db.execute("SELECT COUNT(*) FROM digital_source_owners").fetchone()[0] == 2
