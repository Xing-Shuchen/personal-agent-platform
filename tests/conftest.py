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


def load_runtime_module(module_name: str):
    """Load a runtime module by stem from agents/world-historian/runtime/."""
    spec = importlib.util.spec_from_file_location(
        f"world_historian_runtime_{module_name}",
        REPO / f"agents/world-historian/runtime/{module_name}.py",
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load World Historian runtime module {module_name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_runtime_db():
    return load_runtime_module("db")


@pytest.fixture
def chronicle_db():
    module = load_runtime_db()
    return module
