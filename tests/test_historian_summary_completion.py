"""Completion of a PeriodSummary through the runtime (§28, §38).

§38 requires integration coverage for "ContextPack -> PAP -> PeriodSummary" and
"PeriodSummary -> validator -> commit".  The card paths had it; the summary path
did not, so this covers prepare -> model reply -> validation -> canonical commit
-> deterministic render, and the ways a reply must be refused.

Hermetic: child summaries are synthesized and committed to a temporary store, and
the model reply is supplied directly.
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
run_id = sys.argv[2]
payload = {"run_id": run_id, "skill": "historian-period-summary",
           "args": json.loads(os.environ["ARGS"])}
if sys.argv[1] == "prepare":
    result = adapter.prepare(payload)
else:
    payload["model_reply"] = os.environ.get("MODEL_REPLY", "")
    result = adapter.complete(payload)
print(json.dumps(result))
'''


def _content_hash(document: dict) -> str:
    payload = {key: value for key, value in document.items() if key != "content_hash"}
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, allow_nan=False, sort_keys=True,
                   separators=(",", ":")).encode("utf-8")).hexdigest()


def child_summary(summary_id: str, kind: str, label: str, start: str, end: str, digest: str) -> dict:
    document = {
        "schema_version": "1.0.0", "artifact_type": "historian.period-summary.v1",
        "summary_id": summary_id, "revision": 1, "domain": "personal", "created_at": STAMP,
        "period": {"kind": kind, "label": label, "timezone": TZ, "start": start, "end_exclusive": end},
        "status": "partial", "headline": f"{label} headline", "overview": f"{label} overview.",
        "historical_claims": [], "threads": [], "landmark_events": [], "decisions": [],
        "state_changes": [], "cognitive_changes": [], "subjective_patterns": [], "open_threads": [],
        "contradictions": [], "evidence_gaps": [], "next_level_digest": digest,
        "basis_refs": [{"artifact_id": "event-card:synthetic", "revision": 1, "content_hash": "a" * 64}],
        "provenance": {"generated_at": STAMP, "generator": "test",
                       "input_refs": [{"artifact_id": "event-card:synthetic", "revision": 1,
                                       "content_hash": "a" * 64}],
                       "input_manifest_hash": "b" * 64},
    }
    document["content_hash"] = _content_hash(document)
    return document


SEPTEMBER_WEEKS = [
    child_summary("summary:week:2026-W37", "week", "2026-W37",
                  "2026-09-07T00:00:00+08:00", "2026-09-14T00:00:00+08:00", "W37 digest."),
    child_summary("summary:week:2026-W38", "week", "2026-W38",
                  "2026-09-14T00:00:00+08:00", "2026-09-21T00:00:00+08:00", "W38 digest."),
    child_summary("summary:week:2026-W39", "week", "2026-W39",
                  "2026-09-21T00:00:00+08:00", "2026-09-28T00:00:00+08:00", "W39 digest."),
]


class Session:
    def __init__(self, tmp_path):
        self.store = tmp_path / "store"
        self.state = tmp_path / "state"
        self.collection = tmp_path / "no-collections"

    def run(self, action, run_id, *, reply=None, seed=SEPTEMBER_WEEKS):
        env = dict(os.environ,
                   HISTORIAN_ROOT=str(HISTORIAN_ROOT), ADAPTER_PATH=str(ADAPTER),
                   PERSONAL_HISTORIAN_ROOT=str(HISTORIAN_ROOT),
                   PERSONAL_HISTORIAN_STORE=str(self.store),
                   PERSONAL_HISTORIAN_REVISIONS=str(self.collection / "revisions"),
                   PERSONAL_HISTORIAN_COLLECTION_ROOT=str(self.collection),
                   PERSONAL_HISTORIAN_WATERMARKS_JSON=json.dumps(WATERMARKS),
                   PAP_AGENT_STATE_DIR=str(self.state),
                   ARGS=json.dumps({"kind": "month", "period": "2026-09", "timezone": TZ}),
                   SEED_ARTIFACTS=json.dumps(list(seed)))
        if reply is not None:
            env["MODEL_REPLY"] = reply
        completed = subprocess.run([INTERPRETER, "-c", DRIVER, action, run_id],
                                   capture_output=True, text=True, env=env, check=False)
        assert completed.returncode == 0, completed.stderr
        return json.loads(completed.stdout)

    def pack(self, run_id="prepare1"):
        return json.loads((self.state / "context" / f"{run_id}.json").read_text(encoding="utf-8"))

    def fixed(self, run_id="prepare1"):
        return json.loads((self.state / "prepared" / f"{run_id}.json").read_text(encoding="utf-8"))

    def stored(self, artifact_type="historian.period-summary.v1"):
        path = self.store / "artifacts.jsonl"
        if not path.is_file():
            return []
        return [json.loads(line)["record"] for line in path.read_text(encoding="utf-8").splitlines()
                if json.loads(line)["record"]["artifact_type"] == artifact_type]

    def summaries(self, summary_id="summary:month:2026-09"):
        """Only the month's own summary; the seeded weeks share the artifact type."""
        return [record for record in self.stored() if record["summary_id"] == summary_id]

    def rendered(self):
        directory = self.state / "rendered"
        return sorted(path.name for path in directory.iterdir()) if directory.is_dir() else []


