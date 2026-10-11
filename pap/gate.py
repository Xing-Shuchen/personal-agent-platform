"""The shared proactive gate — mechanical interruption discipline.

Design (matches the SOUL/skill contracts in agents/):

- every proactive delivery must pass through ``decide``/CLI ``pap gate``;
- a stable ``dedupe_key`` (derived from concepts, not wording) prevents
  repeats within a per-agent TTL window;
- low-priority items are rejected during local quiet hours;
- an exponential backoff floor (4h → 32h) escalates after repeated denials
  so a chatty agent silences itself;
- every decision is appended to ``var/state/gate-log.jsonl`` for audit.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .state import append_jsonl, file_lock, load_state, save_state

DEFAULT_DB = Path("var/state/gate-state.json")
DEFAULT_LOG = Path("var/state/gate-log.jsonl")

MIN_PRIORITY = 70          # daytime bar for interruption-worthy items
QUIET_PRIORITY = 90        # required bar inside quiet hours
QUIET_START = 22           # local hours [22:00, 08:00)
QUIET_END = 8
DEDUPE_TTL_HOURS = 168     # same key may not be delivered again for 7 days
BACKOFF_BASE_HOURS = 4     # denial backoff floor: 4h, 8h, 16h, 32h (capped)
BACKOFF_MAX_HOURS = 32


class GateDecision(dict):
    """dict with a fixed shape; truthiness = allowed."""

    @property
    def allowed(self) -> bool:
        return bool(self.get("allowed"))

    @property
    def reason(self) -> str:
        return str(self.get("reason", ""))


def _now() -> datetime:
    return datetime.now(timezone.utc).astimezone()


def _in_quiet_hours(now: datetime) -> bool:
    return now.hour >= QUIET_START or now.hour < QUIET_END


def _parse_ts(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _locked_state(db_path: Path):
    """Serialize gate decisions: dedupe/backoff is a read-modify-write cycle.

    Two proactive agents asking at the same moment must not both see the key as
    undelivered and both get ``allowed``; the lock makes one wait for the
    other's recorded decision.
    """
    return file_lock(db_path)


def decide(
    agent: str,
    dedupe_key: str,
    priority: int,
    *,
    now: datetime | None = None,
    db_path: Path = DEFAULT_DB,
) -> GateDecision:
    """Return the gate decision for one candidate delivery and record it."""
    if not agent or not agent.strip():
        return GateDecision(allowed=False, reason="agent must be a non-empty identifier")
    if not dedupe_key or not dedupe_key.strip():
        return GateDecision(allowed=False, reason="dedupe-key must be a non-empty stable key")
    if not isinstance(priority, int) or isinstance(priority, bool) or not 0 <= priority <= 100:
        return GateDecision(allowed=False, reason="priority must be an integer in 0..100")

    now = now or _now()
    with _locked_state(db_path):
        state = load_state(db_path)
        agents = state.setdefault("agents", {})
        entry = agents.setdefault(agent, {"delivered": {}, "attempts": []})
        attempts = [a for a in entry.get("attempts", []) if isinstance(a, dict)]
        delivered: dict[str, str] = entry.get("delivered", {})

        reasons: list[str] = []

        # 1. Exponential denial backoff: repeated denials raise the silence floor.
        if attempts:
            last = attempts[-1]
            last_ts = _parse_ts(last.get("ts"))
            if last_ts is not None:
                streak = 0
                for a in reversed(attempts):
                    if a.get("allowed"):
                        break
                    streak += 1
                floor = min(BACKOFF_BASE_HOURS * (2 ** max(0, streak - 1)), BACKOFF_MAX_HOURS)
                if not last.get("allowed") and now - last_ts < timedelta(hours=floor):
                    reasons.append(
                        f"backoff: agent denied {streak}x; silence floor {floor}h not elapsed"
                    )

        # 2. Dedupe by stable key within the TTL window.
        last_delivered = _parse_ts(delivered.get(dedupe_key))
        if last_delivered is not None:
            elapsed = now - last_delivered
            if elapsed < timedelta(hours=DEDUPE_TTL_HOURS):
                reasons.append(
                    f"dedupe: key delivered {elapsed.total_seconds() / 3600:.1f}h ago "
                    f"(TTL {DEDUPE_TTL_HOURS}h)"
                )

        # 3. Priority bar, higher during local quiet hours.
        if _in_quiet_hours(now):
            if priority < QUIET_PRIORITY:
                reasons.append(f"quiet-hours: priority {priority} < {QUIET_PRIORITY}")
        elif priority < MIN_PRIORITY:
            reasons.append(f"priority: {priority} < {MIN_PRIORITY}")

        allowed = not reasons
        record = {
            "ts": now.isoformat(timespec="seconds"),
            "agent": agent,
            "dedupe_key": dedupe_key,
            "priority": priority,
            "allowed": allowed,
            "reason": reasons[0] if reasons else "passed",
        }

        attempts.append({"ts": record["ts"], "allowed": allowed, "priority": priority,
                         "key": dedupe_key, "reason": record["reason"]})
        entry["attempts"] = attempts[-100:]  # bounded history
        if allowed:
            delivered[dedupe_key] = record["ts"]
            entry["delivered"] = delivered
        agents[agent] = entry
        state["agents"] = agents

        save_state(db_path, state)
        log_path = db_path.parent / "gate-log.jsonl"
        append_jsonl(log_path, record)
    return GateDecision(record)


def history(agent: str | None = None, log_path: Path = DEFAULT_LOG) -> list[dict]:
    records = []
    if log_path.exists():
        for line in log_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                # A truncated append must not make the whole audit log unreadable.
                continue
            if not isinstance(rec, dict):
                continue
            if agent is None or rec.get("agent") == agent:
                records.append(rec)
    return records


def _print_decision(decision: GateDecision) -> None:
    print(json.dumps({"allowed": decision.allowed, "reason": decision.reason}))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pap gate", description="Shared proactive gate")
    parser.add_argument("--agent", required=True, help="agent name")
    parser.add_argument("--dedupe-key", required=True, help="stable key from concepts, not wording")
    parser.add_argument("--priority", required=True, type=int, help="0..100 interruption priority")
    parser.add_argument("--message", default="", help="candidate message (audited, not validated)")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB, help="gate state file")
    args = parser.parse_args(argv)

    decision = decide(args.agent, args.dedupe_key, args.priority, db_path=args.db)
    if args.message:
        log_path = args.db.parent / "gate-log.jsonl"
        append_jsonl(log_path, {
            "ts": _now().isoformat(timespec="seconds"),
            "agent": args.agent,
            "type": "message-preview",
            "message": args.message[:500],
        })
    _print_decision(decision)
    return 0 if decision.allowed else 1


if __name__ == "__main__":
    sys.exit(main())
