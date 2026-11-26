"""Small, dependency-free schedule parser used by ``pap tick``.

The platform deliberately supports only minute-resolution schedules:

* ``every 30m`` / ``every 2h`` / ``every 1d``;
* ``every 14d from 2026-09-12 20:43 tz Asia/Shanghai``;
* ``HH:MM`` (optionally ``HH:MM tz Area/Location``);
* five-field cron, with or without the historical ``cron `` prefix.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


class ScheduleError(ValueError):
    """Raised when a schedule cannot be evaluated safely."""


_EVERY_RE = re.compile(r"^every\s+(\d+)([smhd])$")
_ANCHORED_EVERY_RE = re.compile(
    r"^every\s+(\d+)([smhd])\s+from\s+(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2})\s+tz\s+([^\s]+)$"
)
_CLOCK_RE = re.compile(r"^(\d{2}):(\d{2})(?:\s+tz\s+([^\s]+))?$")


def _interval_minutes(schedule: str) -> int | None:
    match = _EVERY_RE.fullmatch(schedule)
    if not match:
        return None
    amount = int(match.group(1))
    unit = match.group(2)
    if amount <= 0:
        raise ScheduleError("interval must be greater than zero")
    seconds = amount * {"s": 1, "m": 60, "h": 3600, "d": 86400}[unit]
    if seconds < 60 or seconds % 60:
        raise ScheduleError("pap tick supports minute-resolution intervals only")
    return seconds // 60


def _anchored_interval(schedule: str) -> tuple[int, datetime] | None:
    match = _ANCHORED_EVERY_RE.fullmatch(schedule)
    if not match:
        return None
    amount, unit, date, clock, zone_name = match.groups()
    minutes = _interval_minutes(f"every {amount}{unit}")
    assert minutes is not None
    try:
        zone = ZoneInfo(zone_name)
    except ZoneInfoNotFoundError as exc:
        raise ScheduleError(f"unknown timezone {zone_name!r}") from exc
    try:
        anchor = datetime.fromisoformat(f"{date}T{clock}").replace(tzinfo=zone)
    except ValueError as exc:
        raise ScheduleError("anchored interval must use a valid YYYY-MM-DD HH:MM time") from exc
    return minutes, anchor


def _cron_fields(schedule: str) -> list[str] | None:
    value = schedule[5:].strip() if schedule.startswith("cron ") else schedule
    fields = value.split()
    return fields if len(fields) == 5 else None


def _expand_field(token: str, minimum: int, maximum: int, *, sunday: bool = False) -> set[int]:
    values: set[int] = set()
    for part in token.split(","):
        if not part:
            raise ScheduleError(f"empty cron field component in {token!r}")
        base, slash, step_text = part.partition("/")
        if slash:
            try:
                step = int(step_text)
            except ValueError as exc:
                raise ScheduleError(f"invalid cron step {step_text!r}") from exc
            if step <= 0:
                raise ScheduleError("cron step must be greater than zero")
        else:
            step = 1

        if base == "*":
            start, end = minimum, maximum
        elif "-" in base:
            left, right = base.split("-", 1)
            try:
                start, end = int(left), int(right)
            except ValueError as exc:
                raise ScheduleError(f"invalid cron range {base!r}") from exc
            if start > end:
                raise ScheduleError(f"descending cron range {base!r} is not supported")
        else:
            try:
                start = end = int(base)
            except ValueError as exc:
                raise ScheduleError(f"invalid cron value {base!r}") from exc

        allowed_max = 7 if sunday else maximum
        if start < minimum or end > allowed_max:
            raise ScheduleError(
                f"cron value {base!r} outside allowed range {minimum}..{allowed_max}"
            )
        values.update(range(start, end + 1, step))

    if sunday and 7 in values:
        values.remove(7)
        values.add(0)
    return values


def validate_schedule(schedule: str) -> None:
    """Raise ``ScheduleError`` unless *schedule* is supported."""
    if not isinstance(schedule, str) or not schedule.strip():
        raise ScheduleError("schedule must be a non-empty string")
    value = schedule.strip()
    if _EVERY_RE.fullmatch(value):
        _interval_minutes(value)
        return
    if _ANCHORED_EVERY_RE.fullmatch(value):
        _anchored_interval(value)
        return

    clock = _CLOCK_RE.fullmatch(value)
    if clock:
        hour, minute = int(clock.group(1)), int(clock.group(2))
        if hour > 23 or minute > 59:
            raise ScheduleError("clock schedule must use a valid HH:MM time")
        if clock.group(3):
            try:
                ZoneInfo(clock.group(3))
            except ZoneInfoNotFoundError as exc:
                raise ScheduleError(f"unknown timezone {clock.group(3)!r}") from exc
        return

    fields = _cron_fields(value)
    if fields is None:
        raise ScheduleError(
            "expected 'every Nm/h/d', 'HH:MM [tz Area/Location]', or five-field cron"
        )
    ranges = ((0, 59, False), (0, 23, False), (1, 31, False),
              (1, 12, False), (0, 6, True))
    for field, (minimum, maximum, sunday) in zip(fields, ranges):
        _expand_field(field, minimum, maximum, sunday=sunday)


def matches_schedule(schedule: str, moment: datetime, *, timezone_name: str | None = None) -> bool:
    """Return whether *schedule* is due in the minute containing *moment*."""
    if moment.tzinfo is None:
        raise ScheduleError("scheduler moments must be timezone-aware")
    value = schedule.strip()
    validate_schedule(value)
    zone = ZoneInfo(timezone_name) if timezone_name else None

    interval = _interval_minutes(value)
    if interval is not None:
        local = (moment.astimezone(zone) if zone else moment).replace(second=0, microsecond=0, tzinfo=None)
        epoch = datetime(1970, 1, 1)
        elapsed = int((local - epoch).total_seconds() // 60)
        return elapsed % interval == 0

    anchored_interval = _anchored_interval(value)
    if anchored_interval is not None:
        interval, anchor = anchored_interval
        local = moment.astimezone(anchor.tzinfo).replace(second=0, microsecond=0)
        elapsed = int((local - anchor).total_seconds() // 60)
        return elapsed >= 0 and elapsed % interval == 0

    clock = _CLOCK_RE.fullmatch(value)
    if clock:
        clock_zone = ZoneInfo(clock.group(3)) if clock.group(3) else (zone or moment.tzinfo)
        local = moment.astimezone(clock_zone)
        return local.hour == int(clock.group(1)) and local.minute == int(clock.group(2))

    fields = _cron_fields(value)
    assert fields is not None
    local = moment.astimezone(zone) if zone else moment
    minute, hour, day, month, weekday = (
        local.minute,
        local.hour,
        local.day,
        local.month,
        (local.weekday() + 1) % 7,
    )
    minute_ok = minute in _expand_field(fields[0], 0, 59)
    hour_ok = hour in _expand_field(fields[1], 0, 23)
    month_ok = month in _expand_field(fields[3], 1, 12)
    dom_ok = day in _expand_field(fields[2], 1, 31)
    dow_ok = weekday in _expand_field(fields[4], 0, 6, sunday=True)
    dom_wild, dow_wild = fields[2] == "*", fields[4] == "*"
    day_ok = (dom_ok and dow_ok) if dom_wild or dow_wild else (dom_ok or dow_ok)
    return minute_ok and hour_ok and month_ok and day_ok


def latest_due(
    schedule: str,
    *,
    start_exclusive: datetime,
    end_inclusive: datetime,
    timezone_name: str | None = None,
) -> datetime | None:
    """Return the latest due minute in ``(start_exclusive, end_inclusive]``."""
    if start_exclusive.tzinfo is None or end_inclusive.tzinfo is None:
        raise ScheduleError("scheduler window must be timezone-aware")
    cursor = end_inclusive.replace(second=0, microsecond=0)
    lower = start_exclusive.replace(second=0, microsecond=0)
    while cursor > lower:
        if matches_schedule(schedule, cursor, timezone_name=timezone_name):
            return cursor
        cursor -= timedelta(minutes=1)
    return None
