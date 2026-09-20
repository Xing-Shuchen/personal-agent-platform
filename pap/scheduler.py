"""Platform scheduler: resolve due manifest jobs and invoke their skills."""

from __future__ import annotations

import fcntl
import hashlib
import os
import secrets
import subprocess
import re
import time
from contextlib import contextmanager, nullcontext
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Iterator

from .run import RunResult, invoke, is_retryable, normalize_terminal_response
from .schedule import matches_schedule
from .spec import AgentSpec, ProactiveJob, load_platform
from .state import append_jsonl, load_json, save_json
from paplog import observe as paplog
from paplog.core import ulid

DEFAULT_SCHEDULER_STATE = Path("var/state/scheduler-state.json")
MAX_CATCHUP = timedelta(hours=24)
RESERVATION_TTL = timedelta(minutes=90)  # 必须大于最长单次运行时长（PAP_RUN_TIMEOUT_SECONDS 上限 3600s），否则超长运行会被后续 tick 重复认领
RETRY_DELAY = timedelta(minutes=5)
MAX_ATTEMPTS_PER_SLOT = 3
JITTER_MAX_MINUTES = 5
LEAK_MARKERS = (
    "<invoke name=",
    "</｜｜DSML｜",
    "｜｜DSML｜｜",
    "sqlite3.connect(",
    "The tool run finished, but no final summary was produced.",
)


def _now() -> datetime:
    return datetime.now(timezone.utc).astimezone()


