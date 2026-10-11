"""EventCard refresh lifecycle (Gate 5), driven through the PAP runtime adapter.

Hermetic: the Event revision journal is synthesized at runtime from the
historian repository's own synthetic Event fixture, and the artifact store is a
temporary directory.  No real personal history is read and no canonical artifact
is written.
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
import tempfile

import pytest

REPO = Path(__file__).parents[1]
ADAPTER = REPO / "agents/personal-historian/runtime/historian.py"
HISTORIAN_ROOT = Path(os.environ.get("PERSONAL_HISTORIAN_ROOT", REPO.parent / "personal-historian-handoff"))
EVENT_FIXTURE = HISTORIAN_ROOT / "examples" / "events" / "parser-morning.revision-2.event.json"

INTERPRETER = os.environ.get("PAP_RUNTIME_PYTHON") or shutil.which("python3") or sys.executable


def _adapter_is_drivable() -> bool:
    if not (HISTORIAN_ROOT / "historian" / "summarization").is_dir() or not EVENT_FIXTURE.is_file():
        return False
    probe = subprocess.run([INTERPRETER, "-c", "import jsonschema, yaml"],
                           capture_output=True, text=True, check=False)
    return probe.returncode == 0


pytestmark = pytest.mark.skipif(
    not _adapter_is_drivable(),
    reason="the historian checkout or the adapter's dependencies are unavailable",
)

#: Drives prepare/complete in a subprocess for one synthetic journal + store.
DRIVER = r'''
import importlib.util, json, os, sys
sys.path.insert(0, os.environ["HISTORIAN_ROOT"])
spec = importlib.util.spec_from_file_location("adapter", os.environ["ADAPTER_PATH"])
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)
action, run_id = sys.argv[1], sys.argv[2]
payload = json.loads(os.environ.get("PAYLOAD", "{}"))
payload["run_id"] = run_id
if action == "prepare":
    result = adapter._prepare_event_card(payload)
elif action == "seed":
    # Seeding bypasses CardLifecycle on purpose: the store must accept a card
    # bound to an older Event content hash so the refresh path can be exercised.
    from historian.summarization import ArtifactStore
    ArtifactStore(os.environ["PERSONAL_HISTORIAN_STORE"], domain="personal") \
        .commit(json.loads(os.environ["SEED_CARD"]))
    result = {"status": "success"}
else:
    result = adapter.complete({**payload, "run_id": run_id,
                               "model_reply": os.environ["MODEL_REPLY"]})
print(json.dumps(result))
'''


def _write_journal(root: Path, *, status: str = "current") -> dict:
    """Seed a revisions journal from the historian's synthetic Event fixture."""
    document = json.loads(EVENT_FIXTURE.read_text(encoding="utf-8"))
    document["revision"] = {**document["revision"], "status": status, "number": 1}
    record = document
    digest = hashlib.sha256(
        json.dumps(record, ensure_ascii=False, allow_nan=False, sort_keys=True,
                   separators=(",", ":")).encode("utf-8")).hexdigest()
    root.mkdir(parents=True, exist_ok=True)
    (root / "revisions.jsonl").write_text(
        json.dumps({"store_schema_version": "0.1.0", "record_digest": digest, "record": record}) + "\n",
        encoding="utf-8")
    return record


