"""Platform scheduler: resolve due manifest jobs and invoke their skills."""

from __future__ import annotations

import fcntl
import os
import subprocess
from contextlib import contextmanager, nullcontext
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Iterator

from .run import RunResult, invoke
from .schedule import latest_due
from .spec import AgentSpec, ProactiveJob, load_platform
from .state import append_jsonl, load_json, save_json

DEFAULT_SCHEDULER_STATE = Path("var/state/scheduler-state.json")
MAX_CATCHUP = timedelta(hours=24)
RESERVATION_TTL = timedelta(minutes=90)  # 必须大于最长单次运行时长（PAP_RUN_TIMEOUT_SECONDS 上限 3600s），否则超长运行会被后续 tick 重复认领
RETRY_DELAY = timedelta(minutes=5)
MAX_ATTEMPTS_PER_SLOT = 3
LEAK_MARKERS = ("<invoke name=", "</｜｜DSML｜", "｜｜DSML｜｜", "sqlite3.connect(")


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

    @property
    def key(self) -> str:
        return f"{self.spec.name}/{self.job.name}"


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
        previous_tick = _parse_time(state.get("last_tick_at"))
        lower = previous_tick or (now - timedelta(minutes=1))
        lower = max(lower, now - MAX_CATCHUP)
        job_state = state.setdefault("jobs", {})
        for spec in specs:
            for job in spec.jobs:
                key = f"{spec.name}/{job.name}"
                entry = job_state.get(key, {})
                previous_slot = _parse_time(entry.get("last_slot"))
                previous_status = entry.get("last_status")
                attempts = int(entry.get("attempts", 0))
                retry_after = _parse_time(
                    entry.get("reserved_at") if previous_status == "reserved"
                    else entry.get("last_finished_at")
                )
                slot = latest_due(job.schedule, start_exclusive=lower, end_inclusive=now)
                retry_due = False
                if previous_slot is not None and retry_after is not None:
                    if previous_status == "reserved":
                        retry_due = (
                            attempts < MAX_ATTEMPTS_PER_SLOT
                            and now - retry_after >= RESERVATION_TTL
                        )
                    elif previous_status == "failed" and attempts < MAX_ATTEMPTS_PER_SLOT:
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
                found.append(DueJob(spec=spec, job=job, slot=slot))
                if reserve:
                    job_state[key] = {
                        **entry,
                        "last_slot": slot.isoformat(timespec="minutes"),
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
    if result.status != "success":
        return "not-attempted"
    if not result.response or _intentional_silence(result.response):
        return "silent"
    if _looks_like_leaked_output(result.response):
        return "leaked-suppressed"
    if job.delivery == "local":
        return "local"
    if not target:
        return "unconfigured"
    command_runner = sender or subprocess.run
    channel = os.environ.get("PAP_OPENCLAW_CHANNEL", "feishu")
    account = os.environ.get("PAP_OPENCLAW_ACCOUNT", "feishu4")
    openclaw_bin = os.environ.get("PAP_OPENCLAW_BIN", "openclaw")
    try:
        sent = command_runner(
            [
                openclaw_bin, "message", "send",
                "--channel", channel,
                "--account", account,
                "--target", target,
                "--message", result.response,
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )
    except (OSError, subprocess.TimeoutExpired):
        return "failed"
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
        result = invoke(
            root=root,
            spec=due.spec,
            skill=due.job.skill,
            args=due.job.args,
            trigger={
                "type": "schedule",
                "job_id": due.job.name,
                "scheduled_for": due.slot.isoformat(timespec="minutes"),
            },
            run_log=run_log,
            command_runner=command_runner,
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
                          "last_delivery": delivery,
                          "last_finished_at": _now().isoformat(timespec="seconds")})
        results.append(TickResult(
            job_key=due.key,
            slot=due.slot.isoformat(timespec="minutes"),
            run=result,
            delivery=delivery,
        ))
    return results
