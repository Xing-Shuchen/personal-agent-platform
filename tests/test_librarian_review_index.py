from pathlib import Path

import pytest

from agents.librarian.runtime.review_index import _bookscan_run_dir


def test_bookscan_review_path_rebases_after_private_store_restore(tmp_path: Path) -> None:
    root = tmp_path / "restored"
    current = root / "bookscan-runs" / "owner-hash" / "run-fixture" / "output" / "run-001"
    current.mkdir(parents=True)
    old = tmp_path / "old-computer" / "bookscan-runs" / "owner-hash" / "run-fixture" / "output"
    report = {"run_id": "run-001", "config": {"output_dir": str(old)}}
    assert _bookscan_run_dir(root, report) == current.resolve()

    second = root / "bookscan-runs" / "other-hash" / "run-fixture" / "output" / "run-001"
    second.mkdir(parents=True)
    with pytest.raises(ValueError, match="not unique"):
        _bookscan_run_dir(root, report)
    with pytest.raises(ValueError, match="invalid"):
        _bookscan_run_dir(root, {"run_id": "../escape", "config": report["config"]})