def _parse_time(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else None


@contextmanager
def _locked_state(path: Path) -> Iterator[dict[str, Any]]:
    lock_path = path.with_suffix(path.suffix + ".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with open(lock_path, "a+", encoding="utf-8") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        state = load_json(path, {"version": 1, "jobs": {}})
        state.setdefault("version", 1)
        state.setdefault("jobs", {})
        yield state
        save_json(path, state)
        fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


@dataclass
class DueJob:
    spec: AgentSpec
    job: ProactiveJob
    slot: datetime
    jitter_minutes: int = 0

    @property
    def key(self) -> str:
        return f"{self.spec.name}/{self.job.name}"


def _jitter_minutes(seed: str, job_key: str, slot: datetime) -> int:
    """Return a stable, uniformly distributed +/- five-minute slot offset.

    The scheduler sees each slot repeatedly while polling every minute.  A
    state-backed seed makes its offset random when first deployed, yet stable
    across those polls and across restarts.  That stability is what lets a
    negative offset run before the nominal cron minute without duplicates.
    """
    if JITTER_MAX_MINUTES == 0:
        return 0
    material = f"{seed}:{job_key}:{slot.isoformat(timespec='minutes')}".encode("utf-8")
    value = int.from_bytes(hashlib.sha256(material).digest()[:8], "big")
    return value % (JITTER_MAX_MINUTES * 2 + 1) - JITTER_MAX_MINUTES


def _target_interval_seconds(schedule: str) -> int | None:
    """Expose declared cadence when the repository's schedule syntax states it."""
    match = re.fullmatch(r"every\s+(\d+)\s*([mhd])", schedule.strip(), re.I)
    if not match:
        return None
    return int(match.group(1)) * {"m": 60, "h": 3600, "d": 86400}[match.group(2).lower()]


def _latest_jittered_due(
    job: ProactiveJob,
    *,
    job_key: str,
    start_exclusive: datetime,
    now: datetime,
    seed: str,
) -> tuple[datetime, int] | None:
    """Find the newest canonical slot whose jittered dispatch time has arrived.

    Search slightly into the future because a negative offset may make the
    next nominal slot eligible up to five minutes early.
    """
    window = timedelta(minutes=JITTER_MAX_MINUTES)
    cursor = (now + window).replace(second=0, microsecond=0)
    lower = (start_exclusive - window).replace(second=0, microsecond=0)
    while cursor >= lower:
        if matches_schedule(job.schedule, cursor, timezone_name=job.timezone):
            jitter = _jitter_minutes(seed, job_key, cursor)
            if cursor + timedelta(minutes=jitter) <= now:
                return cursor, jitter
        cursor -= timedelta(minutes=1)
    return None


@dataclass
class TickResult:
    job_key: str
    slot: str
    run: RunResult | None
    delivery: str


def due_jobs(
    root: Path,
    *,
    now: datetime | None = None,
    state_path: Path | None = None,
    reserve: bool = True,
) -> list[DueJob]:
    """Find the latest unclaimed due slot per job, optionally reserving it."""
    root = Path(root).resolve()
    now = (now or _now()).replace(second=0, microsecond=0)
    state_path = Path(state_path or root / DEFAULT_SCHEDULER_STATE)
    specs = load_platform(root)
    found: list[DueJob] = []

    state_context = (
        _locked_state(state_path)
        if reserve
        else nullcontext(load_json(state_path, {"version": 1, "jobs": {}}))
    )
    with state_context as state:
        # Keep one random seed in scheduler state.  It is not a credential; it
        # only makes each job/slot's jitter stable across ticks and restarts.
        if reserve:
            jitter_seed = state.setdefault("jitter_seed", secrets.token_hex(16))
        else:
            jitter_seed = state.get("jitter_seed", "pap-scheduler-jitter-preview-v1")
        previous_tick = _parse_time(state.get("last_tick_at"))
        lower = previous_tick or (now - timedelta(minutes=1))
        lower = max(lower, now - MAX_CATCHUP)
        job_state = state.setdefault("jobs", {})
        for spec in specs:
            for job in spec.jobs:
                if not job.enabled:
                    # §40: declared, auditable, not yet scheduled.
                    paplog.event("pap.schedule.skipped", job={"id": f"{spec.name}/{job.name}", "definition_version": "sha256:" + hashlib.sha256(spec.source_path.read_bytes()).hexdigest() if spec.source_path and spec.source_path.is_file() else None},
                                 agent={"id": spec.name}, attributes={"reason": "disabled", "tracking_class": spec.proactive_class})
                    continue
                key = f"{spec.name}/{job.name}"
                entry = job_state.get(key, {})
                previous_slot = _parse_time(entry.get("last_slot"))
                previous_status = entry.get("last_status")
                attempts = int(entry.get("attempts", 0))
                retry_after = _parse_time(
                    entry.get("reserved_at") if previous_status == "reserved"
                    else entry.get("last_finished_at")
                )
                jittered_due = _latest_jittered_due(
                    job,
                    job_key=key,
                    start_exclusive=lower,
                    now=now,
                    seed=jitter_seed,
                )
                slot, jitter_minutes = jittered_due or (None, 0)
                retry_due = False
                if previous_slot is not None and retry_after is not None:
                    if previous_status == "reserved":
                        retry_due = (
                            attempts < MAX_ATTEMPTS_PER_SLOT
                            and now - retry_after >= RESERVATION_TTL
                        )
                    elif (
                        previous_status == "failed"
                        and attempts < MAX_ATTEMPTS_PER_SLOT
                        # §34: only transient trouble is retried. Output the
                        # Historian rejected fails the same way every time, so a
                        # blind retry burns model calls and still fails.
                        and entry.get("last_retryable") is True
                    ):
                        retry_due = now - retry_after >= RETRY_DELAY
                if retry_due and (slot is None or slot <= previous_slot):
                    found.append(DueJob(spec=spec, job=job, slot=previous_slot))
                    if reserve:
                        job_state[key] = {
                            **entry,
                            "reserved_at": now.isoformat(timespec="seconds"),
                            "last_status": "reserved",
                            "last_run_id": None,
                            "attempts": attempts + 1,
                        }
                    continue

                if slot is None:
                    continue
                last_slot = previous_slot
                if last_slot is not None and last_slot >= slot:
                    continue
                found.append(DueJob(
                    spec=spec,
                    job=job,
                    slot=slot,
                    jitter_minutes=jitter_minutes,
                ))
                paplog.event("pap.schedule.due", job={"id": key, "definition_version": "sha256:" + hashlib.sha256(spec.source_path.read_bytes()).hexdigest() if spec.source_path and spec.source_path.is_file() else None},
                             agent={"id": spec.name}, attributes={"scheduled_for": slot.isoformat(), "due_at": now.isoformat(), "schedule_lag_ms": max(0, (now-slot).total_seconds()*1000), "tracking_class": spec.proactive_class, "target_interval_s": _target_interval_seconds(job.schedule)})
                if reserve:
                    job_state[key] = {
                        **entry,
                        "last_slot": slot.isoformat(timespec="minutes"),
                        "last_jitter_minutes": jitter_minutes,
                        "dispatch_at": (slot + timedelta(minutes=jitter_minutes)).isoformat(timespec="minutes"),
                        "reserved_at": now.isoformat(timespec="seconds"),
                        "last_status": "reserved",
                        "last_run_id": None,
                        "attempts": 1,
                    }
        if reserve:
            state["last_tick_at"] = now.isoformat(timespec="seconds")
            state["jobs"] = job_state
    return found


def _intentional_silence(response: str) -> bool:
    """Recognize OpenClaw's exact intentional-silence marker, ``NO_REPLY``."""
    if not response:
        return False
    stripped = response.strip()
    if not stripped:
        return False

    return stripped == "NO_REPLY"


def _requests_silence(response: str) -> bool:
    """True when the run asked for silence: the whole response is NO_REPLY, or
    any line is exactly NO_REPLY (prose around it is the model going off-contract)."""
    return any(line.strip() == "NO_REPLY" for line in response.splitlines())


def _looks_like_leaked_output(text: str) -> bool:
    """True when a run's final text is an echo of tool use, not an answer."""
    if any(marker in text for marker in LEAK_MARKERS):
        return True
    lines = text.splitlines()
    reasoning_preambles = ("Let me ", "I'll ", "I will ", "Now let me ", "First, let me ")
    for preamble, code_line in zip(lines, lines[1:]):
        if preamble.lstrip().startswith(reasoning_preambles):
            stripped_code = code_line.lstrip()
            if ("=" in stripped_code and "(" in stripped_code) or stripped_code.startswith("<"):
                return True
    return "```python" in text


def _deliver(
    result: RunResult,
    job: ProactiveJob,
    *,
    target: str | None,
    sender: Callable[..., subprocess.CompletedProcess[str]] | None = None,
) -> str:
    """Deliver user-facing run output through the OpenClaw Gateway CLI."""
    # Defense in depth for callers or older records that bypassed invoke().
    response, _ = normalize_terminal_response(result.response)
    if result.status != "success":
        return "not-attempted"
    if not response or _intentional_silence(response):
        return "silent"
    if _requests_silence(response):
        return "silence-suppressed"
    if _looks_like_leaked_output(response):
        return "leaked-suppressed"
    if job.delivery == "local":
        return "local"
    if not target:
        return "unconfigured"
    command_runner = sender or subprocess.run
    channel = os.environ.get("PAP_OPENCLAW_CHANNEL", "feishu")
    account = os.environ.get("PAP_OPENCLAW_ACCOUNT", "feishu4")
    openclaw_bin = os.environ.get("PAP_OPENCLAW_BIN", "openclaw")
    started = time.monotonic()
    message_action_id = ulid()
    message_execution = {"run_id": result.run_id, "operation_id": result.run_id, "action_id": message_action_id}
    message_metadata = {"channel": channel, "account": account, "target": target,
                        "content": {"sha256": hashlib.sha256(response.encode("utf-8")).hexdigest(), "bytes": len(response.encode("utf-8"))},
                        "action.effect": "send", "action.scope": "external"}
    paplog.event("pap.message.send", kind="action", phase="started",
                 execution=message_execution,
                 attributes=message_metadata)
    try:
        sent = command_runner(
            [
                openclaw_bin, "message", "send",
                "--channel", channel,
                "--account", account,
                "--target", target,
                "--message", response,
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        paplog.event("pap.message.send", kind="action", phase="failed", severity="ERROR",
                     execution=message_execution, outcome={"status": "error"},
                     duration_ms=(time.monotonic() - started) * 1000,
                     error={"type": type(exc).__name__, "message": str(exc)}, attributes=message_metadata)
        return "failed"
    paplog.event("pap.message.send", kind="action", phase="completed" if sent.returncode == 0 else "failed",
                 severity="INFO" if sent.returncode == 0 else "ERROR", execution=message_execution,
                 outcome={"status": "ok" if sent.returncode == 0 else "error"}, duration_ms=(time.monotonic() - started) * 1000,
                 attributes={**message_metadata, "exit_code": sent.returncode})
    return "sent" if sent.returncode == 0 else "failed"


def tick(
    root: Path,
    *,
    now: datetime | None = None,
    state_path: Path | None = None,
    run_log: Path | None = None,
    delivery_target: str | None = None,
    dry_run: bool = False,
    command_runner: Callable[..., subprocess.CompletedProcess[str]] | None = None,
    sender: Callable[..., subprocess.CompletedProcess[str]] | None = None,
) -> list[TickResult]:
    """Run one scheduler tick. A claimed slot is never executed twice."""
    root = Path(root).resolve()
    state_path = Path(state_path or root / DEFAULT_SCHEDULER_STATE)
    run_log = Path(run_log or root / "var/state/runs.jsonl")
    target = delivery_target or os.environ.get("PAP_OPENCLAW_DELIVERY_TARGET")
    jobs = due_jobs(root, now=now, state_path=state_path, reserve=not dry_run)
    if dry_run:
        return [
            TickResult(job_key=due.key, slot=due.slot.isoformat(timespec="minutes"),
                       run=None, delivery="dry-run")
            for due in jobs
        ]

    results: list[TickResult] = []
    for due in jobs:
        dispatched_at = _now()
        paplog.event("pap.schedule.dispatched", job={"id": due.key}, agent={"id": due.spec.name},
                     attributes={"scheduled_for": due.slot.isoformat(), "dispatched_at": dispatched_at.isoformat(), "jitter_minutes": due.jitter_minutes, "tracking_class": due.spec.proactive_class, "target_interval_s": _target_interval_seconds(due.job.schedule)})
        result = invoke(
            root=root,
            spec=due.spec,
            skill=due.job.skill,
            args=due.job.args,
            trigger={
                "type": "schedule",
                # Use the same stable key emitted by due/dispatched events so
                # one job filter follows the entire scheduler-to-run trace.
                "job_id": due.key,
                "job_name": due.job.name,
                "scheduled_for": due.slot.isoformat(),
                "dispatched_at": dispatched_at.isoformat(),
                "jitter_minutes": due.jitter_minutes,
            },
            run_log=run_log,
            command_runner=command_runner,
            runtime=due.job.runtime,
            model=due.job.model,
            runner_backend=due.job.runner,
            command=due.job.command,
        )
        delivery = _deliver(result, due.job, target=target, sender=sender)
        append_jsonl(run_log, {
            "event": "run.delivery",
            "run_id": result.run_id,
            "delivery": delivery,
            "delivery_target_configured": bool(target),
        })
        with _locked_state(state_path) as state:
            entry = state.setdefault("jobs", {}).setdefault(due.key, {})
            entry.update({"last_run_id": result.run_id, "last_status": result.status,
                          "last_failure_kind": getattr(result, "failure_kind", ""),
                          "last_retryable": is_retryable(getattr(result, "failure_kind", ""))
                          if result.status == "failed" else None,
                          "last_delivery": delivery,
                          "last_finished_at": _now().isoformat(timespec="seconds")})
        results.append(TickResult(
            job_key=due.key,
            slot=due.slot.isoformat(timespec="minutes"),
            run=result,
            delivery=delivery,
        ))
    return results
