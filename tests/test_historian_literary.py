"""Exact literary Properties are supplied before the model renders the summary."""

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import yaml


def test_literary_prompt_supplies_exact_required_properties(tmp_path, monkeypatch):
    path = Path(__file__).parents[1] / "agents/personal-historian/runtime/historian.py"
    spec = importlib.util.spec_from_file_location("literary_adapter", path)
    adapter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(adapter)
    period_data = {
        "label": "2026-W42", "start": "2026-10-12T00:00:00+08:00",
        "end_exclusive": "2026-10-19T00:00:00+08:00",
    }
    summary = {"period": period_data, "status": "partial", "revision": 1, "content_hash": "synthetic"}
    monkeypatch.setattr(adapter, "resolve_period", lambda *args: SimpleNamespace(
        label="2026-W42", to_dict=lambda: period_data), raising=False)
    monkeypatch.setattr(adapter, "_store", lambda: SimpleNamespace(
        latest=lambda key: summary, is_stale=lambda key: False))
    monkeypatch.setenv("PAP_AGENT_STATE_DIR", str(tmp_path))
    result = adapter._prepare_literary({"run_id": "literary1", "args": {"kind": "week"}})
    prompt = result["input_text"]
    assert "verbatim into the YAML Properties" in prompt
    properties = yaml.safe_load(prompt.split("```yaml\n", 1)[1].split("```", 1)[0])
    assert properties == {
        "schema_version": 1, "week": "2026-W42", "type": "ethnography-weekly", "status": "partial",
        "period_start": "2026-10-12", "period_end": "2026-10-18",
    }
    prepared = json.loads(adapter._prepared_path("literary1").read_text())
    assert prepared == {
        "kind": "literary", "summary_id": "summary:week:2026-W42", "summary_revision": 1,
        "summary_hash": "synthetic", "period": period_data,
    }
