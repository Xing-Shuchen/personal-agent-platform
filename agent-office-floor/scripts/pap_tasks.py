"""Read-only, allowlisted PAP task projection for the local office view."""

from __future__ import annotations

import argparse
from datetime import datetime, time, timedelta, timezone
import json
from pathlib import Path
import sys
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from pap.schedule import _anchored_interval, _CLOCK_RE, _expand_field, _interval_minutes, matches_schedule  # noqa: E402
from pap.scheduler import DEFAULT_SCHEDULER_STATE, JITTER_MAX_MINUTES, _jitter_minutes  # noqa: E402
from pap.spec import load_platform  # noqa: E402


def next_nominal(schedule: str, now: datetime, timezone_name: str | None) -> str | None:
    """Find the next nominal minute using PAP's own schedule matcher."""
    zone = ZoneInfo(timezone_name) if timezone_name else now.astimezone().tzinfo
    assert zone is not None
    clock_match = _CLOCK_RE.fullmatch(schedule)
    anchored_match = _anchored_interval(schedule)
    effective_zone = (ZoneInfo(clock_match.group(3)) if clock_match and clock_match.group(3)
                      else anchored_match[1].tzinfo if anchored_match else zone)
    assert effective_zone is not None
    utc_now = now.astimezone(timezone.utc)
    # A repeated local hour has two distinct dispatch instants. Search on the
    # UTC timeline around an offset change so neither fold is skipped.
    if (utc_now - timedelta(hours=3)).astimezone(effective_zone).utcoffset() != (utc_now + timedelta(hours=3)).astimezone(effective_zone).utcoffset():
        instant = utc_now.replace(second=0, microsecond=0) + timedelta(minutes=1)
        for _ in range(180):
            if matches_schedule(schedule, instant, timezone_name=timezone_name):
                return instant.astimezone(effective_zone).isoformat(timespec="minutes")
            instant += timedelta(minutes=1)
    local = now.astimezone(zone)
    interval = _interval_minutes(schedule)
    if interval is not None:
        naive = local.replace(tzinfo=None, second=0, microsecond=0)
        elapsed = int((naive - datetime(1970, 1, 1)).total_seconds() // 60)
        next_elapsed = (elapsed // interval + 1) * interval
        for _ in range(3):
            candidate = (datetime(1970, 1, 1) + timedelta(minutes=next_elapsed)).replace(tzinfo=zone)
            if candidate.astimezone(timezone.utc) > utc_now and candidate.astimezone(timezone.utc).astimezone(zone) == candidate and matches_schedule(schedule, candidate, timezone_name=timezone_name):
                return candidate.isoformat(timespec="minutes")
            next_elapsed += interval
        return None
    anchored = anchored_match
    if anchored is not None:
        minutes, anchor = anchored
        elapsed = int((now.astimezone(anchor.tzinfo).replace(second=0, microsecond=0) - anchor).total_seconds() // 60)
        next_elapsed = max(0, (elapsed // minutes + 1) * minutes)
        for _ in range(3):
            candidate = anchor + timedelta(minutes=next_elapsed)
            if candidate.astimezone(timezone.utc) > utc_now and candidate.astimezone(timezone.utc).astimezone(anchor.tzinfo) == candidate and matches_schedule(schedule, candidate, timezone_name=timezone_name):
                return candidate.isoformat(timespec="minutes")
            next_elapsed += minutes
        return None
    clock = clock_match
    if clock:
        clock_zone = ZoneInfo(clock.group(3)) if clock.group(3) else zone
        clock_local = now.astimezone(clock_zone)
        for offset in range(3):
            candidate = datetime.combine(clock_local.date() + timedelta(days=offset),
                                         time(int(clock.group(1)), int(clock.group(2))), clock_zone)
            if candidate.astimezone(timezone.utc) > utc_now and candidate.astimezone(timezone.utc).astimezone(clock_zone) == candidate and matches_schedule(schedule, candidate, timezone_name=timezone_name):
                return candidate.isoformat(timespec="minutes")
        return None
    value = schedule.removeprefix("cron ")
    fields = value.split()
    if len(fields) == 5:
        minutes = sorted(_expand_field(fields[0], 0, 59))
        hours = sorted(_expand_field(fields[1], 0, 23))
        # A Feb 29 cron may wait eight years across a non-leap century year.
        for offset in range(366 * 8 + 1):
            day = local.date() + timedelta(days=offset)
            for hour in hours:
                for minute in minutes:
                    candidate = datetime.combine(day, time(hour, minute), zone)
                    if candidate.astimezone(timezone.utc) <= utc_now or candidate.astimezone(timezone.utc).astimezone(zone) != candidate:
                        continue
                    if matches_schedule(schedule, candidate, timezone_name=timezone_name):
                        return candidate.isoformat(timespec="minutes")
        return None
    return None


def _process_start_ticks(pid: int, proc_root: Path = Path("/proc")) -> int | None:
    try:
        fields = (proc_root / str(pid) / "stat").read_text(encoding="utf-8").rsplit(") ", 1)[1].split()
        if fields[0] in {"Z", "X", "x"}:
            return None
        return int(fields[19])
    except (OSError, IndexError, ValueError):
        return None


def _safe_id(value: object) -> str | None:
    if not isinstance(value, str) or not 0 < len(value) <= 128 or any(ord(char) < 32 for char in value):
        return None
    return value


def _safe_time(value: object) -> str | None:
    if not isinstance(value, str) or len(value) > 40:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return value if parsed.tzinfo is not None else None
    except ValueError:
        return None


def future_occurrences(key: str, agent_id: str, name: str, schedule: str,
                       timezone_name: str | None, enabled: bool, now: datetime,
                       jitter_seed: str | None) -> list[dict]:
    """All occurrences in the next hour, plus eight later ones per job."""
    cutoff = now + timedelta(hours=1)
    cursor = now - timedelta(minutes=JITTER_MAX_MINUTES + 1)
    # pap tick hashes the slot in its own local clock, even when the schedule
    # matcher uses a job-specific timezone.
    scheduler_zone = now.astimezone().tzinfo
    assert scheduler_zone is not None
    items: list[dict] = []
    later_count = 0
    for _ in range(100):
        next_at = next_nominal(schedule, cursor, timezone_name)
        if next_at is None:
            break
        slot = datetime.fromisoformat(next_at)
        if slot.astimezone(timezone.utc) <= cursor.astimezone(timezone.utc):
            raise ValueError("schedule projection did not advance")
        cursor = slot
        offset = _jitter_minutes(jitter_seed, key, slot.astimezone(scheduler_zone)) if jitter_seed else 0
        dispatch = (slot.astimezone(timezone.utc) + timedelta(minutes=offset)).astimezone(slot.tzinfo)
        if dispatch > now:
            items.append({"key": key, "agentId": agent_id, "name": name,
                          "timezone": timezone_name, "enabled": enabled,
                          "nominalAt": slot.isoformat(timespec="minutes"),
                          "dispatchAt": dispatch.isoformat(timespec="minutes")})
            if dispatch > cutoff:
                later_count += 1
        # Jitter can reorder nearby slots, so keep scanning through the boundary.
        if slot.astimezone(timezone.utc) > cutoff.astimezone(timezone.utc) + timedelta(minutes=JITTER_MAX_MINUTES) and later_count >= 8:
            break
    items.sort(key=lambda item: (datetime.fromisoformat(item["dispatchAt"]).timestamp(), item["key"], item["nominalAt"]))
    near = [item for item in items if datetime.fromisoformat(item["dispatchAt"]) <= cutoff]
    later = [item for item in items if datetime.fromisoformat(item["dispatchAt"]) > cutoff][:8]
    return near + later


def run_metadata(path: Path, proc_root: Path = Path("/proc")) -> tuple[list[dict], list[dict], int, list[dict]]:
    if not path.is_file():
        return [], [], 0, []
    starts: dict[str, dict] = {}
    completions: list[dict] = []
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(record, dict):
                continue
            run_id = _safe_id(record.get("run_id"))
            if run_id is None:
                continue
            if record.get("event") == "run.started":
                starts[run_id] = {"runId": run_id, "agentId": _safe_id(record.get("agent_id")),
                                  "jobId": _safe_id(record.get("job_id")), "startedAt": _safe_time(record.get("started_at")),
                                  "_pid": record.get("process_id"), "_start_ticks": record.get("process_start_ticks")}
            elif record.get("event") == "run.completed":
                start = starts.pop(run_id, None)
                status = record.get("status")
                completions.append({"runId": run_id, "agentId": _safe_id(record.get("agent_id")) or (start or {}).get("agentId"),
                                    "jobId": _safe_id(record.get("job_id")) or (start or {}).get("jobId"),
                                    "completedAt": _safe_time(record.get("completed_at")),
                                    "status": status if isinstance(status, str) and status in {"success", "failed", "not_ready"} else None})
    active_runs: list[dict] = []
    open_runs: list[dict] = []
    for start in starts.values():
        pid, ticks = start.pop("_pid"), start.pop("_start_ticks")
        # The process identity is checked locally and never sent to the browser.
        if type(pid) is int and pid > 0 and type(ticks) is int and ticks > 0 and _process_start_ticks(pid, proc_root) == ticks:
            active_runs.append(start)
        else:
            open_runs.append(start)
    active_runs.sort(key=lambda item: item.get("startedAt") or "", reverse=True)
    open_runs.sort(key=lambda item: item.get("startedAt") or "", reverse=True)
    recent = sorted(completions, key=lambda item: item.get("completedAt") or "", reverse=True)[:10]
    return active_runs, open_runs[:10], len(open_runs), recent


def snapshot(root: Path, now: datetime) -> dict:
    specs = load_platform(root)
    jobs = []
    state_path = root / DEFAULT_SCHEDULER_STATE
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
        jitter_seed = state.get("jitter_seed") if isinstance(state, dict) else None
    except (OSError, ValueError):
        jitter_seed = None
    if not isinstance(jitter_seed, str) or not jitter_seed:
        jitter_seed = None
    occurrences = []
    for spec in specs:
        for job in spec.jobs:
            enabled = spec.enabled and job.enabled
            key = f"{spec.name}/{job.name}"
            jobs.append({"key": key, "agentId": spec.name,
                         "name": job.name, "schedule": job.schedule, "timezone": job.timezone,
                         "enabled": enabled,
                         "nextNominalAt": next_nominal(job.schedule, now, job.timezone)})
            occurrences.extend(future_occurrences(key, spec.name, job.name, job.schedule,
                                                  job.timezone, enabled, now, jitter_seed))
    occurrences.sort(key=lambda item: (datetime.fromisoformat(item["dispatchAt"]).timestamp(), item["key"], item["nominalAt"]))
    active_runs, open_runs, open_run_count, recent = run_metadata(root / "var/state/runs.jsonl")
    return {"generatedAt": now.isoformat(timespec="seconds"),
            "agents": [{"id": spec.name, "description": spec.description, "enabled": spec.enabled} for spec in specs],
            "jobs": jobs, "occurrences": occurrences,
            "timingBasis": "jittered" if jitter_seed else "nominal",
            "activeRuns": active_runs, "openRuns": open_runs, "openRunCount": open_run_count,
            "recentRuns": recent}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    print(json.dumps(snapshot(args.root, datetime.now(timezone.utc)), ensure_ascii=False))


if __name__ == "__main__":
    main()
