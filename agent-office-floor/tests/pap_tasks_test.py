import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from datetime import datetime, timedelta, timezone


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/pap_tasks.py"
SPEC = importlib.util.spec_from_file_location("pap_tasks", SCRIPT)
assert SPEC and SPEC.loader
pap_tasks = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(pap_tasks)


class PapTasksTest(unittest.TestCase):
    def test_run_projection_excludes_payloads_and_does_not_claim_liveness(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "runs.jsonl"
            path.write_text("\n".join(json.dumps(row) for row in [
                {"event": "run.started", "run_id": "a", "agent_id": "alpha", "job_id": "daily",
                 "started_at": "2026-10-01T00:00:00Z", "input": "PRIVATE_INPUT"},
                {"event": "run.completed", "run_id": "a", "agent_id": "alpha", "job_id": "daily",
                 "completed_at": "2026-10-01T00:01:00Z", "status": "success", "response": "PRIVATE_RESPONSE"},
                {"event": "run.started", "run_id": "b", "agent_id": "beta", "job_id": "weekly",
                 "started_at": "2026-09-01T00:00:00Z", "error": "PRIVATE_ERROR"},
            ]), encoding="utf-8")
            active_runs, open_runs, open_count, recent = pap_tasks.run_metadata(path)
            self.assertEqual(active_runs, [])
            self.assertEqual([item["runId"] for item in open_runs], ["b"])
            self.assertEqual(open_count, 1)
            self.assertEqual([item["runId"] for item in recent], ["a"])
            output = json.dumps([active_runs, open_runs, recent])
            for private in ("PRIVATE_INPUT", "PRIVATE_RESPONSE", "PRIVATE_ERROR"):
                self.assertNotIn(private, output)
            self.assertNotIn("running", output)

    def test_process_identity_must_match_and_is_not_projected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            proc = root / "proc"
            (proc / "321").mkdir(parents=True)
            (proc / "321" / "stat").write_text("321 (pap worker) " + " ".join(["S"] + ["0"] * 18 + ["456"]), encoding="utf-8")
            log = root / "runs.jsonl"
            log.write_text("\n".join(json.dumps({"event": "run.started", "run_id": run_id,
                "agent_id": "alpha", "started_at": "2026-10-04T00:00:00Z",
                "process_id": 321, "process_start_ticks": ticks}) for run_id, ticks in
                [("matching", 456), ("reused-pid", 455)]), encoding="utf-8")
            active, unconfirmed, open_count, recent = pap_tasks.run_metadata(log, proc)
            self.assertEqual([item["runId"] for item in active], ["matching"])
            self.assertEqual([item["runId"] for item in unconfirmed], ["reused-pid"])
            self.assertEqual(open_count, 1)
            self.assertEqual(recent, [])
            self.assertNotIn("process_id", json.dumps([active, unconfirmed]))
            self.assertNotIn("456", json.dumps([active, unconfirmed]))
            (proc / "321" / "stat").write_text("321 (pap worker) " + " ".join(["Z"] + ["0"] * 18 + ["456"]), encoding="utf-8")
            active, unconfirmed, open_count, _ = pap_tasks.run_metadata(log, proc)
            self.assertEqual(active, [])
            self.assertEqual({item["runId"] for item in unconfirmed}, {"matching", "reused-pid"})
            self.assertEqual(open_count, 2)

    def test_malformed_run_metadata_is_not_forwarded(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "runs.jsonl"
            path.write_text(json.dumps({"event": "run.completed", "run_id": "r", "agent_id": {"secret": "PRIVATE"},
                                        "job_id": "job", "completed_at": "not a time", "status": {"secret": "PRIVATE"}}), encoding="utf-8")
            active, unconfirmed, open_count, recent = pap_tasks.run_metadata(path)
            self.assertEqual(active, [])
            self.assertEqual(unconfirmed, [])
            self.assertEqual(open_count, 0)
            self.assertEqual(recent, [{"runId": "r", "agentId": None, "jobId": "job",
                                       "completedAt": None, "status": None}])
            self.assertNotIn("PRIVATE", json.dumps(recent))

    def test_unconfirmed_count_is_not_truncated_with_display_rows(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "runs.jsonl"
            path.write_text("\n".join(json.dumps({"event": "run.started", "run_id": f"r{i}",
                "agent_id": "a", "started_at": "2026-10-04T00:00:00Z"}) for i in range(14)), encoding="utf-8")
            active, unconfirmed, open_count, recent = pap_tasks.run_metadata(path)
            self.assertEqual(active, [])
            self.assertEqual(len(unconfirmed), 10)
            self.assertEqual(open_count, 14)
            self.assertEqual(recent, [])

    def test_next_cron_uses_pap_matcher_and_timezone(self):
        now = datetime(2026, 10, 3, 0, 0, tzinfo=timezone.utc)
        self.assertEqual(pap_tasks.next_nominal("0 9 * * *", now, "Asia/Shanghai"),
                         "2026-10-03T09:00+08:00")

    def test_long_interval_and_clock_do_not_need_minute_scan(self):
        now = datetime(2026, 10, 3, 0, 0, tzinfo=timezone.utc)
        self.assertEqual(pap_tasks.next_nominal("every 14d from 2026-09-12 20:43 tz Asia/Shanghai",
                                                now, "Asia/Shanghai"), "2026-10-10T20:43+08:00")
        self.assertEqual(pap_tasks.next_nominal("09:30 tz Asia/Shanghai", now, None),
                         "2026-10-03T09:30+08:00")
        self.assertEqual(pap_tasks.next_nominal("every 30m", now, "Asia/Shanghai"),
                         "2026-10-03T08:30+08:00")

    def test_leap_day_cron_crosses_non_leap_century(self):
        now = datetime(2097, 3, 1, 0, 0, tzinfo=timezone.utc)
        self.assertEqual(pap_tasks.next_nominal("0 9 29 2 *", now, "UTC"),
                         "2104-02-29T09:00+00:00")

    def test_recurring_forecast_keeps_every_occurrence_in_first_hour_and_eight_later(self):
        now = datetime(2026, 10, 4, 0, 0, tzinfo=timezone.utc)
        entries = pap_tasks.future_occurrences("alpha/quarter-hour", "alpha", "quarter-hour",
                                               "every 15m", "UTC", True, now, None)
        times = [datetime.fromisoformat(item["dispatchAt"]) for item in entries]
        self.assertEqual(times[:4], [now + timedelta(minutes=minutes) for minutes in (15, 30, 45, 60)])
        self.assertEqual(times[4:], [now + timedelta(minutes=minutes) for minutes in
                                     (75, 90, 105, 120, 135, 150, 165, 180)])
        self.assertEqual(len({item["key"] + item["nominalAt"] for item in entries}), len(entries))

    def test_jittered_forecast_is_chronological_even_when_dispatch_reorders_slots(self):
        now = datetime(2026, 10, 4, 0, 0, tzinfo=timezone.utc)
        entries = pap_tasks.future_occurrences("alpha/minutely", "alpha", "minutely",
                                               "every 1m", "UTC", True, now, "test-seed")
        times = [datetime.fromisoformat(item["dispatchAt"]) for item in entries]
        self.assertEqual(times, sorted(times))
        self.assertTrue(all(instant > now for instant in times))
        self.assertEqual(sum(instant > now + timedelta(hours=1) for instant in times), 8)

    def test_repeated_dst_hour_keeps_both_real_occurrences(self):
        now = datetime(2026, 11, 1, 5, 40, tzinfo=timezone.utc)
        self.assertEqual(pap_tasks.next_nominal("every 30m", now, "America/New_York"),
                         "2026-11-01T01:00-05:00")
        self.assertEqual(pap_tasks.next_nominal("01:30 tz America/New_York", now, None),
                         "2026-11-01T01:30-05:00")
        self.assertEqual(pap_tasks.next_nominal("30 1 * * *", now, "America/New_York"),
                         "2026-11-01T01:30-05:00")
        entries = pap_tasks.future_occurrences("a/half-hour", "a", "half-hour", "every 30m",
                                               "America/New_York", True, now, None)
        actual = [datetime.fromisoformat(row["dispatchAt"]).astimezone(timezone.utc) for row in entries[:3]]
        self.assertEqual(actual, [datetime(2026, 11, 1, 6, minute, tzinfo=timezone.utc)
                                  for minute in (0, 30)] + [datetime(2026, 11, 1, 7, 0, tzinfo=timezone.utc)])

    def test_jitter_uses_scheduler_local_slot_not_job_timezone(self):
        now = datetime(2026, 10, 4, 0, 0, tzinfo=timezone.utc)
        key = "alpha/foreign-clock"
        entries = pap_tasks.future_occurrences(key, "alpha", "foreign-clock", "every 30m",
                                               "America/New_York", True, now, "seed")
        self.assertTrue(entries)
        first = entries[0]
        nominal = datetime.fromisoformat(first["nominalAt"])
        dispatch = datetime.fromisoformat(first["dispatchAt"])
        expected_offset = pap_tasks._jitter_minutes("seed", key, nominal.astimezone(now.astimezone().tzinfo))
        self.assertEqual(dispatch.astimezone(timezone.utc) - nominal.astimezone(timezone.utc),
                         timedelta(minutes=expected_offset))


if __name__ == "__main__":
    unittest.main()
