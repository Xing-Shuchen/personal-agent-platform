"""Model usage for one run, as the runner reported it (§31, §41).

§31 requires PAP to retain execution metadata — model, provider, input tokens,
output tokens, cost — separately from canonical Historian artifacts.  PAP owns
model policy (§35) but it does not call the provider itself: the OpenClaw turn
does.  So PAP can only record what the runner says afterwards, and this module
is the whole of how it asks.

Three read-only surfaces are used, all *after* the turn, all attributable to
exactly one run because PAP chooses the session key:

``openclaw sessions --agent <id> --json``
    The runner's supported per-session view, which reports the session's
    ``inputTokens``/``outputTokens`` (and the model it ran).  The session is
    located by the key PAP assigned — ``agent:<agent>:pap-<run_id>`` — so a
    concurrent run's session can never be mistaken for this one.

the agent's trajectory store
    ``$OPENCLAW_STATE_DIR/agents/<agent>/agent/openclaw-agent.sqlite``, whose
    ``trajectory_runtime_events`` rows hold the run's completed model call
    including the provider-reported cost.  This is the runner's own state, read
    read-only and only for the run's own session.

the agent's transcript store
    the same SQLite file, whose ``session_nodes``/``transcript_events`` rows hold
the turn's terminal message.  A provider that refused the generated text is
named there and nowhere else, so PAP reads it to classify the failure rather
than guessing from the CLI's rendered copy.

Everything here is best effort, and deliberately so: usage that cannot be read
is recorded as *absent*, never as zero.  A run whose usage is unobservable is
still a successful run, and a fabricated ``cost: 0.0`` would be a lie about
money.  The two surfaces also cover each other — the trajectory store still
answers when the CLI is unavailable, and the CLI still answers when the store
has been rotated or its schema has moved on.
"""

from __future__ import annotations

import json
import os
import sqlite3
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Mapping

from paplog.core import content_metadata

#: Sessions are listed newest-first; a just-finished run is at the head, and the
#: window only needs to be wide enough to survive concurrent runs.
SESSION_SCAN_LIMIT = 50

#: The terminal event is the last thing the runner wrote for the session, so a
#: short window reaches it without reading a whole transcript.
TRANSCRIPT_SCAN_LIMIT = 20

_PROBE_TIMEOUT_SECONDS = 30


def session_key(agent_id: str, run_id: str) -> str:
    """The OpenClaw session key PAP assigns to a run's model turn.

    The invocation and the usage lookup must agree on this, or usage silently
    detaches from the run that produced it, so both derive it here.

    The key is canonical lower case because the runner stores it that way: a
    run id in upper case (the ULID scheme) would otherwise be passed verbatim
    to ``--session-key`` and never match the stored row, so usage and the
    provider-failure reading would both come back empty.
    """

    return f"agent:{agent_id}:pap-{run_id}".lower()


def _runner_binary() -> str:
    return os.environ.get("PAP_OPENCLAW_BIN", "openclaw")


def _state_dir() -> Path:
    configured = os.environ.get("PAP_OPENCLAW_STATE_DIR") or os.environ.get("OPENCLAW_STATE_DIR")
    if configured:
        return Path(configured).expanduser()
    return Path("~/.openclaw").expanduser()


