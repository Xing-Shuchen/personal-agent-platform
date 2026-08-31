"""Shared test fixtures.

``agents/world-historian/`` contains a hyphen, so its runtime modules cannot
be imported as a regular package. Load ``db.py`` directly by file path.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

import pytest

REPO = Path(__file__).resolve().parents[1]


def load_runtime_db():
    spec = importlib.util.spec_from_file_location(
        "world_historian_runtime_db",
        REPO / "agents/world-historian/runtime/db.py",
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load World Historian runtime db module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def chronicle_db():
    module = load_runtime_db()
    return module
