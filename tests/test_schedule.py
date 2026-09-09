"""Tests for minute-resolution platform schedules."""

from datetime import datetime, timedelta, timezone

import pytest

from pap.schedule import ScheduleError, latest_due, matches_schedule, validate_schedule

CST = timezone(timedelta(hours=8))


def test_raw_cron_matches_expected_local_minute():
    assert matches_schedule("17 */2 * * *", datetime(2026, 8, 31, 18, 17, tzinfo=CST))
    assert not matches_schedule("17 */2 * * *", datetime(2026, 8, 31, 19, 17, tzinfo=CST))


def test_weekly_cron_uses_sunday_zero():
    assert matches_schedule("0 20 * * 0", datetime(2026, 8, 30, 20, 0, tzinfo=CST))
    assert not matches_schedule("0 20 * * 0", datetime(2026, 8, 31, 20, 0, tzinfo=CST))


def test_interval_is_anchored_to_local_wall_clock():
    assert matches_schedule("every 4h", datetime(2026, 8, 31, 8, 0, tzinfo=CST))
    assert not matches_schedule("every 4h", datetime(2026, 8, 31, 9, 0, tzinfo=CST))


def test_anchored_interval_matches_only_its_configured_biweekly_slot():
    schedule = "every 14d from 2026-09-12 20:43 tz Asia/Shanghai"
    assert matches_schedule(schedule, datetime(2026, 9, 12, 20, 43, tzinfo=CST))
    assert matches_schedule(schedule, datetime(2026, 9, 26, 20, 43, tzinfo=CST))
    assert not matches_schedule(schedule, datetime(2026, 9, 19, 20, 43, tzinfo=CST))
    assert not matches_schedule(schedule, datetime(2026, 9, 12, 20, 42, tzinfo=CST))


def test_latest_due_returns_only_latest_slot():
    end = datetime(2026, 8, 31, 18, 30, tzinfo=CST)
    due = latest_due("17 */2 * * *", start_exclusive=end - timedelta(hours=5),
                     end_inclusive=end)
    assert due == datetime(2026, 8, 31, 18, 17, tzinfo=CST)


@pytest.mark.parametrize("value", ["every 30s", "25:00", "0 0 0 * *", "*/0 * * * *"])
def test_invalid_schedules(value):
    with pytest.raises(ScheduleError):
        validate_schedule(value)
