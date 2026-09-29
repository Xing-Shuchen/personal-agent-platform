"""Every Gateway subprocess returns a complete, redacted error contract."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from agents.librarian.runtime.gateway_errors import error_result
from agents.librarian.runtime.store import LibrarianError, validate


BRIDGES = (
    "gateway_bridge", "gateway_search", "gateway_session", "gateway_evidence",
    "gateway_review", "gateway_review_decision", "gateway_review_finalize",
)


@pytest.mark.parametrize("bridge", BRIDGES)
def test_bridge_rejects_malformed_json_with_full_error_result(
        bridge: str, tmp_path: Path) -> None:
    completed = subprocess.run(
        [sys.executable, "-m", f"agents.librarian.runtime.{bridge}",
         "--root", str(tmp_path / "absent")],
        input="{invalid", text=True, capture_output=True, check=False)
    assert completed.returncode == 2
    result = json.loads(completed.stdout)["error"]
    validate("ErrorResult", result)
    assert result["code"] == "VALIDATION_FAILED"
    assert result["stage"].startswith("gateway.")
    assert result["retryable"] is False
    assert result["details"] == {}
    assert not (tmp_path / "absent").exists()


def test_bridge_error_redacts_exception_text_and_preserves_review_code() -> None:
    error = LibrarianError("RECONCILIATION_REQUIRED", "secret token and private page")
    result = error_result(error, "gateway.review_finalize")
    validate("ErrorResult", result)
    assert result["code"] == "RECONCILIATION_REQUIRED"
    assert "secret" not in json.dumps(result)
    assert result["retryable"] is False
    unexpected = error_result(RuntimeError("private path"), "gateway.search")
    validate("ErrorResult", unexpected)
    assert unexpected["code"] == "BRIDGE_FAILED"
    assert "private" not in json.dumps(unexpected)