def _token_count(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value if value >= 0 else None


def _amount(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value) if value >= 0 else None


def session_usage(
    agent_id: str,
    run_id: str,
    *,
    command_runner: Callable[..., subprocess.CompletedProcess[str]] | None = None,
    timeout: int = _PROBE_TIMEOUT_SECONDS,
) -> dict[str, Any] | None:
    """Read this run's session from the runner's session list, or ``None``."""

    command = [
        _runner_binary(), "sessions", "--agent", agent_id,
        "--limit", str(SESSION_SCAN_LIMIT), "--json",
    ]
    runner = command_runner or subprocess.run
    try:
        completed = runner(command, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError):
        return None
    if getattr(completed, "returncode", 1):
        return None
    try:
        payload = json.loads(getattr(completed, "stdout", "") or "")
    except (TypeError, ValueError):
        return None
    sessions = payload.get("sessions") if isinstance(payload, Mapping) else None
    if not isinstance(sessions, list):
        return None
    wanted = session_key(agent_id, run_id)
    for session in sessions:
        if not isinstance(session, Mapping):
            continue
        listed_key = session.get("key")
        if not isinstance(listed_key, str) or listed_key.lower() != wanted:
            continue
        session_id = session.get("sessionId")
        return {
            "session_id": session_id if isinstance(session_id, str) else None,
            "input_tokens": _token_count(session.get("inputTokens")),
            "output_tokens": _token_count(session.get("outputTokens")),
            "model": session.get("model") if isinstance(session.get("model"), str) else None,
            "provider": session.get("modelProvider") if isinstance(session.get("modelProvider"), str) else None,
        }
    return None


def trajectory_usage(agent_id: str, run_id: str, *, state_dir: Path | None = None) -> dict[str, Any] | None:
    """Read this run's completed model call from the runner's trajectory store.

    The store is the runner's private state, so an unreadable or unfamiliar
    store is simply no data — never an error and never an assumption.
    """

    path = (state_dir or _state_dir()) / "agents" / agent_id / "agent" / "openclaw-agent.sqlite"
    if not path.is_file():
        return None
    wanted = session_key(agent_id, run_id)
    try:
        connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    except sqlite3.Error:
        return None
    try:
        rows = connection.execute(
            "select event_json from trajectory_runtime_events where lower(event_json) like ? order by seq",
            (f"%{wanted}%",),
        ).fetchall()
    except sqlite3.Error:
        return None
    finally:
        connection.close()

    result: dict[str, Any] | None = None
    for (raw,) in rows:
        try:
            event = json.loads(raw)
        except (TypeError, ValueError):
            continue
        if not isinstance(event, Mapping):
            continue
        if event.get("type") != "model.completed" or str(event.get("sessionKey") or "").lower() != wanted:
            continue
        usage = event.get("data")
        usage = usage.get("usage") if isinstance(usage, Mapping) else None
        if not isinstance(usage, Mapping):
            continue
        # A run makes one completed model call, and it carries the run's totals;
        # if a runner ever reports several, the last one is the run's outcome.
        cost = usage.get("cost")
        result = {
            "input_tokens": _token_count(usage.get("input")),
            "output_tokens": _token_count(usage.get("output")),
            "cache_read_tokens": _token_count(usage.get("cacheRead")),
            "cache_write_tokens": _token_count(usage.get("cacheWrite")),
            "reasoning_tokens": _token_count(usage.get("reasoningTokens")),
            "cost": _amount(cost.get("total")) if isinstance(cost, Mapping) else None,
        }
    return result


def _event_timestamp(value: Any) -> str | None:
    """Return an RFC3339 timestamp only when the runner supplied a valid one."""

    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).isoformat()
    except ValueError:
        return None


def trajectory_tools(agent_id: str, run_id: str, *, state_dir: Path | None = None) -> list[dict[str, Any]]:
    """Read OpenClaw's recorded tool lifecycle for precisely one PAP run.

    OpenClaw is the tool executor for an OpenClaw-backed PAP turn; its
    trajectory database is therefore the authoritative integration boundary.
    This intentionally keeps tool arguments and results as hash/size metadata,
    never as tool content.  An unknown trajectory schema is best-effort no
    data, matching :func:`trajectory_usage`.
    """

    path = (state_dir or _state_dir()) / "agents" / agent_id / "agent" / "openclaw-agent.sqlite"
    if not path.is_file():
        return []
    wanted = session_key(agent_id, run_id)
    try:
        connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    except sqlite3.Error:
        return []
    try:
        rows = connection.execute(
            "select event_json from trajectory_runtime_events where lower(event_json) like ? order by seq",
            (f"%{wanted}%",),
        ).fetchall()
    except sqlite3.Error:
        return []
    finally:
        connection.close()

    calls: dict[str, dict[str, Any]] = {}
    result: list[dict[str, Any]] = []
    for (raw,) in rows:
        try:
            event = json.loads(raw)
        except (TypeError, ValueError):
            continue
        if not isinstance(event, Mapping) or str(event.get("sessionKey") or "").lower() != wanted:
            continue
        data = event.get("data")
        if not isinstance(data, Mapping):
            continue
        call_id = data.get("toolCallId")
        if not isinstance(call_id, str) or not call_id:
            continue
        name = data.get("name")
        name = name if isinstance(name, str) and name else "unknown"
        if event.get("type") == "tool.call":
            calls[call_id] = {
                "tool_call_id": call_id,
                "name": name,
                "arguments": content_metadata(data.get("args")),
                "started_at": _event_timestamp(event.get("ts")),
            }
            continue
        if event.get("type") != "tool.result":
            continue
        call = calls.pop(call_id, {"tool_call_id": call_id, "name": name})
        completed_at = _event_timestamp(event.get("ts"))
        duration_ms: float | None = None
        if call.get("started_at") and completed_at:
            try:
                duration_ms = max(
                    0.0,
                    (datetime.fromisoformat(completed_at) - datetime.fromisoformat(str(call["started_at"]))).total_seconds() * 1000,
                )
            except ValueError:
                pass
        result.append({
            **call,
            "completed_at": completed_at,
            "duration_ms": duration_ms,
            "success": data.get("success") is True,
            "result": content_metadata(data.get("result")),
        })
    # Preserve incomplete tool calls: their started lifecycle is valuable for
    # diagnosing a session that dies during tool execution.
    result.extend(calls.values())
    return result