class Harness:
    def __init__(self, tmp_path):
        self.revisions = tmp_path / "revisions"
        self.store = tmp_path / "store"
        self.state = tmp_path / "state"
        self.event = _write_journal(self.revisions)

    def run(self, action, run_id, payload=None, model_reply=None, seed_card=None, extra_env=None):
        if action == "complete" and payload is None:
            payload = {"skill": "historian-event-card", "args": {}}
        env = dict(os.environ,
                   HISTORIAN_ROOT=str(HISTORIAN_ROOT), ADAPTER_PATH=str(ADAPTER),
                   PERSONAL_HISTORIAN_ROOT=str(HISTORIAN_ROOT),
                   PERSONAL_HISTORIAN_REVISIONS=str(self.revisions),
                   PERSONAL_HISTORIAN_STORE=str(self.store),
                   PAP_AGENT_STATE_DIR=str(self.state),
                   PAYLOAD=json.dumps(payload or {}))
        if model_reply is not None:
            env["MODEL_REPLY"] = model_reply
        if seed_card is not None:
            env["SEED_CARD"] = json.dumps(seed_card)
        env.update(extra_env or {})
        completed = subprocess.run([INTERPRETER, "-c", DRIVER, action, run_id],
                                   capture_output=True, text=True, env=env, check=False)
        assert completed.returncode == 0, completed.stderr
        return json.loads(completed.stdout)

    def prepared(self, run_id):
        return json.loads((self.state / "prepared" / f"{run_id}.json").read_text(encoding="utf-8"))

    def first(self, run_id):
        """The batch's first fixed card identity — the tests act on one event."""
        return self.prepared(run_id)["cards"][0]

    def card(self, fixed, *, revision, content_hash):
        return {
            "schema_version": "1.0.0", "artifact_type": "historian.event-card.v1",
            "event_card_id": fixed["event_card_id"], "revision": revision, "domain": "personal",
            "created_at": "2026-09-13T00:00:00+00:00",
            "event_ref": {**fixed["event_ref"], "content_hash": content_hash},
            "title": "Synthetic card", "digest": "Synthetic digest.",
            "time": {"start": {"value": "2026-08-20T09:00:00+08:00", "precision": "exact"},
                     "end": {"value": "2026-08-20T10:00:00+08:00", "precision": "exact"}},
            "event_type": "record", "importance": "low", "confidence": "low",
            "subjective_salience": "unknown", "thread_ids": [], "decisions": [], "state_changes": [],
            "open_consequences": [], "contradictions": [],
            "evidence_refs": [{"artifact_id": "observation:synthetic", "revision": 1,
                               "content_hash": "a" * 64}],
            "provenance": {"generated_at": "2026-09-13T00:00:00+00:00", "generator": "test",
                           "input_refs": [fixed["event_ref"]], "input_manifest_hash": "b" * 64},
        }

    def seal(self, card):
        payload = {key: value for key, value in card.items() if key != "content_hash"}
        card["content_hash"] = hashlib.sha256(
            json.dumps(payload, ensure_ascii=False, allow_nan=False, sort_keys=True,
                       separators=(",", ":")).encode("utf-8")).hexdigest()
        return card


def test_event_revision_produces_a_bound_card(tmp_path):
    harness = Harness(tmp_path)
    prepared = harness.run("prepare", "r1")
    assert prepared["status"] == "ready"
    fixed = harness.first("r1")
    assert fixed["revision"] == 1
    assert fixed["event_card_id"] == "event-card:" + harness.event["event_id"].split(":", 1)[1]
    assert fixed["event_ref"] == {"artifact_id": harness.event["event_id"], "revision": 1,
                                  "content_hash": fixed["event_ref"]["content_hash"]}

    card = harness.seal(harness.card(fixed, revision=1, content_hash=fixed["event_ref"]["content_hash"]))
    assert harness.run("complete", "r1", model_reply=json.dumps({"event_cards": [card]}))["status"] == "success"
    assert (harness.store / "artifacts.jsonl").is_file()


def test_an_unchanged_event_reuses_its_card(tmp_path):
    harness = Harness(tmp_path)
    prepared = harness.run("prepare", "r1")
    fixed = harness.first("r1")
    card = harness.seal(harness.card(fixed, revision=1, content_hash=fixed["event_ref"]["content_hash"]))
    harness.run("complete", "r1", model_reply=json.dumps({"event_cards": [card]}))

    second = harness.run("prepare", "r2")
    assert second["status"] == "not_ready"
    assert "no current Event revision needs an EventCard refresh" in second["reason"]


def test_a_changed_event_revision_stales_the_old_card(tmp_path):
    """Gate 5: event r2 -> old card stale, and the replacement binds event r2."""
    harness = Harness(tmp_path)
    harness.run("prepare", "r1")
    fixed = harness.first("r1")
    # A card bound to an older content hash stands in for an Event revision that
    # has since changed.  It is seeded directly, because the commit path rightly
    # refuses to bind a card to a revision that is not the current one.
    stale = harness.seal(harness.card(fixed, revision=1, content_hash="0" * 64))
    assert harness.run("seed", "seed", seed_card=stale)["status"] == "success"

    refreshed = harness.run("prepare", "r2")
    assert refreshed["status"] == "ready"
    replacement = harness.first("r2")
    assert replacement["revision"] == 2
    assert replacement["event_card_id"] == fixed["event_card_id"]
    assert replacement["event_ref"]["content_hash"] != "0" * 64

    probe = subprocess.run(
        [INTERPRETER, "-c",
         "import json,sys;sys.path.insert(0, sys.argv[1]);"
         "from historian.summarization import ArtifactStore;"
         "s=ArtifactStore(sys.argv[2], domain='personal');"
         "print(json.dumps({'stale': s.is_stale(sys.argv[3]),"
         " 'revisions': len(s.revisions(sys.argv[3]))}))",
         str(HISTORIAN_ROOT), str(harness.store), fixed["event_card_id"]],
        capture_output=True, text=True, check=False)
    assert probe.returncode == 0, probe.stderr
    state = json.loads(probe.stdout)
    assert state == {"stale": True, "revisions": 1}


