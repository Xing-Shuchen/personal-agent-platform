"""Lightweight append-only artifacts shared across agents.

An artifact is the smallest durable unit agents can publish for each other:
an id, a type, a producer, a timestamp, a payload, and provenance. v0.1 keeps
them in one append-only JSONL file (``var/state/artifacts.jsonl``) with no
delivery machinery — consumers scan by type or producer.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .state import append_jsonl, read_jsonl
from paplog import observe as paplog
from paplog.core import git_provenance, ulid

DEFAULT_ARTIFACT_LOG = Path("var/state/artifacts.jsonl")

RESERVED_FIELDS = frozenset({"id", "type", "producer", "created_at", "provenance"})


class ArtifactError(ValueError):
    """Raised when an artifact record would be malformed."""


def _now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _payload_fingerprint(payload: dict[str, Any]) -> dict[str, Any]:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {"payload_sha256": hashlib.sha256(raw).hexdigest(), "payload_bytes": len(raw)}


@dataclass
class Artifact:
    id: str
    type: str
    producer: str
    created_at: str
    payload: dict[str, Any] = field(default_factory=dict)
    provenance: dict[str, Any] = field(default_factory=dict)


def new_artifact_id(artifact_type: str, now: datetime | None = None) -> str:
    safe_type = "".join(c if c.isalnum() or c in "-_" else "_" for c in artifact_type)
    return f"art_{safe_type}_{ulid(now or datetime.now(timezone.utc))}"


def append(
    artifact_type: str,
    producer: str,
    payload: dict[str, Any] | None = None,
    *,
    provenance: dict[str, Any] | None = None,
    log_path: Path | str | None = None,
    artifact_id: str | None = None,
    created_at: str | None = None,
) -> Artifact:
    """Validate and append one artifact; returns the persisted record."""
    if not isinstance(artifact_type, str) or not artifact_type.strip():
        raise ArtifactError("artifact type must be a non-empty string")
    if not isinstance(producer, str) or not producer.strip():
        raise ArtifactError("artifact producer must be a non-empty string")
    if payload is not None and not isinstance(payload, dict):
        raise ArtifactError("artifact payload must be a JSON object")
    if provenance is not None and not isinstance(provenance, dict):
        raise ArtifactError("artifact provenance must be a JSON object")

    record = Artifact(
        id=artifact_id or new_artifact_id(artifact_type),
        type=artifact_type,
        producer=producer,
        created_at=created_at or _now(),
        payload=dict(payload or {}),
        provenance=dict(provenance or {}),
    )
    artifact_path = Path(log_path or DEFAULT_ARTIFACT_LOG)
    def write_record() -> None:
        append_jsonl(artifact_path, {
            "id": record.id,
            "type": record.type,
            "producer": record.producer,
            "created_at": record.created_at,
            "payload": record.payload,
            "provenance": record.provenance,
        })
    if os.environ.get("PAP_RUN_ID") or os.environ.get("PAP_OBSERVABILITY_DIR"):
        with paplog.action("pap.filesystem.write", effect="create", scope="local",
                           subject={"type": "artifact_log", "id": str(artifact_path)},
                           attributes={"bytes": len(json.dumps(record.payload, ensure_ascii=False).encode("utf-8"))}):
            write_record()
    else:
        write_record()
    links = []
    for ref in record.provenance.get("input_refs", []):
        if isinstance(ref, dict) and isinstance(ref.get("artifact_id"), str):
            links.append({"type": "derived_from", "target_type": "artifact", "target_id": ref["artifact_id"]})
    paplog.event("pap.artifact.created", subject={"type": record.type, "id": record.id},
                 links=links, actor={"type": "agent", "id": record.producer},
                 attributes={"uri": str(artifact_path), "provenance_keys": sorted(record.provenance),
                             **_payload_fingerprint(record.payload)}, **git_provenance(Path.cwd()))
    return record


def artifacts(
    log_path: Path | str | None = None,
    *,
    artifact_type: str | None = None,
    producer: str | None = None,
) -> list[dict[str, Any]]:
    """Read artifacts, optionally filtered by type or producer."""
    artifact_path = Path(log_path or DEFAULT_ARTIFACT_LOG)
    if os.environ.get("PAP_RUN_ID") or os.environ.get("PAP_OBSERVABILITY_DIR"):
        with paplog.action("pap.filesystem.read", effect="read", scope="local",
                           subject={"type": "artifact_log", "id": str(artifact_path)}):
            records = read_jsonl(artifact_path)
    else:
        records = read_jsonl(artifact_path)
    if artifact_type is not None:
        records = [r for r in records if r.get("type") == artifact_type]
    if producer is not None:
        records = [r for r in records if r.get("producer") == producer]
    return records
