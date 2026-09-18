"""§31/§41: model token usage and cost, as reported by the runner.

Everything here is synthetic: the runner's session list is a stub, and its
trajectory store is a SQLite database built at test time with the observed
schema.  No test reads the developer's real OpenClaw state.
"""

import json
import sqlite3
import subprocess
from pathlib import Path

from pap.usage import (
    probe_model_usage,
    session_failure,
    session_key,
    session_usage,
    trajectory_usage,
)

RUN = "run_20260913_051333_e03ac3"
SESSION = f"agent:personal-historian:pap-{RUN}"


def completed(command, returncode=0, stdout="", stderr=""):
    return subprocess.CompletedProcess(command, returncode, stdout=stdout, stderr=stderr)


def session_payload(**overrides):
    record = {
        "key": SESSION,
        "sessionId": "cb77ac79-47c6-4817-9ced-61eaac8354d1",
        "inputTokens": 106795,
        "outputTokens": 28800,
        "model": "deepseek-flash",
        "modelProvider": "deepseek",
    }
    record.update(overrides)
    return json.dumps({"count": 1, "sessions": [record]})


def write_trajectory(state_dir: Path, events, *, agent="personal-historian") -> Path:
    """Build the runner's store with the columns the real one has."""

    path = state_dir / "agents" / agent / "agent" / "openclaw-agent.sqlite"
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.execute(
        """CREATE TABLE trajectory_runtime_events (
             session_id TEXT NOT NULL,
             seq INTEGER NOT NULL,
             run_id TEXT,
             event_json TEXT NOT NULL,
             created_at INTEGER NOT NULL,
             PRIMARY KEY (session_id, seq)
           )"""
    )
    for index, event in enumerate(events):
        connection.execute(
            "INSERT INTO trajectory_runtime_events VALUES (?, ?, ?, ?, ?)",
            (
                event.get("sessionId", "cb77ac79"),
                index,
                event.get("runId"),
                json.dumps(event),
                1789276609741 + index,
            ),
        )
    connection.commit()
    connection.close()
    return path


def model_completed(key=SESSION, *, total=0.085265796):
    return {
        "type": "model.completed",
        "sessionKey": key,
        "sessionId": "cb77ac79",
        "data": {
            "aborted": False,
            "usage": {
                "input": 106795,
                "output": 28800,
                "cacheRead": 2223232,
                "cost": {"total": total},
            },
        },
    }


# --- the session key is the only thing that attributes usage to a run ---------

def test_the_session_key_names_one_run():
    assert session_key("personal-historian", RUN) == SESSION
    assert session_key("personal-historian", RUN) != session_key("personal-historian", RUN + "x")


def test_a_usage_command_is_issued_for_the_declared_agent():
    seen = {}

    def runner(command, **kwargs):
        seen["command"] = command
        return completed(command, 0, session_payload())

    session_usage("personal-historian", RUN, command_runner=runner)
    assert seen["command"][:4] == ["openclaw", "sessions", "--agent", "personal-historian"]
    assert "--json" in seen["command"]


def test_the_matching_session_is_read():
    usage = session_usage(
        "personal-historian", RUN,
        command_runner=lambda command, **kw: completed(command, 0, session_payload()),
    )
    assert usage == {
        "session_id": "cb77ac79-47c6-4817-9ced-61eaac8354d1",
        "input_tokens": 106795,
        "output_tokens": 28800,
        "model": "deepseek-flash",
        "provider": "deepseek",
    }


def test_another_runs_session_is_never_mistaken_for_this_one():
    """The list holds every session the agent has; only one belongs to this run."""

    payload = json.dumps({"sessions": [
        {"key": "agent:personal-historian:pap-run_other", "inputTokens": 5, "outputTokens": 6},
        {"key": SESSION, "inputTokens": 106795, "outputTokens": 28800},
    ]})
    usage = session_usage(
        "personal-historian", RUN,
        command_runner=lambda command, **kw: completed(command, 0, payload),
    )
    assert usage["input_tokens"] == 106795


