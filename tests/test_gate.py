"""Tests for pap.gate — the shared proactive gate."""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from pap.gate import (
    BACKOFF_BASE_HOURS,
    BACKOFF_MAX_HOURS,
    DEDUPE_TTL_HOURS,
    MIN_PRIORITY,
    QUIET_PRIORITY,
    decide,
    history,
)


def local_dt(hour: int, minute: int = 0) -> datetime:
    """A datetime in the machine's local timezone at the given hour."""
    return datetime.now(timezone.utc).astimezone().replace(
        hour=hour, minute=minute, second=0, microsecond=0)


def quiet_hour() -> int:
    # 23:00 local is always inside [22:00, 08:00) quiet hours.
    return 23


def day_hour() -> int:
    # 14:00 local is always outside quiet hours.
    return 14


def test_allow_high_priority_daytime(tmp_path):
    d = decide("a", "k1", 80, now=local_dt(day_hour()), db_path=tmp_path / "db.json")
    assert d.allowed is True
    assert d.reason == "passed"


def test_reject_low_priority_daytime(tmp_path):
    d = decide("a", "k1", MIN_PRIORITY - 1, now=local_dt(day_hour()), db_path=tmp_path / "db.json")
    assert d.allowed is False
    assert "priority" in d.reason


def test_quiet_hours_need_higher_priority(tmp_path):
    h = quiet_hour()
    d1 = decide("a", "k1", 80, now=local_dt(h), db_path=tmp_path / "db.json")
    assert d1.allowed is False
    assert "quiet-hours" in d1.reason
    # Fresh agent (no denial streak) may pass with the higher quiet-hours bar.
    d2 = decide("b", "k2", QUIET_PRIORITY, now=local_dt(h, 1), db_path=tmp_path / "db.json")
    assert d2.allowed is True


def test_dedupe_blocks_repeat_within_ttl(tmp_path):
    t0 = local_dt(day_hour())
    db = tmp_path / "db.json"
    d1 = decide("a", "same-key", 95, now=t0, db_path=db)
    assert d1.allowed
    d2 = decide("a", "same-key", 95, now=t0 + timedelta(hours=1), db_path=db)
    assert d2.allowed is False
    assert "dedupe" in d2.reason
    # After TTL expiry the key may deliver again (priority 95 also survives
    # any quiet-hours window the +169h timestamp may land in).
    d3 = decide("a", "same-key", 95,
                now=t0 + timedelta(hours=DEDUPE_TTL_HOURS + 1), db_path=db)
    assert d3.allowed


def test_dedupe_key_scoped_per_agent(tmp_path):
    t0 = local_dt(day_hour())
    db = tmp_path / "db.json"
    assert decide("a", "k", 80, now=t0, db_path=db).allowed
    # Same key from a different agent is independent.
    assert decide("b", "k", 80, now=t0 + timedelta(minutes=1), db_path=db).allowed


def test_backoff_escalates_after_denials(tmp_path):
    db = tmp_path / "db.json"
    t = local_dt(day_hour())
    # 1st denial (low priority) -> floor 4h from t
    assert decide("a", "k1", 10, now=t, db_path=db).allowed is False
    # 3 minutes later, high priority but inside 4h floor -> denied.
    # This 2nd denial escalates the floor to 8h from t+3min.
    d = decide("a", "k2", 95, now=t + timedelta(minutes=3), db_path=db)
    assert d.allowed is False
    assert "backoff" in d.reason
    assert "4h" in d.reason
    # 9h after t (> 8h since the last denial): allowed again. Note the probe
    # may land in quiet hours, so priority must be >= QUIET_PRIORITY.
    d = decide("a", "k3", 95, now=t + timedelta(hours=9), db_path=db)
    assert d.allowed


