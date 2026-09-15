"""The skills' output contracts must match the schemas that judge them.

The skills are the only thing telling the model what to emit. They are also the
one part of the system that no validator reads, so a schema can gain a required
field and every model reply then fails with no hint that the instruction is stale.
These tests pin the contract to the schema.

Hermetic: the schemas are read from the historian checkout, no model runs.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

REPO = Path(__file__).parents[1]
PROFILE = REPO / "agents/personal-historian/profile"
HISTORIAN_ROOT = Path(os.environ.get("PERSONAL_HISTORIAN_ROOT", REPO.parent / "personal-historian-handoff"))
SCHEMAS = HISTORIAN_ROOT / "schemas"

#: skill -> (contract file, schema, artifact type)
CONTRACTS = {
    "historian-event-card": (
        PROFILE / "skills/historian-event-card/SKILL.md", "event-card.v1.schema.json",
        "historian.event-card.v1"),
    "historian-thread-card": (
        PROFILE / "skills/historian-thread-card/SKILL.md", "thread-card.v1.schema.json",
        "historian.thread-card.v1"),
    "historian-period-summary": (
        PROFILE / "skills/historian-period-summary/references/output-contract.md",
        "period-summary.v1.schema.json", "historian.period-summary.v1"),
}

pytestmark = pytest.mark.skipif(not SCHEMAS.is_dir(), reason="historian checkout unavailable")


def _schema(name):
    return json.loads((SCHEMAS / name).read_text(encoding="utf-8"))


def _enum_values(schema) -> set[str]:
    """Every enum literal the schema declares, so a value is not read as a field."""

    values: set[str] = set()
    for node in [*schema.get("properties", {}).values(), *schema.get("$defs", {}).values()]:
        if isinstance(node, dict) and isinstance(node.get("enum"), list):
            values.update(item for item in node["enum"] if isinstance(item, str))
    return values


def _flatten(text: str) -> str:
    """Contract prose wraps; compare against unwrapped text."""
    return " ".join(text.split())


@pytest.mark.parametrize("skill", sorted(CONTRACTS))
def test_the_contract_names_every_required_field(skill):
    path, schema_name, _ = CONTRACTS[skill]
    required = _schema(schema_name)["required"]
    text = path.read_text(encoding="utf-8")
    missing = [field for field in required if f"`{field}`" not in text]
    assert missing == [], f"{path.name} does not name: {', '.join(missing)}"


@pytest.mark.parametrize("skill", sorted(CONTRACTS))
def test_the_contract_names_no_field_the_schema_rejects(skill):
    path, schema_name, _ = CONTRACTS[skill]
    properties = set(_schema(schema_name)["properties"])
    text = path.read_text(encoding="utf-8")
    # Every backticked field-like token inside the contract must be a real field.
    for token in _contract_fields(text):
        assert token in properties or token in _enum_values(_schema(schema_name)), (
            f"{path.name} names unknown field {token!r}")


@pytest.mark.parametrize("skill", sorted(CONTRACTS))
def test_the_contract_states_the_artifact_type_and_schema_version(skill):
    path, schema_name, artifact_type = CONTRACTS[skill]
    schema = _schema(schema_name)
    text = path.read_text(encoding="utf-8")
    assert artifact_type in text
    assert schema["properties"]["schema_version"]["const"] in text
    assert schema["properties"]["artifact_type"]["const"] == artifact_type


@pytest.mark.parametrize("skill", sorted(CONTRACTS))
def test_the_contract_says_unknown_fields_are_rejected(skill):
    path, schema_name, _ = CONTRACTS[skill]
    assert _schema(schema_name).get("additionalProperties") is False
    flattened = _flatten(path.read_text(encoding="utf-8")).lower()
    assert "unknown fields" in flattened and "reject" in flattened


def test_enum_values_stated_for_thread_status_match_the_schema():
    path, schema_name, _ = CONTRACTS["historian-thread-card"]
    statuses = _schema(schema_name)["properties"]["status"]["enum"]
    text = path.read_text(encoding="utf-8")
    flattened = _flatten(text)
    start = flattened.index("`status` (")
    stated = flattened[start:flattened.index(")", start)]
    for status in statuses:
        assert status in stated, status


def test_enum_values_stated_for_period_status_match_the_schema():
    path, schema_name, _ = CONTRACTS["historian-period-summary"]
    statuses = _schema(schema_name)["properties"]["status"]["enum"]
    text = path.read_text(encoding="utf-8")
    flattened = _flatten(text)
    start = flattened.index("| `status` |")
    stated = flattened[start:flattened.index("|", start + 12)]
    for status in statuses:
        assert status in stated, status


def test_every_level_reference_carries_its_digest_range():
    """§19's soft limits belong where the model reads level guidance."""
    expected = {"weekly.md": "300-700", "monthly.md": "400-900",
                "quarterly.md": "500-1200", "halfyear.md": "600-1500"}
    for name, span in expected.items():
        text = (PROFILE / "skills/historian-period-summary/references" / name).read_text(encoding="utf-8")
        assert span in text, name
        assert "next_level_digest" in text, name