def test_unreadable_session_output_reads_as_no_usage():
    cases = [
        completed(["openclaw"], 1, ""),                       # the runner failed
        completed(["openclaw"], 0, "not json"),               # nothing to parse
        completed(["openclaw"], 0, '{"sessions": "nope"}'),   # unexpected shape
        completed(["openclaw"], 0, '{"sessions": []}'),       # the run is absent
    ]
    for case in cases:
        assert session_usage(
            "personal-historian", RUN,
            command_runner=lambda command, _case=case, **kw: _case,
        ) is None


def test_a_missing_or_failing_runner_is_not_an_error():
    def missing(command, **kwargs):
        raise FileNotFoundError("openclaw not found")

    def timing_out(command, **kwargs):
        raise subprocess.TimeoutExpired(command, 1)

    assert session_usage("personal-historian", RUN, command_runner=missing) is None
    assert session_usage("personal-historian", RUN, command_runner=timing_out) is None


def test_impossible_counts_are_not_reported_as_measurements():
    payload = json.dumps({"sessions": [
        {"key": SESSION, "inputTokens": -1, "outputTokens": "many", "model": 7},
    ]})
    usage = session_usage(
        "personal-historian", RUN,
        command_runner=lambda command, **kw: completed(command, 0, payload),
    )
    assert usage["input_tokens"] is None
    assert usage["output_tokens"] is None
    assert usage["model"] is None


# --- the trajectory store supplies the cost -----------------------------------

def test_the_trajectory_store_reports_the_runs_cost(tmp_path):
    write_trajectory(tmp_path, [
        {"type": "session.started", "sessionKey": SESSION},
        model_completed(),
        {"type": "session.ended", "sessionKey": SESSION},
    ])
    assert trajectory_usage("personal-historian", RUN, state_dir=tmp_path) == {
        "input_tokens": 106795,
        "output_tokens": 28800,
        "cost": 0.085265796,
    }


def test_another_sessions_completed_call_is_ignored(tmp_path):
    write_trajectory(tmp_path, [
        model_completed("agent:personal-historian:pap-run_other", total=99.0),
        model_completed(),
    ])
    assert trajectory_usage("personal-historian", RUN, state_dir=tmp_path)["cost"] == 0.085265796


def test_a_store_without_this_run_reports_nothing(tmp_path):
    write_trajectory(tmp_path, [{"type": "session.started", "sessionKey": SESSION}])
    assert trajectory_usage("personal-historian", RUN, state_dir=tmp_path) is None


def test_a_missing_store_is_not_an_error(tmp_path):
    assert trajectory_usage("personal-historian", RUN, state_dir=tmp_path / "absent") is None


def test_a_store_with_an_unfamiliar_schema_is_not_an_error(tmp_path):
    """The store belongs to the runner; if it moves on, PAP simply has no cost."""

    path = tmp_path / "agents" / "personal-historian" / "agent" / "openclaw-agent.sqlite"
    path.parent.mkdir(parents=True)
    connection = sqlite3.connect(path)
    connection.execute("CREATE TABLE something_else (a TEXT)")
    connection.commit()
    connection.close()
    assert trajectory_usage("personal-historian", RUN, state_dir=tmp_path) is None


# --- the two surfaces cover each other ----------------------------------------

def test_both_surfaces_are_merged_into_one_record(tmp_path):
    write_trajectory(tmp_path, [model_completed()])
    probe = probe_model_usage(
        "personal-historian", RUN,
        command_runner=lambda command, **kw: completed(command, 0, session_payload()),
        state_dir=tmp_path,
    )
    assert probe["input_tokens"] == 106795
    assert probe["output_tokens"] == 28800
    assert probe["cost"] == 0.085265796
    assert probe["provider"] == "deepseek"
    assert probe["session_key"] == SESSION
    assert probe["source"] == "openclaw.sessions+openclaw.trajectory"


