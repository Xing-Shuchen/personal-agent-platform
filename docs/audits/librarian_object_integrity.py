"""Read-only inventory of Librarian's referenced private object files."""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from collections import Counter
from pathlib import Path
from typing import Any


SIDECARS = (
    ("extractor_attempts", "raw_asset"),
    ("extractor_derivatives", "derivative"),
    ("koodo_native_records", "pending_asset"),
    ("weread_native_records", "pending_asset"),
)


def object_refs(value: Any):
    if isinstance(value, dict):
        if {"object_key", "sha256", "byte_size"} <= value.keys():
            yield value
        else:
            for item in value.values():
                yield from object_refs(item)
    elif isinstance(value, list):
        for item in value:
            yield from object_refs(item)


def file_status(root: Path, asset: dict[str, Any]) -> str:
    objects = root / "objects"
    key = asset["object_key"]
    if not isinstance(key, str) or Path(key).is_absolute() or objects.is_symlink():
        return "unsafe_path"
    path = root / key
    if path.is_symlink() or not path.resolve().is_relative_to(objects.resolve()):
        return "unsafe_path"
    if not path.is_file():
        return "missing"
    digest = hashlib.sha256()
    size = 0
    try:
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
                size += len(block)
    except OSError:
        return "unreadable"
    return "ok" if size == asset["byte_size"] and digest.hexdigest() == asset["sha256"] else "corrupt"


def audit(root: Path) -> dict[str, Any]:
    root = root.resolve()
    db_path = root / "librarian.sqlite"
    db = sqlite3.connect(db_path.as_uri() + "?mode=ro", uri=True)
    try:
        db.execute("PRAGMA query_only=ON")
        by_source: Counter[str] = Counter()
        assets: dict[tuple[str, str, int], dict[str, Any]] = {}
        invalid_json = 0

        def collect(raw: str, source: str) -> None:
            nonlocal invalid_json
            try:
                value = json.loads(raw)
            except json.JSONDecodeError:
                invalid_json += 1
                return
            for asset in object_refs(value):
                by_source[source] += 1
                key = (asset["object_key"], asset["sha256"], asset["byte_size"])
                assets[key] = asset

        for model, body in db.execute("SELECT model,body FROM records"):
            collect(body, model)
        tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        for table, column in SIDECARS:
            if table in tables:
                for (raw,) in db.execute(f"SELECT {column} FROM {table} WHERE {column} IS NOT NULL"):
                    collect(raw, table)

        statuses = Counter(file_status(root, asset) for asset in assets.values())
        paths = {key[0] for key in assets}
        files = {str(path.relative_to(root)) for path in (root / "objects").rglob("*")
                 if path.is_file() or path.is_symlink()}
        result = {
            "references": sum(by_source.values()), "unique_assets": len(assets),
            "by_source": dict(sorted(by_source.items())),
            "asset_status": dict(sorted(statuses.items())),
            "missing_paths": len(paths - files), "orphan_files": len(files - paths),
            "invalid_json": invalid_json,
        }
        return result
    finally:
        db.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    result = audit(parser.parse_args().root)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if (result["asset_status"].get("ok", 0) == result["unique_assets"]
                 and not result["missing_paths"] and not result["orphan_files"]
                 and not result["invalid_json"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
