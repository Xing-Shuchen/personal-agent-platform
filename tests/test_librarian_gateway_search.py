from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from agents.librarian.runtime.digital import ingest_export
from agents.librarian.runtime.gateway_search import search_inbound
from agents.librarian.runtime.store import Library, LibrarianError


EXPORT = '''---
bookId: "search-bridge-book"
---
> [!abstract] Search Bridge Book
# 高亮划线
## One
> 📌 Weber and Parsons
> ⏱ 2026-01-01 12:00:00 ^bridge-mark
'''.encode()


def test_gateway_search_reads_only_mapped_owner_scope(tmp_path: Path):
    with Library(tmp_path) as lib:
        trace = ingest_export(lib, "owner_a", "weread", "fixture.md", EXPORT)[0]
        result = search_inbound(lib, {"owner_id": "owner_a", "query": "Parsons"})
        assert [hit["trace_id"] for hit in result["hits"]] == [trace["id"]]
        assert result["hits"][0]["content"]["printed_text"]["text"] == "Weber and Parsons"
        assert search_inbound(lib, {"owner_id": "owner_b", "query": "Parsons"})["hits"] == []
        for message in ({"owner_id": "owner_a", "query": ""},
                        {"owner_id": "owner_a", "query": "Parsons", "limit": 100},
                        {"owner_id": "owner_a", "query": "x" * 257}):
            with pytest.raises(LibrarianError) as error:
                search_inbound(lib, message)
            assert error.value.code == "VALIDATION_FAILED"


def test_gateway_search_cli_stdin_protocol(tmp_path: Path):
    with Library(tmp_path) as lib:
        ingest_export(lib, "owner_a", "weread", "fixture.md", EXPORT)
    result = subprocess.run(
        [sys.executable, "-m", "agents.librarian.runtime.gateway_search",
         "--root", str(tmp_path)], input=json.dumps({"owner_id": "owner_a",
                                                      "query": "Parsons"}),
        text=True, capture_output=True, check=True)
    response = json.loads(result.stdout)
    assert len(response["hits"]) == 1 and response["index_state"] == "ready"
    assert json.loads(subprocess.run(
        [sys.executable, "-m", "agents.librarian.runtime.gateway_search",
         "--root", str(tmp_path)], input=json.dumps({"owner_id": "owner_b",
                                                      "query": "Parsons"}),
        text=True, capture_output=True, check=True).stdout)["hits"] == []


def test_gateway_search_does_not_create_missing_store(tmp_path: Path):
    root = tmp_path / "absent"
    result = subprocess.run(
        [sys.executable, "-m", "agents.librarian.runtime.gateway_search",
         "--root", str(root)], input=json.dumps({"owner_id": "owner_a",
                                                 "query": "Parsons"}),
        text=True, capture_output=True)
    assert result.returncode == 2
    assert json.loads(result.stdout)["error"]["code"] == "OBJECT_STORE_UNAVAILABLE"
    assert not root.exists()
