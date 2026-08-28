"""Loading and validation of declarative ``pap/v1`` Agent specs."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

API_VERSION = "pap/v1"
NAME_RE = re.compile(r"^[a-z][a-z0-9-]*$")
SCHEDULE_RE = re.compile(r"^(every \d+[smhd]|\d{2}:\d{2}(\s+\S+)*|cron .+)$")


class SpecError(ValueError):
    """Raised when an agent spec is invalid."""


@dataclass
class ProactiveJob:
    name: str
    schedule: str
    skill: str
    attach_to_session: bool = True
    delivery: str = "user-home"


@dataclass
class AgentSpec:
    name: str
    description: str
    profile_name: str
    capabilities: list[str] = field(default_factory=list)
    proactive_enabled: bool = False
    proactive_class: str | None = None
    jobs: list[ProactiveJob] = field(default_factory=list)
    private_state: list[str] = field(default_factory=list)
    source_path: Path | None = None


def _err(spec_path: Path, msg: str) -> SpecError:
    return SpecError(f"{spec_path}: {msg}")


def _require(spec_path: Path, obj: dict[str, Any], key: str, where: str) -> Any:
    if key not in obj or obj[key] is None:
        raise _err(spec_path, f"{where}: missing required key '{key}'")
    return obj[key]


def load_spec(path: Path) -> AgentSpec:
    """Parse and validate a single agent.yaml file."""
    path = Path(path)
    try:
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        raise SpecError(f"{path}: invalid YAML: {e}") from e
    if not isinstance(doc, dict):
        raise _err(path, "top level must be a mapping")

    if doc.get("apiVersion") != API_VERSION:
        raise _err(path, f"apiVersion must be '{API_VERSION}', got {doc.get('apiVersion')!r}")
    if doc.get("kind") != "Agent":
        raise _err(path, f"kind must be 'Agent', got {doc.get('kind')!r}")

    meta = doc.get("metadata")
    if not isinstance(meta, dict):
        raise _err(path, "metadata: must be a mapping")
    name = _require(path, meta, "name", "metadata")
    if not isinstance(name, str) or not NAME_RE.match(name):
        raise _err(path, f"metadata.name: must match {NAME_RE.pattern}, got {name!r}")
    description = _require(path, meta, "description", "metadata")
    if not isinstance(description, str) or not description.strip():
        raise _err(path, "metadata.description: must be a non-empty string")

    spec = doc.get("spec")
    if not isinstance(spec, dict):
        raise _err(path, "spec: must be a mapping")

    profile = spec.get("profile")
    if not isinstance(profile, dict):
        raise _err(path, "spec.profile: must be a mapping")
    profile_name = _require(path, profile, "name", "spec.profile")
    if not isinstance(profile_name, str) or not profile_name.strip():
        raise _err(path, "spec.profile.name: must be a non-empty string")
    source = profile.get("source", "profile")
    if source != "profile":
        raise _err(path, f"spec.profile.source: only 'profile' is supported, got {source!r}")

    capabilities = spec.get("capabilities", [])
    if not isinstance(capabilities, list) or not all(isinstance(c, str) and c for c in capabilities):
        raise _err(path, "spec.capabilities: must be a list of non-empty strings")
    if len(set(capabilities)) != len(capabilities):
        raise _err(path, "spec.capabilities: duplicates are not allowed")

    jobs: list[ProactiveJob] = []
    proactive_enabled = False
    proactive_class = None
    proactive = spec.get("proactive")
    if proactive is not None:
        if not isinstance(proactive, dict):
            raise _err(path, "spec.proactive: must be a mapping")
        proactive_enabled = bool(proactive.get("enabled", False))
        if proactive_enabled:
            proactive_class = proactive.get("class")
            if proactive_class not in ("conversational", "ambient"):
                raise _err(
                    path,
                    "spec.proactive.class: must be 'conversational' or 'ambient' "
                    f"when enabled, got {proactive_class!r}",
                )
            raw_jobs = proactive.get("desired_jobs", [])
            if not isinstance(raw_jobs, list):
                raise _err(path, "spec.proactive.desired_jobs: must be a list")
            seen_jobs: set[str] = set()
            for i, raw in enumerate(raw_jobs):
                where = f"spec.proactive.desired_jobs[{i}]"
                if not isinstance(raw, dict):
                    raise _err(path, f"{where}: must be a mapping")
                jname = _require(path, raw, "name", where)
                if not isinstance(jname, str) or not NAME_RE.match(jname):
                    raise _err(path, f"{where}.name: invalid job name {jname!r}")
                if jname in seen_jobs:
                    raise _err(path, f"{where}.name: duplicate job {jname!r}")
                seen_jobs.add(jname)
                schedule = _require(path, raw, "schedule", where)
                if not isinstance(schedule, str) or not SCHEDULE_RE.match(schedule):
                    raise _err(
                        path,
                        f"{where}.schedule: expected 'every Ns/m/h/d', 'HH:MM [tz ...]' "
                        f"or 'cron ...', got {schedule!r}",
                    )
                skill = _require(path, raw, "skill", where)
                if not isinstance(skill, str) or not skill.strip():
                    raise _err(path, f"{where}.skill: must be a non-empty string")
                delivery = raw.get("delivery", "user-home")
                if delivery not in ("user-home", "origin", "local"):
                    raise _err(path, f"{where}.delivery: unknown delivery {delivery!r}")
                jobs.append(
                    ProactiveJob(
                        name=jname,
                        schedule=schedule,
                        skill=skill,
                        attach_to_session=bool(raw.get("attach_to_session", True)),
                        delivery=delivery,
                    )
                )
        elif proactive.get("desired_jobs"):
            raise _err(path, "spec.proactive: desired_jobs set but enabled is false")

    private_state = spec.get("state", {}).get("private", []) if isinstance(spec.get("state"), dict) else []
    if not isinstance(private_state, list) or not all(isinstance(s, str) and s for s in private_state):
        raise _err(path, "spec.state.private: must be a list of non-empty strings")

    return AgentSpec(
        name=name,
        description=description,
        profile_name=profile_name,
        capabilities=list(capabilities),
        proactive_enabled=proactive_enabled,
        proactive_class=proactive_class,
        jobs=jobs,
        private_state=list(private_state),
        source_path=path,
    )


def load_platform(root: Path) -> list[AgentSpec]:
    """Load every agents/*/agent.yaml under *root*, sorted by name."""
    root = Path(root)
    agents_dir = root / "agents"
    if not agents_dir.is_dir():
        raise SpecError(f"no agents/ directory under {root}")
    specs = []
    for agent_yaml in sorted(agents_dir.glob("*/agent.yaml")):
        specs.append(load_spec(agent_yaml))
    if not specs:
        raise SpecError(f"no agent.yaml files found under {agents_dir}")
    names = [s.name for s in specs]
    dupes = {n for n in names if names.count(n) > 1}
    if dupes:
        raise SpecError(f"duplicate agent names across agents/: {sorted(dupes)}")
    return specs