def test_the_store_still_answers_when_the_cli_does_not(tmp_path):
    write_trajectory(tmp_path, [model_completed()])

    def unavailable(command, **kwargs):
        raise FileNotFoundError("openclaw not found")

    probe = probe_model_usage("personal-historian", RUN, command_runner=unavailable, state_dir=tmp_path)
    assert probe["input_tokens"] == 106795
    assert probe["cost"] == 0.085265796
    assert probe["source"] == "openclaw.trajectory"


def test_the_cli_still_answers_when_the_store_does_not(tmp_path):
    probe = probe_model_usage(
        "personal-historian", RUN,
        command_runner=lambda command, **kw: completed(command, 0, session_payload()),
        state_dir=tmp_path,
    )
    assert probe["source"] == "openclaw.sessions"
    # Cost is unmeasurable here, and an unmeasurable cost is not zero.
    assert "cost" not in probe


def test_nothing_readable_is_no_usage_at_all(tmp_path):
    def unavailable(command, **kwargs):
        raise FileNotFoundError("openclaw not found")

    assert probe_model_usage(
        "personal-historian", RUN, command_runner=unavailable, state_dir=tmp_path,
    ) is None


# --- the run's terminal provider failure, read from its own transcript --------

WH_RUN = "run_20260918_000701_bc96f2"
WH_SESSION = session_key("world-historian", WH_RUN)


def write_transcript(state_dir: Path, events, *, agent="world-historian", session=WH_SESSION) -> Path:
    """Build the runner's session + transcript store with the observed schema."""

    path = state_dir / "agents" / agent / "agent" / "openclaw-agent.sqlite"
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.execute(
        "CREATE TABLE session_nodes (session_key TEXT PRIMARY KEY, current_session_id TEXT NOT NULL)"
    )
    connection.execute(
        """CREATE TABLE transcript_events (
             session_id TEXT NOT NULL,
             seq INTEGER NOT NULL,
             event_json TEXT NOT NULL,
             PRIMARY KEY (session_id, seq)
           )"""
    )
    connection.execute("INSERT INTO session_nodes VALUES (?, ?)", (session, "d6294eb2"))
    for index, event in enumerate(events):
        connection.execute(
            "INSERT INTO transcript_events VALUES (?, ?, ?)",
            ("d6294eb2", index, json.dumps(event)),
        )
    connection.commit()
    connection.close()
    return path


def test_a_provider_refusal_is_read_from_the_run_transcript(tmp_path):
    write_transcript(
        tmp_path,
        [
            {"type": "message", "message": {"role": "toolResult", "content": [{"type": "text", "text": "ok"}]}},
            {"type": "message", "message": {
                "role": "assistant", "stopReason": "error",
                "errorMessage": "Output data may contain inappropriate content.",
                "errorCode": "data_inspection_failed",
            }},
        ],
    )
    assert session_failure("world-historian", WH_RUN, state_dir=tmp_path) == (
        "data_inspection_failed: Output data may contain inappropriate content."
    )


def test_a_settled_turn_reports_no_failure(tmp_path):
    write_transcript(
        tmp_path,
        [{"type": "message", "message": {"role": "assistant", "stopReason": "stop"}}],
    )
    assert session_failure("world-historian", WH_RUN, state_dir=tmp_path) is None


def test_another_runs_session_key_is_not_this_runs_failure(tmp_path):
    write_transcript(tmp_path, [{"type": "message", "message": {
        "role": "assistant", "stopReason": "error", "errorMessage": "Output data may contain inappropriate content.",
    }}])
    assert session_failure("world-historian", "run_20260918_999999_zzzzzz", state_dir=tmp_path) is None


def test_an_unreadable_store_is_no_failure_reading_at_all(tmp_path):
    assert session_failure("world-historian", WH_RUN, state_dir=tmp_path / "absent") is None
