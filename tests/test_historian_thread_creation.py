"""Thread creation: the path that lets the first thread exist at all (§7, §30).

Until a thread identity exists there is nothing for the weekly update job to
update, so this bootstrapping path is what makes thread synthesis reachable.

Hermetic: EventCards are synthesized and committed to a temporary store; no real
history is read and no canonical artifact is written.
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
STAMP = "2026-09-13T00:00:00+00:00"


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
action, run_id = sys.argv[1], sys.argv[2]
payload = {"run_id": run_id, "skill": "historian-thread-card", "args": {"mode": "weekly-update"}}
if action == "prepare":
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


def event_card(identifier: str, *, title: str) -> dict:
    reference = {"artifact_id": f"event:{identifier}", "revision": 1, "content_hash": "a" * 64}
    document = {
        "schema_version": "1.0.0", "artifact_type": "historian.event-card.v1",
        "event_card_id": f"event-card:{identifier}", "revision": 1, "domain": "personal",
        "created_at": STAMP, "event_ref": reference, "title": title, "digest": f"{title} digest.",
        "time": {"start": {"value": "2026-09-08T09:00:00+08:00", "precision": "exact"},
                 "end": {"value": "2026-09-08T10:00:00+08:00", "precision": "exact"}},
        "event_type": "work", "importance": "medium", "confidence": "medium",
        "subjective_salience": "unknown", "thread_ids": [], "decisions": [], "state_changes": [],
        "open_consequences": [], "contradictions": [],
        "evidence_refs": [{"artifact_id": "observation:synthetic", "revision": 1, "content_hash": "c" * 64}],
        "provenance": {"generated_at": STAMP, "generator": "test",
                       "input_refs": [reference], "input_manifest_hash": "d" * 64},
    }
    document["content_hash"] = _content_hash(document)
    return document


class Harness:
    def __init__(self, tmp_path, cards):
        self.store = tmp_path / "store"
        self.state = tmp_path / "state"
        self.cards = cards

    def run(self, action, run_id="run1", reply=None):
        env = dict(os.environ,
                   HISTORIAN_ROOT=str(HISTORIAN_ROOT), ADAPTER_PATH=str(ADAPTER),
                   PERSONAL_HISTORIAN_ROOT=str(HISTORIAN_ROOT),
                   PERSONAL_HISTORIAN_STORE=str(self.store),
                   PAP_AGENT_STATE_DIR=str(self.state),
                   SEED_ARTIFACTS=json.dumps(self.cards))
        if reply is not None:
            env["MODEL_REPLY"] = reply
        completed = subprocess.run([INTERPRETER, "-c", DRIVER, action, run_id],
                                   capture_output=True, text=True, env=env, check=False)
        assert completed.returncode == 0, completed.stderr
        return json.loads(completed.stdout)

    def prepared(self, run_id):
        return json.loads((self.state / "prepared" / f"{run_id}.json").read_text(encoding="utf-8"))

    def stored(self):
        path = self.store / "artifacts.jsonl"
        if not path.is_file():
            return []
        return [json.loads(line)["record"] for line in path.read_text(encoding="utf-8").splitlines()]

    def thread_cards(self):
        return [r for r in self.stored() if r["artifact_type"] == "historian.thread-card.v1"]

    def registry_ids(self):
        path = self.store / "threads.jsonl"
        if not path.is_file():
            return set()
        return {json.loads(line)["thread_id"] for line in path.read_text(encoding="utf-8").splitlines()}


def _proposal(harness, *, name="Compiler Learning", evidence=None):
    cards = harness.cards
    chosen = evidence if evidence is not None else [c["event_card_id"] for c in cards]
    document = {
        "schema_version": "1.0.0", "artifact_type": "historian.thread-card.v1",
        "thread_card_id": "thread-card:placeholder", "thread_id": "thread:placeholder",
        "revision": 1, "domain": "personal", "created_at": STAMP,
        "canonical_name": name, "aliases": [], "status": "active",
        "digest": "Synthetic thread.", "trajectory": "Observed across two events.",
        "current_state": "Open.", "milestones": [],
        "evidence_refs": [{"artifact_id": identifier, "revision": 1, "content_hash": "e" * 64}
                          for identifier in chosen],
        "provenance": {"generated_at": STAMP, "generator": "model", "input_refs": [],
                       "input_manifest_hash": "f" * 64},
    }
    document["content_hash"] = _content_hash(document)
    return document


def test_unassigned_events_are_offered_as_a_possible_thread(tmp_path):
    harness = Harness(tmp_path, [event_card("one", title="First"), event_card("two", title="Second")])
    result = harness.run("prepare")
    assert result["status"] == "ready"
    assert harness.prepared("run1")["kind"] == "thread-creation"
    assert "NO_NEW_THREAD" in result["input_text"]


def test_a_single_event_is_not_offered_for_creation(tmp_path):
    harness = Harness(tmp_path, [event_card("one", title="Only one")])
    result = harness.run("prepare")
    assert result["status"] == "not_ready"
    assert "evidence of persistence" in result["reason"]


def test_the_model_may_decline_to_create_a_thread(tmp_path):
    harness = Harness(tmp_path, [event_card("one", title="First"), event_card("two", title="Second")])
    harness.run("prepare")
    result = harness.run("complete", reply="NO_NEW_THREAD")
    assert result["status"] == "success"
    assert result["metadata"]["thread_created"] is None
    assert harness.thread_cards() == []
    assert harness.registry_ids() == set()


def test_an_accepted_proposal_registers_a_derived_identity(tmp_path):
    harness = Harness(tmp_path, [event_card("one", title="First"), event_card("two", title="Second")])
    harness.run("prepare")
    result = harness.run("complete", reply=json.dumps(_proposal(harness)))
    assert result["status"] == "success"
    assert result["metadata"]["thread_created"] == "thread:compiler-learning"
    assert harness.registry_ids() == {"thread:compiler-learning"}

    stored = harness.thread_cards()
    assert len(stored) == 1
    card = stored[0]
    assert card["thread_card_id"] == "thread-card:compiler-learning"
    # The runtime owns provenance, and the card was re-sealed after identity.
    assert card["provenance"]["generator"] == "pap.personal-historian.runtime/v1"
    assert card["content_hash"] == _content_hash(card)


def test_a_proposal_without_runtime_owned_provenance_still_commits(tmp_path):
    """The runtime replaces provenance, so a model draft must not be validated
    against runtime-owned fields first.

    Regression: the 2026-09-14 historian-thread-weekly-update run failed with
    ``thread-card.v1.schema.json invalid at provenance: 'input_manifest_hash' is
    a required property`` because create_thread() validated the unsealed draft.
    """

    harness = Harness(tmp_path, [event_card("one", title="First"), event_card("two", title="Second")])
    harness.run("prepare")
    proposal = _proposal(harness)
    # What a model actually emits: a provenance block, but without the fields the
    # runtime owns (input_manifest_hash in particular).
    proposal["provenance"] = {"generated_at": STAMP, "generator": "model", "input_refs": []}
    proposal["content_hash"] = _content_hash(proposal)

    result = harness.run("complete", reply=json.dumps(proposal))
    assert result["status"] == "success", result.get("error")
    assert result["metadata"]["thread_created"] == "thread:compiler-learning"

    stored = harness.thread_cards()
    assert len(stored) == 1
    card = stored[0]
    assert card["provenance"]["generator"] == "pap.personal-historian.runtime/v1"
    assert card["provenance"]["input_manifest_hash"]
    assert card["content_hash"] == _content_hash(card)


def test_a_proposal_citing_one_event_is_refused_and_registers_nothing(tmp_path):
    harness = Harness(tmp_path, [event_card("one", title="First"), event_card("two", title="Second")])
    harness.run("prepare")
    result = harness.run("complete", reply=json.dumps(_proposal(harness, evidence=["event-card:one"])))
    assert result["status"] == "error"
    assert "at least 2 distinct events" in result["error"]
    assert harness.thread_cards() == []
    assert harness.registry_ids() == set()


def test_a_proposal_citing_unknown_events_is_refused(tmp_path):
    harness = Harness(tmp_path, [event_card("one", title="First"), event_card("two", title="Second")])
    harness.run("prepare")
    result = harness.run("complete", reply=json.dumps(
        _proposal(harness, evidence=["event-card:ghost", "event-card:phantom"])))
    assert result["status"] == "error"
    assert harness.registry_ids() == set()


def test_created_threads_do_not_get_created_again_from_the_same_events(tmp_path):
    """Otherwise one process would fracture into a new thread every week."""
    harness = Harness(tmp_path, [event_card("one", title="First"), event_card("two", title="Second")])
    harness.run("prepare")
    assert harness.run("complete", reply=json.dumps(_proposal(harness)))["status"] == "success"

    second = harness.run("prepare", run_id="run2")
    assert second["status"] == "not_ready"
    assert "evidence of persistence" in second["reason"] or "no registered thread" in second["reason"]


def test_a_registered_thread_with_new_evidence_is_updated_not_recreated(tmp_path):
    first = event_card("one", title="First")
    second = event_card("two", title="Second")
    harness = Harness(tmp_path, [first, second])
    harness.run("prepare")
    assert harness.run("complete", reply=json.dumps(_proposal(harness)))["status"] == "success"

    # A third event arrives assigned to the registered thread.
    third = event_card("three", title="Third")
    third["thread_ids"] = ["thread:compiler-learning"]
    third["content_hash"] = _content_hash(third)
    harness.cards = [first, second, third]
    prepared = harness.run("prepare", run_id="run3")
    assert prepared["status"] == "ready"
    fixed = harness.prepared("run3")
    assert fixed["kind"] == "thread"
    assert fixed["thread_id"] == "thread:compiler-learning"
    assert fixed["revision"] == 2


def _draft_for(harness, kind):
    harness.run("prepare")
    draft = _proposal(harness)
    if kind == "update":
        assert harness.run("complete", reply=json.dumps(draft))["status"] == "success"
        third = event_card("three", title="Third")
        third["thread_ids"] = ["thread:compiler-learning"]
        third["content_hash"] = _content_hash(third)
        harness.cards.append(third)
        assert harness.run("prepare", run_id="update")["status"] == "ready"
        fixed = harness.prepared("update")
        draft.update({key: fixed[key] for key in ("thread_id", "thread_card_id", "revision")})
    return draft, "update" if kind == "update" else "run1"


@pytest.mark.parametrize("kind", ["creation", "update"])
def test_thread_milestone_objects_are_normalized_losslessly_and_reported(tmp_path, kind):
    harness = Harness(tmp_path, [event_card("one", title="First"), event_card("two", title="Second")])
    draft, run_id = _draft_for(harness, kind)
    draft["milestones"] = ["An existing milestone.",
                           {"date": "2026-09-14", "summary": "First note.\nArchived."},
                           {"summary": "Later note."}]
    draft["provenance"].pop("input_manifest_hash")
    result = harness.run("complete", run_id=run_id, reply=json.dumps(draft))
    assert result["status"] == "success", result.get("error")
    card = harness.thread_cards()[-1]
    assert card["milestones"] == ["An existing milestone.", "2026-09-14: First note.\nArchived.",
                                  "Later note."]
    assert card["provenance"]["input_manifest_hash"]
    assert card["content_hash"] == _content_hash(card)
    assert result["metadata"]["output_normalizations"] == [
        {"field": "milestones/1", "operation": "date-summary-to-string"},
        {"field": "milestones/2", "operation": "summary-to-string"},
    ]


@pytest.mark.parametrize("milestone, field", [
    ({"date": "2026-09-14", "summary": 7}, "milestones/0/summary"),
    ({"date": ["2026-09-14"], "summary": "Note."}, "milestones/0/date"),
    ({"date": "2026-09-14", "summary": "Note.", "evidence": ["extra"]}, "milestones/0"),
])
def test_unrecoverable_milestone_objects_name_the_field_and_commit_nothing(tmp_path, milestone, field):
    harness = Harness(tmp_path, [event_card("one", title="First"), event_card("two", title="Second")])
    harness.run("prepare")
    draft = _proposal(harness)
    draft["milestones"] = [milestone]
    result = harness.run("complete", reply=json.dumps(draft))
    assert result["status"] == "error"
    assert result["failure_kind"] == "validation"
    assert field in result["error"]
    assert "expected" in result["error"]
    assert harness.thread_cards() == []
    assert harness.registry_ids() == set()


@pytest.mark.parametrize("recorded_failure", [
    None, "400: 400: [Malformed diagnostic JSON redacted]",
])
def test_weekly_job_refusal_is_rescued_by_fallback_and_real_runtime(tmp_path, monkeypatch, recorded_failure):
    """Exercise local config -> PAP -> runtime -> strict store, with no model service."""
    from pap.run import invoke
    from pap.spec import load_platform
    from paplog import observe

    harness = Harness(tmp_path, [event_card("one", title="First"), event_card("two", title="Second")])
    harness.run("prepare")  # Seed only the synthetic EventCards.
    root = tmp_path / "platform"
    shutil.copytree(REPO / "agents/personal-historian", root / "agents/personal-historian",
                    ignore=shutil.ignore_patterns("__pycache__"))
    config = root / "var/config/agents.yaml"
    config.parent.mkdir(parents=True)
    config.write_text("agents:\n  personal-historian:\n    enabled: true\n"
                      "    provider_rejection_fallback: test-provider/fallback-model\n", encoding="utf-8")
    spec = load_platform(root)[0]
    job = next(job for job in spec.jobs if job.name == "historian-thread-weekly-update")
    assert spec.model is None and job.model is None
    monkeypatch.setenv("PERSONAL_HISTORIAN_ROOT", str(HISTORIAN_ROOT))
    monkeypatch.setenv("PERSONAL_HISTORIAN_STORE", str(harness.store))
    monkeypatch.setenv("PAP_RUNTIME_PYTHON", INTERPRETER)
    observe.configure(tmp_path / "ledger")
    draft = _proposal(harness)
    draft["milestones"] = [{"date": "2026-09-14", "summary": "First note archived."}]
    draft["provenance"].pop("input_manifest_hash")
    calls = []

    def runner(command, **kwargs):
        calls.append(command)
        if len(calls) == 1:
            return subprocess.CompletedProcess(command, 1, "", "The AI service couldn't accept this request. "
                                               "Try a new conversation with /new, or choose another model "
                                               "in the Control UI. | 400")
        return subprocess.CompletedProcess(command, 0, json.dumps(draft), "")

    log = root / "var/state/runs.jsonl"
    result = invoke(
        root=root, spec=spec, skill=job.skill, args=job.args, runtime=job.runtime,
        trigger={"type": "schedule", "job_id": f"{spec.name}/{job.name}", "job_name": job.name},
        run_log=log, command_runner=runner,
        failure_probe=lambda *_: recorded_failure,
    )
    assert result.status == "success", result.error
    assert result.error == "" and result.failure_kind == ""
    assert len(calls) == 2
    assert "--model" not in calls[0]
    assert calls[1][-2:] == ["--model", spec.provider_rejection_fallback]
    events = [json.loads(line) for line in log.read_text().splitlines()]
    assert [event["event"] for event in events] == ["run.started", "run.fallback", "run.completed"]
    assert (recorded_failure or "The AI service couldn't accept this request") in events[1]["error"]
    assert events[-1]["status"] == "success"
    assert events[-1]["model"] == spec.provider_rejection_fallback
    assert events[-1]["usage"]["runtime"]["output_normalizations"] == [
        {"field": "milestones/0", "operation": "date-summary-to-string"},
    ]
    card = harness.thread_cards()[-1]
    assert card["milestones"] == ["2026-09-14: First note archived."]
    assert card["provenance"]["input_manifest_hash"]
    assert card["provenance"]["model"] == spec.provider_rejection_fallback
    assert card["content_hash"] == _content_hash(card)