def reply_for(pack, fixed, *, summary_id=None, revision=None, extra_ref=None, status="partial"):
    selected = {
        item["artifact_ref"]["artifact_id"]: item["artifact_ref"]["content_hash"]
        for entries in pack["sections"].values() for item in entries
    }
    references = [{"artifact_id": key, "revision": 1, "content_hash": value}
                  for key, value in sorted(selected.items())]
    if not references:
        references = [{"artifact_id": pack["context_pack_id"], "content_hash": pack["content_hash"]}]
    if extra_ref is not None:
        references.append(extra_ref)
    document = {
        "schema_version": "1.0.0", "artifact_type": "historian.period-summary.v1",
        "summary_id": summary_id or fixed["summary_id"],
        "revision": fixed["revision"] if revision is None else revision,
        "domain": "personal", "created_at": STAMP, "period": pack["period"], "status": status,
        "headline": "September", "overview": "A month of work.", "historical_claims": [
            {"statement": "Work continued.", "basis_refs": references[:1]}],
        "threads": [], "landmark_events": [], "decisions": [], "state_changes": [],
        "cognitive_changes": [], "subjective_patterns": [], "open_threads": [],
        "contradictions": [], "evidence_gaps": [], "next_level_digest": "September digest.",
        "basis_refs": references,
        "provenance": {"generated_at": "1999-01-01T00:00:00+00:00", "generator": "the-model",
                       "input_refs": [], "input_manifest_hash": "0" * 64,
                       "content_hash": "not-a-provenance-field"},
    }
    document["content_hash"] = _content_hash(document)
    return document


def prepared_session(tmp_path, run_id="prepare1"):
    session = Session(tmp_path)
    result = session.run("prepare", run_id)
    assert result["status"] == "ready", result
    return session


def test_a_valid_reply_is_validated_committed_and_rendered(tmp_path):
    session = prepared_session(tmp_path)
    pack, fixed = session.pack(), session.fixed()

    result = session.run("complete", "prepare1", reply=json.dumps(reply_for(pack, fixed)))
    assert result["status"] == "success", result
    assert result["metadata"]["result_summary_id"] == fixed["summary_id"]
    assert result["metadata"]["summary_revision"] == 1

    committed = session.summaries()
    assert len(committed) == 1
    assert committed[0]["summary_id"] == fixed["summary_id"]
    # The runtime, not the model, states what the summary was built from.
    assert committed[0]["provenance"]["input_manifest_hash"] == pack["provenance"]["input_manifest_hash"]
    assert committed[0]["provenance"]["generator"] == "pap.personal-historian.runtime/v1"
    assert committed[0]["content_hash"] == _content_hash(committed[0])
    # §20: the Markdown view is produced deterministically from the canonical JSON.
    assert session.rendered() == [f"{fixed['summary_id'].replace(':', '_')}.md"]


def test_a_reply_with_the_wrong_identity_is_refused(tmp_path):
    session = prepared_session(tmp_path)
    pack, fixed = session.pack(), session.fixed()

    result = session.run("complete", "prepare1",
                         reply=json.dumps(reply_for(pack, fixed, summary_id="summary:month:1999-01")))
    assert result["status"] == "error"
    assert result["failure_kind"] == "model_output"
    assert session.summaries() == []


def test_a_wrong_revision_is_refused(tmp_path):
    session = prepared_session(tmp_path)
    pack, fixed = session.pack(), session.fixed()

    result = session.run("complete", "prepare1", reply=json.dumps(reply_for(pack, fixed, revision=7)))
    assert result["status"] == "error"
    assert result["failure_kind"] == "model_output"
    assert session.summaries() == []


def test_an_unparseable_reply_is_refused(tmp_path):
    session = prepared_session(tmp_path)
    result = session.run("complete", "prepare1", reply="I could not produce a summary.")
    assert result["status"] == "error"
    assert result["failure_kind"] == "model_output"
    assert session.summaries() == []


def test_a_reference_outside_the_context_pack_is_refused(tmp_path):
    session = prepared_session(tmp_path)
    pack, fixed = session.pack(), session.fixed()

    result = session.run("complete", "prepare1", reply=json.dumps(reply_for(
        pack, fixed, extra_ref={"artifact_id": "event-card:invented", "revision": 1,
                                "content_hash": "c" * 64})))
    assert result["status"] == "error"
    assert result["failure_kind"] == "validation"
    assert session.summaries() == []


def test_a_malformed_summary_is_refused(tmp_path):
    session = prepared_session(tmp_path)
    pack, fixed = session.pack(), session.fixed()
    document = reply_for(pack, fixed)
    user_facing = dict(document)
    # A summary the schema rejects outright: an unsupported status.
    user_facing["status"] = "definitely-not-a-status"
    user_facing["content_hash"] = _content_hash(user_facing)

    result = session.run("complete", "prepare1", reply=json.dumps(user_facing))
    assert result["status"] == "error"
    assert result["failure_kind"] == "validation"
    assert session.summaries() == []


def test_a_summary_without_a_prepared_context_pack_is_refused(tmp_path):
    session = Session(tmp_path)
    result = session.run("complete", "never-prepared", reply=json.dumps({"summary_id": "x"}))
    assert result["status"] == "error"
    assert session.summaries() == []


def test_the_context_pack_is_retained_alongside_the_summary(tmp_path):
    session = prepared_session(tmp_path)
    pack, fixed = session.pack(), session.fixed()
    session.run("complete", "prepare1", reply=json.dumps(reply_for(pack, fixed)))

    packs = session.stored("historian.context-pack.v1")
    assert len(packs) == 1
    assert packs[0]["context_pack_id"] == pack["context_pack_id"]
