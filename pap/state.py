"""Durable local state helpers (under ``var/state/``).

All writes are atomic (tmp file + ``os.replace``); the append-only decision
log is JSONL so it stays inspectable with plain text tools.
"""

from __future__ import annotations

import fcntl
import json
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator


def load_json(path: Path, default: dict[str, Any] | None = None) -> dict[str, Any]:
    """Load a JSON object, returning a shallow copy of *default* if absent."""
    if not path.exists():
        return dict(default or {})
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected a JSON object")
    return data


def save_json(path: Path, data: dict[str, Any]) -> None:
    """Atomically write an arbitrary JSON object."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = _mkstemp(path)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=True)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


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
    save_json(path, state)


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
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            # A truncated line (a writer killed mid-append, a full disk) must
            # not permanently break `pap runs` / `pap artifact list`; the rest
            # of the append-only log stays readable.
            continue
        if isinstance(record, dict):
            out.append(record)
    return out


@contextmanager
def file_lock(path: Path) -> Iterator[None]:
    """Exclusive flock beside *path* for read-modify-write state cycles.

    Writers that load, mutate, and atomically save a shared JSON state file
    (gate decisions, dismissed topics) must hold this lock, or a concurrent
    writer's update is silently lost.
    """
    lock_path = path.with_suffix(path.suffix + ".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with open(lock_path, "a+", encoding="utf-8") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def _mkstemp(path: Path) -> tuple[int, str]:
    import tempfile

    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=path.name, suffix=".tmp")
    return fd, tmp
