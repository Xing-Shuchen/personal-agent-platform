"""Discovery of local collection state by the historian runtime adapter.

The adapter turns collector coverage records into ContextPack coverage and into
readiness watermarks.  These tests are hermetic: they build synthetic collection
output at runtime and never read the developer's real collected history.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

REPO = Path(__file__).parents[1]
ADAPTER = REPO / "agents/personal-historian/runtime/historian.py"
HISTORIAN_ROOT = Path(os.environ.get("PERSONAL_HISTORIAN_ROOT", REPO.parent / "personal-historian-handoff"))

#: The adapter has its own dependencies (jsonschema, PyYAML), so it runs under
#: the same interpreter resolution PAP uses for its runtime calls.
INTERPRETER = os.environ.get("PAP_RUNTIME_PYTHON") or shutil.which("python3") or sys.executable


def _adapter_is_loadable() -> bool:
    if not (HISTORIAN_ROOT / "historian" / "summarization").is_dir():
        return False
    probe = subprocess.run(
        [INTERPRETER, "-c", "import jsonschema, yaml"],
        capture_output=True, text=True, check=False,
    )
    return probe.returncode == 0


pytestmark = pytest.mark.skipif(
    not _adapter_is_loadable(),
    reason="the historian checkout or the adapter's dependencies are unavailable",
)

DISCOVER_SCRIPT = (
    "import json, sys;"
    f"sys.path.insert(0, {str(HISTORIAN_ROOT)!r});"
    "import importlib.util;"
    f"spec = importlib.util.spec_from_file_location('adapter', {str(ADAPTER)!r});"
    "module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module);"
    "records, watermarks = module._discover_collection_state();"
    "print(json.dumps({'records': records,"
    " 'watermarks': {k: (v.isoformat() if v else None) for k, v in watermarks.items()}}))"
)


def _coverage_record(collector_type, *, status, ratio=None, end="2026-09-12T16:00:00+00:00"):
    record = {
        "schema_version": "0.1.0", "coverage_id": f"coverage:{collector_type}", "domain": "personal",
        "collector": {"collector_id": f"collector:{collector_type}", "collector_type": collector_type,
                      "collector_version": "0.1.0"},
        "scope": {"kind": "repository_set", "scope_id": "scope:test"},
        "window": {"start": "2026-09-11T16:00:00+00:00", "end": end, "boundary": "[start,end)"},
        "status": status, "assessed_at": end, "basis": "synthetic", "known_gaps": [], "limitations": [],
    }
    if ratio is not None:
        record["coverage_ratio"] = ratio
    return record


def _run(env, script=DISCOVER_SCRIPT):
    completed = subprocess.run([INTERPRETER, "-c", script], capture_output=True, text=True,
                               env=env, check=False)
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout)


def _discover(tmp_path, records):
    """Run discovery against a synthetic collection root."""
    tag = tmp_path / "examples" / "live-run" / "personal" / "today"
    tag.mkdir(parents=True)
    (tag / "coverage.json").write_text(json.dumps(records), encoding="utf-8")
    env = dict(
        os.environ,
        PERSONAL_HISTORIAN_ROOT=str(HISTORIAN_ROOT),
        PERSONAL_HISTORIAN_COLLECTION_ROOT=str(tmp_path / "examples" / "live-run"),
        PERSONAL_HISTORIAN_REVISIONS=str(tmp_path / "no-revisions"),
    )
    return _run(env)


def test_covered_collection_reports_complete_coverage(tmp_path):
    result = _discover(tmp_path, [_coverage_record("git", status="covered", ratio=1)])
    assert result["records"] == [{"source": "git", "status": "complete",
                                  "note": "collector coverage from coverage.json"}]
    assert result["watermarks"] == {"git": "2026-09-12T16:00:00+00:00"}


def test_partial_collection_reports_partial_coverage(tmp_path):
    result = _discover(tmp_path, [_coverage_record("browser_history", status="covered", ratio=0.5),
                                  _coverage_record("obsidian", status="partial")])
    statuses = {record["source"]: record["status"] for record in result["records"]}
    assert statuses == {"browser_history": "good", "obsidian": "partial"}


def test_unknown_coverage_stays_unknown(tmp_path):
    """Zhihu retention makes completeness unknowable; that is not 'poor'."""
    result = _discover(tmp_path, [_coverage_record("zhihu_browsing_history", status="unknown")])
    assert result["records"][0]["status"] == "unknown"


def test_unsupported_coverage_stays_unknown(tmp_path):
    result = _discover(tmp_path, [_coverage_record("shell", status="unsupported")])
    assert result["records"][0]["status"] == "unknown"


def test_failed_collection_reports_missing_data(tmp_path):
    result = _discover(tmp_path, [_coverage_record("bilibili_history", status="failed")])
    assert result["records"][0]["status"] == "missing"


def test_a_failed_collector_still_yields_a_watermark(tmp_path):
    """The window was attempted; that is a readiness fact, not a coverage claim."""
    result = _discover(tmp_path, [_coverage_record("shell", status="failed", end="2026-09-12T18:00:00+00:00")])
    assert result["watermarks"]["shell"] == "2026-09-12T18:00:00+00:00"
    assert result["records"][0]["status"] == "missing"


def test_the_most_recent_window_wins(tmp_path):
    result = _discover(tmp_path, [
        _coverage_record("git", status="covered", ratio=1, end="2026-09-10T16:00:00+00:00"),
        _coverage_record("git", status="covered", ratio=1, end="2026-09-12T16:00:00+00:00"),
    ])
    assert result["watermarks"] == {"git": "2026-09-12T16:00:00+00:00"}


def test_records_without_a_usable_window_are_skipped(tmp_path):
    broken = _coverage_record("git", status="covered", ratio=1)
    broken["window"] = {"start": "2026-09-11T16:00:00+00:00", "boundary": "[start,end)"}
    result = _discover(tmp_path, [broken])
    assert result["records"] == []
    assert result["watermarks"] == {}


def test_an_absent_collection_root_is_not_an_error(tmp_path):
    env = dict(
        os.environ,
        PERSONAL_HISTORIAN_ROOT=str(HISTORIAN_ROOT),
        PERSONAL_HISTORIAN_COLLECTION_ROOT=str(tmp_path / "does-not-exist"),
        PERSONAL_HISTORIAN_REVISIONS=str(tmp_path / "no-revisions"),
    )
    assert _run(env) == {"records": [], "watermarks": {}}


def _adapter_script(body: str) -> str:
    return (
        "import importlib.util, os, sys;"
        f"sys.path.insert(0, {str(HISTORIAN_ROOT)!r});"
        f"spec=importlib.util.spec_from_file_location('adapter', {str(ADAPTER)!r});"
        "module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module);"
        + body
    )


def test_vault_dir_env_precedence_config_fallback_and_malformed_config(tmp_path):
    root = tmp_path / "historian"
    config = root / "config"
    config.mkdir(parents=True)
    fallback = tmp_path / "fallback-vault"
    configured = tmp_path / "configured-vault"
    (config / "repositories.json").write_text(json.dumps({"repositories": [
        {"name": "second-brain", "path": str(fallback)},
    ]}), encoding="utf-8")
    script = _adapter_script(
        f"os.environ['PERSONAL_HISTORIAN_ROOT']={str(root)!r};"
        f"os.environ['PERSONAL_HISTORIAN_OBSIDIAN_VAULT']={str(configured)!r};"
        "print(module._vault_dir())"
    )
    assert subprocess.run([INTERPRETER, "-c", script], capture_output=True, text=True, check=True).stdout.strip() == str(configured.resolve())

    script = _adapter_script(
        f"os.environ['PERSONAL_HISTORIAN_ROOT']={str(root)!r};"
        "os.environ.pop('PERSONAL_HISTORIAN_OBSIDIAN_VAULT', None); print(module._vault_dir())"
    )
    assert subprocess.run([INTERPRETER, "-c", script], capture_output=True, text=True, check=True).stdout.strip() == str(fallback.resolve())

    (config / "repositories.json").write_text("not json", encoding="utf-8")
    assert subprocess.run([INTERPRETER, "-c", script], capture_output=True, text=True, check=True).stdout.strip() == "None"


def test_missing_week_diaries_detects_empty_missing_and_complete_days(tmp_path):
    vault = tmp_path / "vault"
    script = _adapter_script(
        "from datetime import datetime, timedelta; from types import SimpleNamespace;"
        f"os.environ['PERSONAL_HISTORIAN_OBSIDIAN_VAULT']={str(vault)!r};"
        "period=SimpleNamespace(start=datetime.fromisoformat('2026-09-14T00:00:00+08:00'), end_exclusive=datetime.fromisoformat('2026-09-21T00:00:00+08:00'));"
        "print(module.json.dumps(module._missing_week_diaries(period)))"
    )
    initial = subprocess.run([INTERPRETER, "-c", script], capture_output=True, text=True, check=True)
    assert json.loads(initial.stdout) == [f"2026-09-{day:02d}" for day in range(14, 21)]
    for day in range(14, 21):
        path = vault / "Dairies" / "2026" / f"2026-09-{day:02d}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("---\ntype: ethnography-daily\n---\ncontent\n", encoding="utf-8")
    assert json.loads(subprocess.run([INTERPRETER, "-c", script], capture_output=True, text=True, check=True).stdout) == []
    (vault / "Dairies" / "2026" / "2026-09-17.md").unlink()
    assert json.loads(subprocess.run([INTERPRETER, "-c", script], capture_output=True, text=True, check=True).stdout) == ["2026-09-17"]


def test_the_default_root_matches_where_collect_all_writes(tmp_path, monkeypatch):
    """Without an explicit root, discovery must read the collector output layout.

    The default previously pointed at ``collection-runs``, a directory no
    collector writes, so production ContextPacks carried no coverage records at
    all and every period looked equally unmeasured.
    """
    tag = tmp_path / "examples" / "live-run" / "personal" / "today"
    tag.mkdir(parents=True)
    (tag / "coverage.json").write_text(
        json.dumps([_coverage_record("git", status="covered", ratio=1)]), encoding="utf-8")

    env = {key: value for key, value in os.environ.items()
           if key not in {"PERSONAL_HISTORIAN_COLLECTION_ROOT", "PERSONAL_HISTORIAN_REVISIONS"}}
    env["PERSONAL_HISTORIAN_ROOT"] = str(tmp_path)
    env["PERSONAL_HISTORIAN_REVISIONS"] = str(tmp_path / "no-revisions")

    result = _run(env)
    assert result["records"] == [{"source": "git", "status": "complete",
                                  "note": "collector coverage from coverage.json"}]
    assert result["watermarks"] == {"git": "2026-09-12T16:00:00+00:00"}
