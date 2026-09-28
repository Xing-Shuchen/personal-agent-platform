from __future__ import annotations

import json

from agents.librarian.runtime.tests.validate_contracts import REPORT, check


def test_offline_librarian_contract_examples_match_report():
    assert check() == json.loads(REPORT.read_text(encoding="utf-8"))
