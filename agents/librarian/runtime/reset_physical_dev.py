"""One-off backed-up development reset of derived physical reading results.

This intentionally removes old physical extraction history from the active
Library. It is not a normal correction operation; use only for an explicitly
requested full rebuild, with the Gateway stopped and a separate backup path.
"""
from __future__ import annotations

import argparse
import fcntl
import json
import shutil
import sqlite3
from contextlib import ExitStack
from pathlib import Path

from docs.audits.librarian_object_integrity import SIDECARS, audit, object_refs

from .store import Library, LibrarianError


def _tables(db: sqlite3.Connection) -> set[str]:
    return {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}


def _referenced_objects(db: sqlite3.Connection) -> set[str]:
    keys = set()
    for (body,) in db.execute("SELECT body FROM records"):
        keys.update(ref["object_key"] for ref in object_refs(json.loads(body)))
    tables = _tables(db)
    for table, field in SIDECARS:
        if table in tables:
            for (raw,) in db.execute(f"SELECT {field} FROM {table} WHERE {field} IS NOT NULL"):
                keys.update(ref["object_key"] for ref in object_refs(json.loads(raw)))
    return keys


def reset(root: Path, owner: str, backup: Path, expected_captures: int,
          vault_note: Path | None = None) -> dict:
    root, backup = root.resolve(), backup.resolve()
    if not owner or not root.is_dir() or backup.exists() or backup.is_relative_to(root):
        raise ValueError("valid root, owner and separate unused backup directory required")
    if not (root / "librarian.sqlite").is_file():
        raise FileNotFoundError(root / "librarian.sqlite")
    note_bytes = None
    if vault_note is not None and vault_note.is_file():
        note_bytes = vault_note.read_bytes()
        if (b"doc_type: physical-highlights-notes" not in note_bytes or
                b"data-librarian-batch=" not in note_bytes):
            raise ValueError("Vault note is not a generated physical Librarian note")
    with ExitStack() as stack:
        for name in ("physical-worker.lock", "digital-worker.lock"):
            handle = stack.enter_context((root / name).open("a+b"))
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with Library(root) as lib:
            captures = lib.db.execute(
                "SELECT COUNT(*) FROM records WHERE owner_id=? AND model='PageCapture' AND current=1",
                (owner,)).fetchone()[0]
            if captures != expected_captures:
                raise LibrarianError("REVISION_CONFLICT", "capture count changed before reset")
            before = audit(root)
            if (before["missing_paths"] or before["orphan_files"] or
                    before["invalid_json"] or before["asset_status"].get("ok", 0) !=
                    before["unique_assets"]):
                raise LibrarianError("OBJECT_STORE_UNAVAILABLE", "object audit failed before reset")
            backup.mkdir(parents=True)
            shutil.copytree(root, backup / "state", ignore=shutil.ignore_patterns(
                "librarian.sqlite", "librarian.sqlite-wal", "librarian.sqlite-shm"))
            destination = sqlite3.connect(backup / "state" / "librarian.sqlite")
            try:
                lib.db.backup(destination)
            finally:
                destination.close()
            if note_bytes is not None:
                (backup / "vault-note.md").write_bytes(note_bytes)

            physical_ids = {row[0] for row in lib.db.execute(
                "SELECT DISTINCT id FROM records WHERE owner_id=? AND model='ReadingTrace' "
                "AND json_extract(body,'$.medium')='physical'", (owner,))}
            tables = _tables(lib.db)
            candidates = [json.loads(row[0]) for row in lib.db.execute(
                "SELECT body FROM records WHERE owner_id=? AND model='KnowledgeCandidate'",
                (owner,))]
            if any(ref["trace_id"] in physical_ids for candidate in candidates
                   for ref in candidate["source_trace_refs"]):
                raise LibrarianError("DEPENDENCY_CONFLICT", "physical knowledge candidate exists")
            relation_ids = {row[0] for row in lib.db.execute(
                "SELECT DISTINCT id FROM records WHERE owner_id=? AND model='TraceRelation' "
                "AND json_extract(body,'$.source_trace_ref.trace_id') IN ("
                "SELECT id FROM records WHERE owner_id=? AND model='ReadingTrace' "
                "AND json_extract(body,'$.medium')='physical')", (owner, owner))}
            counts = {}
            with lib.transaction():
                lib.db.execute("DROP TRIGGER evidence_undeletable")
                for model in ("ProcessingRun", "PageObservation", "CaptureResolution"):
                    counts[model] = lib.db.execute(
                        "SELECT COUNT(*) FROM records WHERE owner_id=? AND model=?",
                        (owner, model)).fetchone()[0]
                    lib.db.execute("DELETE FROM records WHERE owner_id=? AND model=?",
                                   (owner, model))
                counts["ReadingTrace"] = lib.db.execute(
                    "SELECT COUNT(*) FROM records WHERE owner_id=? AND model='ReadingTrace' "
                    "AND json_extract(body,'$.medium')='physical'", (owner,)).fetchone()[0]
                lib.db.execute("DELETE FROM records WHERE owner_id=? AND model='ReadingTrace' "
                               "AND json_extract(body,'$.medium')='physical'", (owner,))
                for relation_id in relation_ids:
                    lib.db.execute("DELETE FROM records WHERE owner_id=? AND model='TraceRelation' AND id=?",
                                   (owner, relation_id))
                counts["TraceRelation"] = len(relation_ids)
                lib.db.execute("DELETE FROM trace_index WHERE owner_id=? AND medium='physical'", (owner,))
                lib.db.execute("DELETE FROM extractor_attempts WHERE owner_id=?", (owner,))
                lib.db.execute("DELETE FROM extractor_derivatives WHERE owner_id=?", (owner,))
                for table in ("gateway_review_decisions", "gateway_review_finalizations"):
                    if table in tables:
                        lib.db.execute(f"DELETE FROM {table} WHERE owner_id=?", (owner,))
                lib.db.execute("DELETE FROM outbox WHERE owner_id=? AND "
                               "event_type='reading.capture.processed'", (owner,))
                for trace_id in physical_ids:
                    lib.db.execute("DELETE FROM outbox WHERE owner_id=? AND "
                                   "event_type IN ('reading.trace.created','reading.trace.corrected') "
                                   "AND json_extract(body,'$.payload.trace_id')=?",
                                   (owner, trace_id))
                lib.db.execute("DELETE FROM consumer_events WHERE owner_id=? AND event_id NOT IN "
                               "(SELECT event_id FROM outbox WHERE owner_id=?)", (owner, owner))
                lib.db.execute("CREATE TRIGGER evidence_undeletable BEFORE DELETE ON records "
                               "WHEN OLD.model IN ('PageCapture', 'PageObservation') "
                               "BEGIN SELECT RAISE(ABORT, 'immutable evidence'); END")
            refs = _referenced_objects(lib.db)
            removed_objects = 0
            for path in (root / "objects").rglob("*"):
                if path.is_file() and str(path.relative_to(root)) not in refs:
                    path.unlink()
                    removed_objects += 1
        for name in ("batch-status", "notifications", "reconciliations",
                     "delivery-evidence", "bookscan-runs"):
            path = root / name
            if path.is_dir():
                shutil.rmtree(path)
                path.mkdir()
        for path in root.glob("worker-*.log"):
            path.unlink()
        if note_bytes is not None:
            vault_note.unlink()
    after = audit(root)
    if after["missing_paths"] or after["orphan_files"] or after["invalid_json"]:
        raise LibrarianError("OBJECT_STORE_UNAVAILABLE", "object audit failed after reset")
    return {"captures_retained": captures, "records_removed": counts,
            "objects_removed": removed_objects, "backup": str(backup),
            "remaining_assets": after["unique_assets"]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--owner", required=True)
    parser.add_argument("--backup", type=Path, required=True)
    parser.add_argument("--expected-captures", type=int, required=True)
    parser.add_argument("--vault-note", type=Path)
    args = parser.parse_args()
    print(json.dumps(reset(args.root, args.owner, args.backup,
                           args.expected_captures, args.vault_note), ensure_ascii=False))


if __name__ == "__main__":
    main()