def test_the_period_summary_contract_states_what_the_digest_must_preserve():
    text = (PROFILE / "skills/historian-period-summary/references/output-contract.md").read_text(
        encoding="utf-8")
    for required in ("major state transitions", "major decisions", "thread lifecycle changes",
                     "inflection points", "important unresolved issues"):
        assert required in text, required
    assert "not a shorter `overview`" in text


def test_literary_renderer_is_a_human_view_with_a_canonical_boundary():
    path = PROFILE / "skills/historian-literary-renderer/SKILL.md"
    text = path.read_text(encoding="utf-8")
    assert "human-facing" in text
    assert "MUST NOT introduce" in text
    assert "artifact IDs" in text
    assert "runtime owns" in text
    weekly = (path.parent / "references/weekly.md").read_text(encoding="utf-8")
    for role in ("主线", "副线", "背景"):
        assert role in weekly
    assert "first person" in weekly
    assert "relationship, care, travel" in weekly
    assert "audit appendix" in weekly


def _contract_fields(text: str) -> list[str]:
    """Backticked snake_case tokens that look like schema fields."""

    fields = []
    for line in text.splitlines():
        for token in line.split("`")[1::2]:
            if token and "_" in token and token.islower() and token.replace("_", "").isalnum():
                fields.append(token)
    return fields


def test_the_event_card_skill_describes_the_batch_protocol():
    """The runtime asks for a batch; the skill is what tells the model so."""
    text = (PROFILE / "skills/historian-event-card/SKILL.md").read_text(encoding="utf-8")
    assert '"event_cards"' in text or "event_cards" in text
    assert "one card per" in text.lower()
    for field in ("event_ref", "event_card_id", "revision"):
        assert field in text, field


def test_the_event_card_batch_is_bounded():
    """A batch must stay a sane prompt, so the bound is declared, not implied."""
    source = (REPO / "agents/personal-historian/runtime/historian.py").read_text(encoding="utf-8")
    assert "EVENT_BATCH_MAX =" in source
    assert "EVENT_BATCH_MAX_CHARS =" in source


def test_every_skill_says_the_reply_is_the_artifact():
    """§16/§21: the model drafts, the runtime persists.

    `historian-period-summary` used to tell the model to run `historian summary
    commit` itself. A real run obeyed: it committed revision 1 by hand and then
    the runtime refused its reply ("must use revision 2, got 1"). The revision
    was spent and the run failed, while the artifact it wrote carried a
    hand-written `generator` claiming the runtime had produced it — provenance
    no runtime could substantiate. Every skill must say the opposite.
    """

    for skill in ("historian-event-card", "historian-thread-card", "historian-period-summary"):
        text = (PROFILE / "skills" / skill / "SKILL.md").read_text(encoding="utf-8")
        # Line wrapping must not decide whether the contract is stated.
        flattened = " ".join(text.split())
        for clause in (
            "Do not run commands",
            "do not write or edit any file",
            "do not modify, commit to, or push any repository",
        ):
            assert clause in flattened, f"{skill}: {clause}"
        # The instruction that caused it, verbatim. Naming the commands in the
        # prohibition is fine; handing them to the model as its job is not.
        assert "The Historian owns persistence" not in flattened, skill
        assert "Use its `historian summary" not in flattened, skill
        assert "operations with the configured local Historian" not in flattened, skill


def test_the_runtime_owns_provenance_for_every_summary_artifact():
    """§21: only the runtime may claim what the runtime can substantiate."""
    source = (REPO / "agents/personal-historian/runtime/historian.py").read_text(encoding="utf-8")
    assert "seal_with_provenance" in source
    assert "pap.personal-historian.runtime/v1" in source
