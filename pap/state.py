"""Durable local state helpers (under ``var/state/``).

All writes are atomic (tmp file + ``os.replace``); the append-only decision
log is JSONL so it stays inspectable with plain text tools.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def default_state() -> dict[str, Any]:
    return {"version": 1, "agents": {}}


def load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return default_state()
    data = json.loads(path.read_text(encoding="utf-8"))
    # Forward-fill defaults so older state files keep working.
    state = default_state()
    if isinstance(data, dict):
        for k, v in data.items():
            if k in state:
                state[k] = v
    return state


def save_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = _mkstemp(path)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2, sort_keys=True)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def append_jsonl(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(record, ensure_ascii=False, sort_keys=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out


def _mkstemp(path: Path) -> tuple[int, str]:
    import tempfile

    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=path.name, suffix=".tmp")
    return fd, tmp
