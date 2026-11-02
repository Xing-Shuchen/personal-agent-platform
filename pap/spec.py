"""Loading and validation of declarative ``pap/v1`` Agent specs."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import yaml

from .schedule import ScheduleError, validate_schedule

API_VERSION = "pap/v1"
NAME_RE = re.compile(r"^[a-z][a-z0-9-]*$")


class SpecError(ValueError):
    """Raised when an agent spec is invalid."""


@dataclass
class ProactiveJob:
    name: str
    schedule: str
    skill: str
    args: dict[str, Any] = field(default_factory=dict)
    attach_to_session: bool = True
    delivery: str = "user-home"
    delivery_target: str | None = None
    delivery_channel: str | None = None
    delivery_account: str | None = None
    runtime: str | None = None
    timezone: str | None = None
    deliver_at: str | None = None
    # A synthesis job may need a stronger model than the agent's routine work.
    # When absent, the agent-level model remains the policy default.
    model: str | None = None
    runner: str = "openclaw"
    command: list[str] | None = None
    notify: dict[str, str] | None = None
    #: §40 stages a rollout: a declared job may exist, be visible and be audited
    #: while not yet scheduled. Disabling is not deleting — the declaration and
    #: its schedule stay in the spec so enabling is a one-line change.
    enabled: bool = True
    requires_env: list[str] = field(default_factory=list)


@dataclass
class AgentSpec:
    name: str
    description: str
    profile_name: str
    enabled: bool = True
    capabilities: list[str] = field(default_factory=list)
    proactive_enabled: bool = False
    proactive_class: str | None = None
    jobs: list[ProactiveJob] = field(default_factory=list)
    private_state: list[str] = field(default_factory=list)
    model: str | None = None
    #: §35: PAP owns model policy, but a route may be configured with a fallback
    #: chain in OpenClaw itself.  Pinning the model on the command line is a
    #: strict one-off selection that skips that chain, so an agent that wants the
    #: configured chain opts in here and runs without the override.
    model_fallback: bool = False
    provider_rejection_fallback: str | None = None
    source_path: Path | None = None


def _err(spec_path: Path, msg: str) -> SpecError:
    return SpecError(f"{spec_path}: {msg}")


def _require(spec_path: Path, obj: dict[str, Any], key: str, where: str) -> Any:
    if key not in obj or obj[key] is None:
        raise _err(spec_path, f"{where}: missing required key '{key}'")
    return obj[key]


def _is_provider_model(value: Any) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[^/\s]+/[^/\s]+", value) is not None


def parse_deliver_at(value: str) -> tuple[int, int, str | None]:
    """Validate and split a deferred-delivery local clock value."""
    match = re.fullmatch(r"(\d{2}):(\d{2})(?: tz (\S+))?", value)
    if not match:
        raise ValueError("must be 'HH:MM' or 'HH:MM tz Area/Location'")
    hour, minute = int(match.group(1)), int(match.group(2))
    if hour > 23 or minute > 59:
        raise ValueError("hour must be 00-23 and minute must be 00-59")
    zone = match.group(3)
    if zone:
        try:
            ZoneInfo(zone)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError(f"unknown timezone {zone!r}") from exc
    return hour, minute, zone


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
    agent_enabled = spec.get("enabled", True)
    if not isinstance(agent_enabled, bool):
        raise _err(path, "spec.enabled: must be a boolean")

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
                try:
                    validate_schedule(schedule)
                except (ScheduleError, TypeError) as exc:
                    raise _err(
                        path,
                        f"{where}.schedule: {exc}; got {schedule!r}",
                    ) from exc
                skill = _require(path, raw, "skill", where)
                if not isinstance(skill, str) or not skill.strip():
                    raise _err(path, f"{where}.skill: must be a non-empty string")
                job_args = raw.get("args", {})
                if not isinstance(job_args, dict) or not all(
                    isinstance(key, str) and key for key in job_args
                ):
                    raise _err(path, f"{where}.args: must be a mapping with string keys")
                enabled = raw.get("enabled", True)
                if not isinstance(enabled, bool):
                    raise _err(path, f"{where}.enabled: must be a boolean")
                requires_env = raw.get("requires_env", [])
                if not isinstance(requires_env, list) or not all(
                    isinstance(key, str) and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key)
                    for key in requires_env
                ):
                    raise _err(path, f"{where}.requires_env: must be a list of environment variable names")
                delivery = raw.get("delivery", "user-home")
                if delivery not in ("user-home", "origin", "local"):
                    raise _err(path, f"{where}.delivery: unknown delivery {delivery!r}")
                for key in ("delivery_target", "delivery_channel", "delivery_account"):
                    if key in raw and (not isinstance(raw[key], str) or not raw[key].strip()):
                        raise _err(path, f"{where}.{key}: must be a non-empty string")
                notify = raw.get("notify")
                if notify is not None:
                    if not isinstance(notify, dict):
                        raise _err(path, f"{where}.notify: must be a mapping")
                    expected_notify_keys = {"channel", "account", "target"}
                    unknown = set(notify) - expected_notify_keys
                    if unknown:
                        raise _err(path, f"{where}.notify: unknown key {sorted(unknown)[0]!r}")
                    for key in expected_notify_keys:
                        value = notify.get(key)
                        if not isinstance(value, str) or not value.strip():
                            raise _err(path, f"{where}.notify: {key} must be a non-empty string")
                runtime = raw.get("runtime")
                if runtime is not None and (not isinstance(runtime, str) or not NAME_RE.match(runtime)):
                    raise _err(path, f"{where}.runtime: must be a runtime identifier or null")
                timezone = raw.get("timezone")
                if timezone is not None:
                    if not isinstance(timezone, str) or not timezone:
                        raise _err(path, f"{where}.timezone: must be an IANA timezone")
                    try:
                        ZoneInfo(timezone)
                    except ZoneInfoNotFoundError as exc:
                        raise _err(path, f"{where}.timezone: unknown timezone {timezone!r}") from exc
                deliver_at = raw.get("deliver_at")
                if deliver_at is not None:
                    if not isinstance(deliver_at, str):
                        raise _err(path, f"{where}.deliver_at: must be 'HH:MM' or 'HH:MM tz Area/Location'")
                    try:
                        parse_deliver_at(deliver_at)
                    except ValueError as exc:
                        raise _err(path, f"{where}.deliver_at: {exc}") from exc
                job_model = raw.get("model")
                if job_model is not None and (
                    not isinstance(job_model, str) or not job_model.strip()
                ):
                    raise _err(path, f"{where}.model: must be a non-empty string")
                job_runner = raw.get("runner", "openclaw")
                if job_runner not in ("openclaw", "codex", "opencode", "command"):
                    raise _err(path, f"{where}.runner: must be 'openclaw', 'codex', 'opencode', or 'command'")
                command = raw.get("command")
                if job_runner == "command":
                    if not isinstance(command, list) or not command or not all(
                        isinstance(item, str) and item for item in command
                    ):
                        raise _err(path, f"{where}.command: required for runner 'command' and must be a non-empty list of non-empty strings")
                    if runtime is not None:
                        raise _err(path, f"{where}.runtime: cannot be set with runner 'command'")
                    if job_model is not None:
                        raise _err(path, f"{where}.model: cannot be set with runner 'command'")
                elif command is not None:
                    raise _err(path, f"{where}.command: can only be set with runner 'command'")
                if job_runner == "opencode":
                    # OpenCode's CLI selection is provider/model; do not let an
                    # ambiguous agent-level default silently select a model.
                    if not isinstance(job_model, str) or job_model.count("/") != 1 or any(
                        not part.strip() for part in job_model.split("/", 1)
                    ):
                        raise _err(path, f"{where}.model: required for runner 'opencode' and must be '<provider>/<model>'")
                    # ``attach_to_session`` is OpenClaw-specific and is ignored
                    # by OpenCode's isolated one-shot ``run`` invocation.
                jobs.append(
                    ProactiveJob(
                        name=jname,
                        schedule=schedule,
                        skill=skill,
                        args=dict(job_args),
                        attach_to_session=bool(raw.get("attach_to_session", True)),
                        delivery=delivery,
                        delivery_target=raw.get("delivery_target"),
                        delivery_channel=raw.get("delivery_channel"),
                        delivery_account=raw.get("delivery_account"),
                        runtime=runtime,
                        timezone=timezone,
                        deliver_at=deliver_at,
                        model=job_model,
                        runner=job_runner,
                        command=list(command) if command is not None else None,
                        notify=dict(notify) if notify is not None else None,
                        enabled=enabled,
                        requires_env=list(requires_env),
                    )
                )
        elif proactive.get("desired_jobs"):
            raise _err(path, "spec.proactive: desired_jobs set but enabled is false")

    private_state = spec.get("state", {}).get("private", []) if isinstance(spec.get("state"), dict) else []
    if not isinstance(private_state, list) or not all(isinstance(s, str) and s for s in private_state):
        raise _err(path, "spec.state.private: must be a list of non-empty strings")

    model = spec.get("model")
    if model is not None and (not isinstance(model, str) or not model.strip()):
        raise _err(path, "spec.model: must be a non-empty string in 'provider/model' form")

    model_fallback = spec.get("model_fallback", False)
    if not isinstance(model_fallback, bool):
        raise _err(path, "spec.model_fallback: must be a boolean")

    provider_rejection_fallback = spec.get("provider_rejection_fallback")
    if provider_rejection_fallback is not None and not _is_provider_model(provider_rejection_fallback):
        raise _err(path, "spec.provider_rejection_fallback: must be a non-empty string in 'provider/model' form")

    return AgentSpec(
        name=name,
        description=description,
        profile_name=profile_name,
        enabled=agent_enabled,
        capabilities=list(capabilities),
        proactive_enabled=proactive_enabled,
        proactive_class=proactive_class,
        jobs=jobs,
        private_state=list(private_state),
        model=model,
        model_fallback=model_fallback,
        provider_rejection_fallback=provider_rejection_fallback,
        source_path=path,
    )


def _apply_job_overrides(
    local_config: Path, agent_name: str, spec: AgentSpec, jobs_override: Any
) -> None:
    """Apply ignored local per-job model and delivery routing overrides."""
    if jobs_override is None:
        return
    if not isinstance(jobs_override, dict):
        raise SpecError(f"{local_config}: {agent_name}: jobs must be a mapping of job name to overrides")
    jobs_by_name = {job.name: job for job in spec.jobs}
    for job_name, job_config in jobs_override.items():
        job = jobs_by_name.get(job_name)
        if job is None or not isinstance(job_config, dict):
            raise SpecError(f"{local_config}: {agent_name}: unknown job or invalid job config: {job_name!r}")
        delivery_keys = {"delivery_target", "delivery_channel", "delivery_account"}
        unknown = set(job_config) - {"model"} - delivery_keys
        if unknown:
            raise SpecError(
                f"{local_config}: {agent_name}: {job_name}: unknown job override keys: {sorted(unknown)}"
            )
        for key in sorted(delivery_keys):
            if key in job_config:
                value = job_config[key]
                if not isinstance(value, str) or not value.strip():
                    raise SpecError(f"{local_config}: {agent_name}: {job_name}: {key} must be a non-empty string")
                setattr(job, key, value)
        model = job_config.get("model")
        if model is None:
            continue
        if not isinstance(model, str) or not model.strip():
            raise SpecError(f"{local_config}: {agent_name}: {job_name}: model must be a non-empty string")
        if job.runner == "command":
            raise SpecError(f"{local_config}: {agent_name}: {job_name}: model cannot be set for runner 'command'")
        if job.runner == "opencode" and not _is_provider_model(model):
            raise SpecError(
                f"{local_config}: {agent_name}: {job_name}: "
                "model must be '<provider>/<model>' for runner 'opencode'"
            )
        job.model = model


def load_platform(root: Path) -> list[AgentSpec]:
    """Load every agents/*/agent.yaml under *root*, sorted by name."""
    root = Path(root)
    agents_dir = root / "agents"
    if not agents_dir.is_dir():
        raise SpecError(f"no agents/ directory under {root}")
    specs = []
    for agent_yaml in sorted(agents_dir.glob("*/agent.yaml")):
        loaded = load_spec(agent_yaml)
        for job in loaded.jobs:
            skill_file = agent_yaml.parent / "profile" / "skills" / job.skill / "SKILL.md"
            if not skill_file.is_file():
                raise _err(agent_yaml, f"job {job.name!r}: skill file not found: {skill_file}")
            if job.runtime is not None:
                # A declared runtime adapter is part of the job contract; catch a
                # missing one at validate time instead of mid-tick at invoke time.
                runtime_file = agent_yaml.parent / "runtime" / f"{job.runtime}.py"
                if not runtime_file.is_file():
                    raise _err(agent_yaml, f"job {job.name!r}: runtime adapter not found: {runtime_file}")
        specs.append(loaded)
    # Machine-local activation is stored under var/, which is excluded from Git.
    local_config = root / "var" / "config" / "agents.yaml"
    if local_config.exists():
        try:
            overrides = yaml.safe_load(local_config.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError as exc:
            raise SpecError(f"{local_config}: invalid YAML: {exc}") from exc
        if not isinstance(overrides, dict) or not isinstance(overrides.get("agents", {}), dict):
            raise SpecError(f"{local_config}: expected agents mapping")
        by_name = {item.name: item for item in specs}
        for name, config in overrides.get("agents", {}).items():
            if name not in by_name or not isinstance(config, dict):
                raise SpecError(f"{local_config}: unknown agent or invalid config: {name!r}")
            unknown = set(config) - {"enabled", "provider_rejection_fallback", "jobs"}
            if unknown:
                raise SpecError(f"{local_config}: {name}: unknown override keys: {sorted(unknown)}")
            if not isinstance(config.get("enabled"), bool):
                raise SpecError(f"{local_config}: {name}: enabled must be a boolean")
            provider_rejection_fallback = config.get("provider_rejection_fallback")
            if provider_rejection_fallback is not None and not _is_provider_model(provider_rejection_fallback):
                raise SpecError(
                    f"{local_config}: {name}: provider_rejection_fallback: "
                    "must be a non-empty string in 'provider/model' form"
                )
            by_name[name].enabled = config["enabled"]
            if provider_rejection_fallback is not None:
                by_name[name].provider_rejection_fallback = provider_rejection_fallback
            _apply_job_overrides(local_config, name, by_name[name], config.get("jobs"))
    if not specs:
        raise SpecError(f"no agent.yaml files found under {agents_dir}")
    names = [s.name for s in specs]
    dupes = {n for n in names if names.count(n) > 1}
    if dupes:
        raise SpecError(f"duplicate agent names across agents/: {sorted(dupes)}")
    return specs