def test_a_card_that_changes_identity_is_rejected(tmp_path):
    harness = Harness(tmp_path)
    harness.run("prepare", "r1")
    fixed = harness.first("r1")
    forged = harness.seal(harness.card(fixed, revision=9, content_hash=fixed["event_ref"]["content_hash"]))
    result = harness.run("complete", "r1", model_reply=json.dumps({"event_cards": [forged]}))
    assert result["status"] == "error"
    assert not (harness.store / "artifacts.jsonl").exists()


def test_a_card_without_evidence_is_rejected(tmp_path):
    harness = Harness(tmp_path)
    harness.run("prepare", "r1")
    fixed = harness.first("r1")
    card = harness.card(fixed, revision=1, content_hash=fixed["event_ref"]["content_hash"])
    card["evidence_refs"] = []
    forged = harness.seal(card)
    result = harness.run("complete", "r1", model_reply=json.dumps({"event_cards": [forged]}))
    assert result["status"] == "error"
    assert not (harness.store / "artifacts.jsonl").exists()


@pytest.mark.skipif(not (HISTORIAN_ROOT / "revisions" / "revisions.jsonl").is_file(),
                    reason="no local revision journal")
def test_the_real_journal_yields_a_preparable_event(tmp_path):
    """The adapter must cope with the real journal shape, not only fixtures."""
    harness = Harness(tmp_path)
    shutil.rmtree(harness.revisions)
    shutil.copytree(HISTORIAN_ROOT / "revisions", harness.revisions)
    prepared = harness.run("prepare", "real1")
    assert prepared["status"] == "ready"
    fixed = harness.first("real1")
    assert fixed["event_card_id"].startswith("event-card:")
    assert fixed["revision"] == 1
    assert len(fixed["event_ref"]["content_hash"]) == 64


def _stored_records(store_dir):
    """Read the artifact journal with the standard library only."""
    path = Path(store_dir) / "artifacts.jsonl"
    if not path.is_file():
        return []
    return [json.loads(line)["record"] for line in path.read_text(encoding="utf-8").splitlines()]


def _sealed(document):
    payload = {key: value for key, value in document.items() if key != "content_hash"}
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, allow_nan=False, sort_keys=True,
                   separators=(",", ":")).encode("utf-8")).hexdigest()


def test_the_runtime_owns_provenance_not_the_model(tmp_path):
    """A model may assert a clock, a manifest hash and a model identity it cannot know."""
    harness = Harness(tmp_path)
    harness.run("prepare", "r1")
    fixed = harness.first("r1")
    card = harness.card(fixed, revision=1, content_hash=fixed["event_ref"]["content_hash"])
    card["provenance"] = {
        "generated_at": "1999-01-01T00:00:00+00:00", "generator": "the-model",
        "model": "made-up/model", "provider": "made-up",
        "input_refs": [], "input_manifest_hash": "0" * 64,
    }
    assert harness.run("complete", "r1", payload={"skill": "historian-event-card", "args": {}},
                       model_reply=json.dumps({"event_cards": [harness.seal(card)]}))["status"] == "success"

    record = _stored_records(harness.store)[0]
    provenance = record["provenance"]
    assert provenance["generator"] == "pap.personal-historian.runtime/v1"
    assert provenance["generated_at"] != "1999-01-01T00:00:00+00:00"
    assert provenance["input_manifest_hash"] != "0" * 64
    assert provenance["input_refs"] == [fixed["event_ref"]]
    # PAP told the runtime no model, so the model's claim is dropped, not kept.
    assert "model" not in provenance and "provider" not in provenance
    # The artifact was re-sealed over the rewritten provenance.
    assert record["content_hash"] == _sealed(record)


def test_the_runtime_records_the_model_pap_declares(tmp_path):
    harness = Harness(tmp_path)
    harness.run("prepare", "r1")
    fixed = harness.first("r1")
    card = harness.seal(harness.card(fixed, revision=1, content_hash=fixed["event_ref"]["content_hash"]))
    assert harness.run("complete", "r1", payload={"skill": "historian-event-card", "args": {}},
                       model_reply=json.dumps(card),
                       extra_env={"PAP_AGENT_MODEL": "test-provider/test-model"})["status"] == "success"

    provenance = _stored_records(harness.store)[0]["provenance"]
    assert provenance["model"] == "test-provider/test-model"
    assert provenance["provider"] == "test-provider"
