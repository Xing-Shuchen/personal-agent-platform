"""``pap`` command line interface."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import spec as spec_mod
from . import gate as gate_mod


def _cmd_validate(args: argparse.Namespace) -> int:
    root = Path(args.root)
    try:
        specs = spec_mod.load_platform(root)
    except spec_mod.SpecError as e:
        print(f"INVALID: {e}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps([s.__dict__ | {"source_path": str(s.source_path)} for s in specs],
                         ensure_ascii=False, indent=2, default=str))
    else:
        for s in specs:
            jobs = ", ".join(j.name for j in s.jobs) or "none"
            print(f"OK {s.name}: profile={s.profile_name} caps={len(s.capabilities)} "
                  f"proactive={s.proactive_enabled} jobs=[{jobs}]")
        print(f"{len(specs)} agent spec(s) valid.")
    return 0


def _cmd_gate(args: argparse.Namespace) -> int:
    decision = gate_mod.decide(args.agent, args.dedupe_key, args.priority, db_path=args.db)
    if args.message:
        gate_mod.append_jsonl(
            args.db.parent / "gate-log.jsonl",
            {
                "ts": gate_mod._now().isoformat(timespec="seconds"),
                "agent": args.agent,
                "type": "message-preview",
                "message": args.message[:500],
            },
        )
    print(json.dumps({"allowed": decision.allowed, "reason": decision.reason}))
    return 0 if decision.allowed else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pap", description="Personal Agent Platform tooling")
    sub = parser.add_subparsers(dest="command", required=True)

    p_validate = sub.add_parser("validate", help="validate all agents/*/agent.yaml specs")
    p_validate.add_argument("--root", default=".", help="platform repo root (default: cwd)")
    p_validate.add_argument("--json", action="store_true", help="machine-readable output")
    p_validate.set_defaults(func=_cmd_validate)

    p_gate = sub.add_parser("gate", help="shared proactive gate (exit 0 = allow, 1 = deny)")
    p_gate.add_argument("--agent", required=True, help="agent name")
    p_gate.add_argument("--dedupe-key", required=True,
                        help="stable key derived from concepts, not wording")
    p_gate.add_argument("--priority", required=True, type=int,
                        help="0..100 interruption priority")
    p_gate.add_argument("--message", default="",
                        help="candidate message (audited to gate-log, not validated)")
    p_gate.add_argument("--db", type=Path, default=gate_mod.DEFAULT_DB,
                        help="gate state file (log is written next to it)")
    p_gate.set_defaults(func=_cmd_gate)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
