"""Period-summary jobs: child-summary gating and the sealed ContextPack (§14, §28).

Hermetic: child summaries are synthesized at runtime and committed to a
temporary artifact store.  The ContextPack the job would hand to the model is
inspected directly, so the orchestration is verified without a model turn —
which is the only part of Gate 7 this environment cannot run.
"""

from __future__ import annotations

import hashlib
import importlib.util
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

INTERPRETER = os.environ.get("PAP_RUNTIME_PYTHON") or shutil.which("python3") or sys.executable

WATERMARKS = {"reconstruction": "2026-10-05T00:00:00+08:00", "git": "2026-10-05T00:00:00+08:00"}
STAMP = "2026-10-05T00:00:00+08:00"
TZ = "Asia/Shanghai"


def _drivable() -> bool:
    if not (HISTORIAN_ROOT / "historian" / "summarization").is_dir():
        return False
    probe = subprocess.run([INTERPRETER, "-c", "import jsonschema, yaml"],
                           capture_output=True, text=True, check=False)
    return probe.returncode == 0


pytestmark = pytest.mark.skipif(not _drivable(), reason="historian checkout or adapter dependencies unavailable")


def _content_hash(document: dict) -> str:
    """Mirror the historian's content addressing so seeds are schema-valid."""

    payload = {key: value for key, value in document.items() if key != "content_hash"}
    canonical = json.dumps(payload, ensure_ascii=False, allow_nan=False, sort_keys=True,
                           separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def summary(summary_id: str, kind: str, label: str, start: str, end: str) -> dict:
    """A minimal schema-valid PeriodSummary standing in for a committed child."""
    document = {
        "schema_version": "1.0.0", "artifact_type": "historian.period-summary.v1",
        "summary_id": summary_id, "revision": 1, "domain": "personal", "created_at": STAMP,
        "period": {"kind": kind, "label": label, "timezone": TZ, "start": start, "end_exclusive": end},
        "status": "partial", "headline": f"{label} headline", "overview": f"{label} overview.",
        "historical_claims": [{"statement": f"{label} claim", "basis_refs": [
            {"artifact_id": "event-card:synthetic", "revision": 1, "content_hash": "a" * 64}]}],
        "threads": [], "landmark_events": [], "decisions": [], "state_changes": [],
        "cognitive_changes": [], "subjective_patterns": [], "open_threads": [], "contradictions": [],
        "evidence_gaps": [], "next_level_digest": f"{label} digest.",
        "basis_refs": [{"artifact_id": "event-card:synthetic", "revision": 1, "content_hash": "a" * 64}],
        "provenance": {"generated_at": STAMP, "generator": "test",
                       "input_refs": [{"artifact_id": "event-card:synthetic", "revision": 1,
                                       "content_hash": "a" * 64}],
                       "input_manifest_hash": "b" * 64},
    }
    document["content_hash"] = _content_hash(document)
    return document


def week(label: str, start: str, end: str) -> dict:
    return summary(f"summary:week:{label}", "week", label, start, end)


def month(label: str, start: str, end: str) -> dict:
    return summary(f"summary:month:{label}", "month", label, start, end)


# The weeks that lie wholly inside 2026-09; the month job must insist on exactly these.
SEPTEMBER_WEEKS = [
    week("2026-W37", "2026-09-07T00:00:00+08:00", "2026-09-14T00:00:00+08:00"),
    week("2026-W38", "2026-09-14T00:00:00+08:00", "2026-09-21T00:00:00+08:00"),
    week("2026-W39", "2026-09-21T00:00:00+08:00", "2026-09-28T00:00:00+08:00"),
]

DRIVER = r'''
import importlib.util, json, os, sys
sys.path.insert(0, os.environ["HISTORIAN_ROOT"])
from historian.summarization import ArtifactStore
store = ArtifactStore(os.environ["PERSONAL_HISTORIAN_STORE"], domain="personal")
for document in json.loads(os.environ.get("SEED_ARTIFACTS", "[]")):
    store.commit(document)
spec = importlib.util.spec_from_file_location("adapter", os.environ["ADAPTER_PATH"])
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)
result = adapter._prepare_summary({
    "run_id": os.environ["RUN_ID"], "skill": "historian-period-summary",
    "args": json.loads(os.environ["ARGS"])})
print(json.dumps(result))
'''


class Job:
    def __init__(self, tmp_path):
        self.store = tmp_path / "store"
        self.state = tmp_path / "state"
        self.collection = tmp_path / "no-collections"

    def prepare(self, kind, period, *, seed=(), watermarks=WATERMARKS, run_id="run1"):
        env = dict(os.environ,
                   HISTORIAN_ROOT=str(HISTORIAN_ROOT), ADAPTER_PATH=str(ADAPTER),
                   PERSONAL_HISTORIAN_ROOT=str(HISTORIAN_ROOT),
                   PERSONAL_HISTORIAN_STORE=str(self.store),
                   PERSONAL_HISTORIAN_REVISIONS=str(self.collection / "revisions"),
                   # Keep retrieval hermetic: never read the developer's collections.
                   PERSONAL_HISTORIAN_COLLECTION_ROOT=str(self.collection),
                   PAP_AGENT_STATE_DIR=str(self.state),
                   RUN_ID=run_id,
                   ARGS=json.dumps({"kind": kind, "period": period, "timezone": TZ}),
                   SEED_ARTIFACTS=json.dumps(list(seed)))
        if watermarks is None:
            env.pop("PERSONAL_HISTORIAN_WATERMARKS_JSON", None)
        else:
            env["PERSONAL_HISTORIAN_WATERMARKS_JSON"] = json.dumps(watermarks)
        completed = subprocess.run([INTERPRETER, "-c", DRIVER], capture_output=True, text=True,
                                   env=env, check=False)
        assert completed.returncode == 0, completed.stderr
        result = json.loads(completed.stdout)
        return result, (self.state / "context" / f"{run_id}.json")


def pack_of(result, context_path):
    assert result["status"] == "ready", result
    assert context_path.is_file()
    return json.loads(context_path.read_text(encoding="utf-8"))


def test_a_month_without_its_weekly_children_is_not_ready(tmp_path):
    job = Job(tmp_path)
    result, _ = job.prepare("month", "2026-09", seed=SEPTEMBER_WEEKS[:2])
    assert result["status"] == "not_ready"
    assert "summary:week:2026-W39" in result["reason"]
    assert "summary:week:2026-W38" not in result["reason"]


def test_a_month_with_every_weekly_child_is_ready(tmp_path):
    job = Job(tmp_path)
    result, context_path = job.prepare("month", "2026-09", seed=SEPTEMBER_WEEKS)
    pack = pack_of(result, context_path)
    children = {item["artifact_ref"]["artifact_id"] for item in pack["sections"]["child_summaries"]}
    assert children == {"summary:week:2026-W37", "summary:week:2026-W38", "summary:week:2026-W39"}
    assert result["metadata"]["period"] == "2026-09"


def test_weeks_outside_the_month_do_not_satisfy_the_gate(tmp_path):
    """A week from another month must not count as this month's child."""
    job = Job(tmp_path)
    stray = week("2026-W36", "2026-08-31T00:00:00+08:00", "2026-09-07T00:00:00+08:00")
    result, _ = job.prepare("month", "2026-09", seed=[*SEPTEMBER_WEEKS[:2], stray])
    assert result["status"] == "not_ready"
    assert "summary:week:2026-W39" in result["reason"]


def test_a_quarter_needs_its_months_and_uses_weeks_only_as_digest(tmp_path):
    job = Job(tmp_path)
    months = [month("2026-07", "2026-07-01T00:00:00+08:00", "2026-08-01T00:00:00+08:00"),
              month("2026-08", "2026-08-01T00:00:00+08:00", "2026-09-01T00:00:00+08:00"),
              month("2026-09", "2026-09-01T00:00:00+08:00", "2026-10-01T00:00:00+08:00")]
    blocked, _ = job.prepare("quarter", "2026-Q3", seed=months[:2])
    assert blocked["status"] == "not_ready"
    assert "summary:month:2026-09" in blocked["reason"]

    result, context_path = job.prepare("quarter", "2026-Q3", seed=[*months, *SEPTEMBER_WEEKS],
                                       run_id="run2")
    pack = pack_of(result, context_path)
    representation = {item["artifact_ref"]["artifact_id"]: item
                      for item in pack["sections"]["child_summaries"]}
    # Months are the direct children and are offered whole; weeks contribute
    # only their next_level_digest (§19).
    assert representation["summary:month:2026-09"]["content_mode"] == "full"
    assert representation["summary:week:2026-W37"]["content_mode"] == "digest"
    assert representation["summary:week:2026-W37"]["selection_reason"].startswith("next_level_digest of")


def test_a_halfyear_needs_every_quarter_of_its_half(tmp_path):
    job = Job(tmp_path)
    # 2026-H1 ends 2026-07-01, so the 2026-10-05 watermarks are met.
    quarter = summary("summary:quarter:2026-Q1", "quarter", "2026-Q1",
                      "2026-01-01T00:00:00+08:00", "2026-04-01T00:00:00+08:00")
    blocked, _ = job.prepare("halfyear", "2026-H1", seed=[quarter])
    assert blocked["status"] == "not_ready"
    assert "summary:quarter:2026-Q2" in blocked["reason"]


def test_a_job_without_a_reconstruction_watermark_is_not_ready(tmp_path):
    job = Job(tmp_path)
    result, _ = job.prepare("month", "2026-09", seed=SEPTEMBER_WEEKS,
                            watermarks={"git": "2026-10-05T00:00:00+08:00"})
    assert result["status"] == "not_ready"
    assert "reconstruction" in result["reason"]


def test_an_unmet_watermark_is_not_ready_rather_than_failed(tmp_path):
    job = Job(tmp_path)
    result, _ = job.prepare("month", "2026-09", seed=SEPTEMBER_WEEKS,
                            watermarks={"reconstruction": "2026-09-15T00:00:00+08:00"})
    assert result["status"] == "not_ready"
    assert "reconstruction" in result["reason"]


def test_no_watermarks_at_all_is_not_ready(tmp_path):
    job = Job(tmp_path)
    result, _ = job.prepare("month", "2026-09", seed=SEPTEMBER_WEEKS, watermarks=None)
    assert result["status"] == "not_ready"


def test_the_same_input_is_not_summarized_twice(tmp_path):
    """Idempotency (§32): an identical manifest must not mint a second revision."""
    job = Job(tmp_path)
    first, first_path = job.prepare("month", "2026-09", seed=SEPTEMBER_WEEKS, run_id="a")
    pack = pack_of(first, first_path)
    committed = summary("summary:month:2026-09", "month", "2026-09",
                        "2026-09-01T00:00:00+08:00", "2026-10-01T00:00:00+08:00")
    committed["provenance"] = {**pack["provenance"],
                               "input_refs": pack["provenance"]["input_refs"]}
    committed["content_hash"] = _content_hash(committed)

    second, _ = job.prepare("month", "2026-09", seed=[*SEPTEMBER_WEEKS, committed], run_id="b")
    assert second["status"] == "not_ready"
    assert "already committed" in second["reason"]


def test_an_unsupported_kind_is_an_error_not_a_summary(tmp_path):
    job = Job(tmp_path)
    result, _ = job.prepare("day", "2026-09-08", seed=SEPTEMBER_WEEKS)
    assert result["status"] == "error"
    assert "supported kind" in result["error"]


def _stored_artifacts(store_dir):
    path = Path(store_dir) / "artifacts.jsonl"
    if not path.is_file():
        return []
    return [json.loads(line)["record"] for line in path.read_text(encoding="utf-8").splitlines()]


def test_the_context_pack_is_retained_for_diagnostics(tmp_path):
    """§4 allows retaining the execution artifact; §41 needs it to report."""
    job = Job(tmp_path)
    result, context_path = job.prepare("month", "2026-09", seed=SEPTEMBER_WEEKS)
    pack = pack_of(result, context_path)

    stored = [record for record in _stored_artifacts(job.store)
              if record["artifact_type"] == "historian.context-pack.v1"]
    assert len(stored) == 1
    assert stored[0]["context_pack_id"] == pack["context_pack_id"]
    assert stored[0]["revision"] == 1
    assert stored[0]["content_hash"] == pack["content_hash"]


def test_an_unchanged_context_pack_does_not_mint_a_second_revision(tmp_path):
    job = Job(tmp_path)
    assert job.prepare("month", "2026-09", seed=SEPTEMBER_WEEKS, run_id="a")[0]["status"] == "ready"
    assert job.prepare("month", "2026-09", seed=SEPTEMBER_WEEKS, run_id="b")[0]["status"] == "ready"

    packs = [record for record in _stored_artifacts(job.store)
             if record["artifact_type"] == "historian.context-pack.v1"]
    assert len(packs) == 1
    assert packs[0]["revision"] == 1


def test_a_changed_context_pack_becomes_the_next_revision(tmp_path):
    job = Job(tmp_path)
    assert job.prepare("month", "2026-09", seed=SEPTEMBER_WEEKS, run_id="a")[0]["status"] == "ready"
    # A week receives a new revision, so the material the month is built from
    # changes and the pack cannot stay at revision 1.
    changed = week("2026-W39", "2026-09-21T00:00:00+08:00", "2026-09-28T00:00:00+08:00")
    changed["next_level_digest"] = "A revised digest for the same week."
    changed["revision"] = 2
    changed["content_hash"] = _content_hash(changed)
    second, _ = job.prepare("month", "2026-09",
                            seed=[SEPTEMBER_WEEKS[0], SEPTEMBER_WEEKS[1], changed], run_id="b")
    assert second["status"] == "ready"

    packs = [record for record in _stored_artifacts(job.store)
             if record["artifact_type"] == "historian.context-pack.v1"]
    assert [record["revision"] for record in packs] == [1, 2]