def test_backoff_doubles_with_streak(tmp_path):
    db = tmp_path / "db.json"
    t = local_dt(day_hour())
    streak = 3
    for i in range(streak):
        decide("a", f"k{i}", 10, now=t + timedelta(minutes=i), db_path=db)
    # floor = 4 * 2^(3-1) = 16h from the last denial (t+2min)
    last = t + timedelta(minutes=streak - 1)
    d = decide("a", "kz", 95, now=last + timedelta(hours=BACKOFF_BASE_HOURS * 2), db_path=db)
    assert d.allowed is False
    assert "16h" in d.reason
    # The kz probe itself was denied -> streak 4 -> floor 32h. Once 32h have
    # passed since kz, delivery is allowed again (48h later to be safe).
    d = decide("a", "kz", 95, now=last + timedelta(days=2, hours=8), db_path=db)
    assert d.allowed


def test_success_resets_backoff_streak(tmp_path):
    db = tmp_path / "db.json"
    t = local_dt(day_hour())
    decide("a", "k1", 10, now=t, db_path=db)                        # denial 1
    decide("a", "k2", 80, now=t + timedelta(hours=BACKOFF_BASE_HOURS + 1), db_path=db)  # allow
    # streak reset -> next denial starts a fresh 4h floor, not 8h
    d = decide("a", "k3", 95, now=t + timedelta(hours=2 * BACKOFF_BASE_HOURS + 2), db_path=db)
    assert d.allowed is True


def test_backoff_capped(tmp_path):
    db = tmp_path / "db.json"
    t = local_dt(day_hour())
    for i in range(10):
        decide("a", f"k{i}", 10, now=t + timedelta(minutes=i), db_path=db)
    recs = history("a", log_path=tmp_path / "gate-log.jsonl")
    assert len(recs) == 10
    # Floor is capped at BACKOFF_MAX_HOURS: allow once 33h have passed since
    # the first denial (>= 32h after the last denial at t+9min). May land in
    # quiet hours, so priority 95.
    d = decide("a", "kz", 95, now=t + timedelta(hours=33), db_path=db)
    assert d.allowed


def test_invalid_inputs(tmp_path):
    now = local_dt(day_hour())
    assert decide("", "k", 80, now=now, db_path=tmp_path / "db.json").allowed is False
    assert decide("a", "  ", 80, now=now, db_path=tmp_path / "db.json").allowed is False
    assert decide("a", "k", 101, now=now, db_path=tmp_path / "db.json").allowed is False
    assert decide("a", "k", -1, now=now, db_path=tmp_path / "db.json").allowed is False
    assert decide("a", "k", True, now=now, db_path=tmp_path / "db.json").allowed is False


def test_invalid_inputs_do_not_touch_state(tmp_path):
    db = tmp_path / "db.json"
    decide("a", "", 80, now=local_dt(day_hour()), db_path=db)
    assert not db.exists()


def test_state_and_log_written(tmp_path):
    db = tmp_path / "sub" / "db.json"
    decide("a", "k1", 80, now=local_dt(day_hour()), db_path=db)
    assert db.exists()
    log = db.parent / "gate-log.jsonl"
    recs = history("a", log_path=log)
    assert len(recs) == 1
    assert recs[0]["allowed"] is True
    assert recs[0]["dedupe_key"] == "k1"


def test_history_filter(tmp_path):
    db = tmp_path / "db.json"
    now = local_dt(day_hour())
    decide("a", "k1", 80, now=now, db_path=db)
    decide("b", "k2", 80, now=now, db_path=db)
    assert len(history(None, log_path=db.parent / "gate-log.jsonl")) == 2
    assert len(history("a", log_path=db.parent / "gate-log.jsonl")) == 1


def test_jsonl_lines_are_valid_json(tmp_path):
    db = tmp_path / "db.json"
    decide("a", "k1", 80, now=local_dt(day_hour()), db_path=db)
    decide("a", "k2", 10, now=local_dt(day_hour(), 1), db_path=db)
    for line in (db.parent / "gate-log.jsonl").read_text().splitlines():
        assert json.loads(line)