def session_failure(agent_id: str, run_id: str, *, state_dir: Path | None = None) -> str | None:
    """Read the provider failure that ended this run's turn, or ``None``.

    §34 only retries *transient* trouble, so a provider that refused the
    generated text has to be named before the scheduler can tell it apart from
    transport trouble.  The refusal is the runner's own record of the turn,
    read read-only and only for this run's session. Try uncompressed transcript
    JSON first, then compressed transcript frames via the system zstd CLI,
    then trajectory events. Unavailable or invalid compressed rows are skipped.
    """

    path = (state_dir or _state_dir()) / "agents" / agent_id / "agent" / "openclaw-agent.sqlite"
    if not path.is_file():
        return None
    wanted = session_key(agent_id, run_id)
    try:
        connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    except sqlite3.Error:
        return None
    try:
        row = connection.execute(
            "select current_session_id from session_nodes where lower(session_key) = ?",
            (wanted,),
        ).fetchone()
        if not row or not isinstance(row[0], str):
            return None
        events = connection.execute(
            "select event_json from transcript_events where session_id = ? order by seq desc limit ?",
            (row[0], TRANSCRIPT_SCAN_LIMIT),
        ).fetchall()
        for (raw,) in events:
            try:
                event = json.loads(raw)
            except (TypeError, ValueError):
                continue
            message = event.get("message") if isinstance(event, Mapping) else None
            if not isinstance(message, Mapping) or message.get("stopReason") != "error":
                continue
            detail = message.get("errorMessage")
            if isinstance(detail, str) and detail.strip():
                code = message.get("errorCode")
                if isinstance(code, str) and code.strip():
                    return f"{code.strip()}: {detail.strip()}"
                return detail.strip()
        try:
            compressed_events = connection.execute(
                "select event_zstd from transcript_events where session_id = ? order by seq desc limit ?",
                (row[0], TRANSCRIPT_SCAN_LIMIT),
            ).fetchall()
        except sqlite3.OperationalError:
            # Older stores do not have a compressed transcript column.
            compressed_events = []
        for (frame,) in compressed_events:
            if not isinstance(frame, bytes) or not frame:
                continue
            try:
                decoded = subprocess.run(
                    ["zstd", "-d", "--stdout"], input=frame,
                    capture_output=True, timeout=5,
                )
                if decoded.returncode:
                    continue
                event = json.loads(decoded.stdout)
            except (OSError, subprocess.SubprocessError, TypeError, ValueError):
                continue
            message = event.get("message") if isinstance(event, Mapping) else None
            if not isinstance(message, Mapping) or message.get("stopReason") != "error":
                continue
            detail = message.get("errorMessage")
            if isinstance(detail, str) and detail.strip():
                code = message.get("errorCode")
                if isinstance(code, str) and code.strip():
                    return f"{code.strip()}: {detail.strip()}"
                return detail.strip()
        events = connection.execute(
            "select event_json from trajectory_runtime_events where session_id = ? order by seq desc",
            (row[0],),
        ).fetchall()
        for (raw,) in events:
            try:
                event = json.loads(raw)
            except (TypeError, ValueError):
                continue
            if not isinstance(event, Mapping) or event.get("type") != "model.completed":
                continue
            data = event.get("data")
            if not isinstance(data, Mapping):
                continue
            messages = data.get("messagesSnapshot")
            candidates = [data]
            if isinstance(messages, list):
                candidates.extend(reversed(messages))
            for message in candidates:
                if not isinstance(message, Mapping):
                    continue
                message = message.get("message", message)
                if not isinstance(message, Mapping):
                    continue
                detail = message.get("errorMessage") or message.get("error")
                if isinstance(detail, Mapping):
                    detail = detail.get("message")
                if isinstance(detail, str) and detail.strip():
                    code = message.get("errorCode")
                    if isinstance(code, str) and code.strip():
                        return f"{code.strip()}: {detail.strip()}"
                    return detail.strip()
    except sqlite3.Error:
        return None
    finally:
        connection.close()
    return None


def probe_model_usage(
    agent_id: str,
    run_id: str,
    *,
    command_runner: Callable[..., subprocess.CompletedProcess[str]] | None = None,
    state_dir: Path | None = None,
) -> dict[str, Any] | None:
    """Collect what the runner reports about one run's model turn.

    Returns ``None`` when nothing could be read, so the caller records no model
    usage at all rather than a block of nulls that looks like a measurement.
    """

    merged: dict[str, Any] = {"session_key": session_key(agent_id, run_id)}
    sources: list[str] = []

    session = session_usage(agent_id, run_id, command_runner=command_runner)
    if session:
        sources.append("openclaw.sessions")
        merged["input_tokens"] = session["input_tokens"]
        merged["output_tokens"] = session["output_tokens"]
        if session["model"]:
            merged["model"] = session["model"]
        if session["provider"]:
            merged["provider"] = session["provider"]

    trajectory = trajectory_usage(agent_id, run_id, state_dir=state_dir)
    if trajectory:
        sources.append("openclaw.trajectory")
        for field in ("input_tokens", "output_tokens", "cache_read_tokens", "cache_write_tokens", "reasoning_tokens"):
            if merged.get(field) is None:
                merged[field] = trajectory[field]
        merged["cost"] = trajectory["cost"]

    if not sources:
        return None
    merged["source"] = "+".join(sources)
    return merged
