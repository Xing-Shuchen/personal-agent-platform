"""``pap`` command line interface."""

from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime
import json
import os
import sys
from pathlib import Path
from typing import Mapping

from . import spec as spec_mod
from . import gate as gate_mod
from . import dismiss as dismiss_mod
from . import run as run_mod
from . import artifact as artifact_mod
from . import scheduler as scheduler_mod
from . import cognition as cognition_mod
from .state import load_json


def _specs(root: Path) -> list[spec_mod.AgentSpec]:
    return spec_mod.load_platform(root)


def _find_spec(root: Path, name: str) -> spec_mod.AgentSpec:
    for spec in _specs(root):
        if spec.name == name:
            if not spec.enabled:
                raise spec_mod.SpecError(f"agent {name!r} is disabled; enable it in var/config/agents.yaml")
            return spec
    raise spec_mod.SpecError(f"unknown agent {name!r}")


def _path_under(root: Path, value: Path) -> Path:
    return value if value.is_absolute() else root / value


def _parse_kv(values: list[str]) -> dict[str, object]:
    result: dict[str, object] = {}
    for value in values:
        key, separator, raw = value.partition("=")
        if not separator or not key:
            raise ValueError(f"expected KEY=VALUE, got {value!r}")
        try:
            result[key] = json.loads(raw)
        except json.JSONDecodeError:
            result[key] = raw
    return result


def _cmd_validate(args: argparse.Namespace) -> int:
    root = Path(args.root)
    try:
        specs = spec_mod.load_platform(root)
    except spec_mod.SpecError as e:
        print(f"INVALID: {e}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps([asdict(s) | {"source_path": str(s.source_path)} for s in specs],
                         ensure_ascii=False, indent=2, default=str))
    else:
        for s in specs:
            jobs = ", ".join(j.name for j in s.jobs) or "none"
            print(f"OK {s.name}: profile={s.profile_name} caps={len(s.capabilities)} "
                  f"enabled={s.enabled} proactive={s.proactive_enabled} jobs=[{jobs}]")
        print(f"{len(specs)} agent spec(s) valid.")
    return 0


def _cmd_cognition(args: argparse.Namespace) -> int:
    argv: list[str] = []
    if args.vault is not None:
        argv += ["--vault", str(args.vault)]
    if args.db is not None:
        argv += ["--db", str(args.db)]
    argv.append(args.cognition_command)
    if args.cognition_command == "index":
        if args.dry_run: argv.append("--dry-run")
        if args.full: argv.append("--full")
    if args.cognition_command == "evidence":
        argv += [args.evidence_id, "--excerpt", str(args.excerpt)]
    if args.cognition_command == "search":
        argv += [args.query, "--limit", str(args.limit)]
        if args.source_type: argv += ["--source-type", args.source_type]
        if args.voice: argv += ["--voice", args.voice]
    if args.cognition_command == "shadow":
        argv += [args.kind]
        if args.run_id: argv += ["--run-id", args.run_id]
    return cognition_mod.main(argv)


def _cmd_agents(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    try:
        specs = _specs(root)
    except spec_mod.SpecError as exc:
        print(f"INVALID: {exc}", file=sys.stderr)
        return 1
    for spec in specs:
        mode = "disabled" if not spec.enabled else (spec.proactive_class if spec.proactive_enabled else "reactive")
        print(f"{spec.name}\t{mode}\t{len(spec.jobs)} job(s)\t{spec.description}")
    return 0


def _cmd_jobs(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    try:
        specs = _specs(root)
    except spec_mod.SpecError as exc:
        print(f"INVALID: {exc}", file=sys.stderr)
        return 1
    for spec in specs:
        if args.agent and spec.name != args.agent:
            continue
        for job in spec.jobs:
            rendered_args = json.dumps(job.args, ensure_ascii=False, sort_keys=True)
            state = "enabled" if spec.enabled and job.enabled else "disabled"
            runner = f"\trunner={job.runner}" if job.runner != "openclaw" else ""
            model = f"\tmodel={job.model}" if job.model is not None else ""
            print(f"{spec.name}/{job.name}\t{job.schedule}\t{job.skill}\t"
                  f"delivery={job.delivery}\t{state}\targs={rendered_args}{runner}{model}")
    return 0


def _cmd_invoke(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    try:
        spec = _find_spec(root, args.agent)
        job_args = _parse_kv(args.arg)
        result = run_mod.invoke(
            root=root,
            spec=spec,
            skill=args.skill,
            input_text=args.input or "",
            args=job_args,
            trigger={"type": "manual"},
            run_log=_path_under(root, args.runs),
        )
    except (spec_mod.SpecError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    if result.response:
        print(result.response)
    if result.error:
        print(result.error, file=sys.stderr)
    return result.returncode


def _cmd_job_run(args: argparse.Namespace) -> int:
    """Run one manifest job through its declared runtime adapter."""
    root = Path(args.root).resolve()
    try:
        if args.job is None:
            if "/" not in args.agent:
                raise ValueError("job must be given as AGENT JOB or AGENT/JOB")
            args.agent, args.job = args.agent.split("/", 1)
        spec = _find_spec(root, args.agent)
        job = next((item for item in spec.jobs if item.name == args.job), None)
        if job is None:
            raise ValueError(f"unknown job {args.agent}/{args.job}")
        job_args = dict(job.args)
        job_args.update(_parse_kv(args.arg))
        result = run_mod.invoke(
            root=root, spec=spec, skill=job.skill, args=job_args,
            trigger={"type": "manual-job", "job_id": job.name},
            run_log=_path_under(root, args.runs), runtime=job.runtime,
            model=job.model,
            runner_backend=job.runner,
            command=job.command,
        )
    except (spec_mod.SpecError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"job": f"{args.agent}/{args.job}", "run_id": result.run_id, "status": result.status, "returncode": result.returncode}, ensure_ascii=False))
    if result.error:
        print(result.error, file=sys.stderr)
    return result.returncode


def _cmd_tick(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    now = None
    if args.now:
        try:
            now = datetime.fromisoformat(args.now)
            if now.tzinfo is None:
                now = now.astimezone()
        except ValueError as exc:
            print(f"ERROR: invalid --now: {exc}", file=sys.stderr)
            return 2
    try:
        results = scheduler_mod.tick(
            root,
            now=now,
            state_path=_path_under(root, args.state),
            run_log=_path_under(root, args.runs),
            delivery_target=args.delivery_target,
            dry_run=args.dry_run,
        )
    except (spec_mod.SpecError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    failed = False
    for item in results:
        run_id = item.run.run_id if item.run else "-"
        status = item.run.status if item.run else "due"
        print(f"{item.job_key}\t{item.slot}\t{status}\t{run_id}\tdelivery={item.delivery}")
        if item.run and item.run.status not in {"success", "not_ready"}:
            failed = True
        if item.delivery in {"failed", "unconfigured"}:
            failed = True
    return 1 if failed else 0


def _cmd_runs(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    records = run_mod.runs(_path_under(root, args.runs))
    if args.run_id:
        records = [record for record in records if record.get("run_id") == args.run_id]
        if not records:
            print(f"run not found: {args.run_id}", file=sys.stderr)
            return 1
    if args.agent:
        records = [record for record in records if record.get("agent_id") == args.agent]
    records = records[-args.limit:]
    if args.json or args.run_id:
        print(json.dumps(records[0] if args.run_id else records,
                         ensure_ascii=False, indent=2, default=str))
    else:
        for record in records:
            print(f"{record.get('run_id')}\t{record.get('agent_id')}\t"
                  f"{record.get('skill')}\t{record.get('status', 'running')}\t"
                  f"{record.get('started_at')}\t{_usage_column(record)}")
    return 0


def _usage_column(record: Mapping[str, object]) -> str:
    """§41: model token usage and cost stay visible without opening the JSON.

    An unreadable measurement is rendered as unknown rather than as zero, so a
    missing number can never be mistaken for "this run was free".
    """

    tokens_in = record.get("input_tokens")
    tokens_out = record.get("output_tokens")
    cost = record.get("cost")
    if tokens_in is None and tokens_out is None and cost is None:
        return "tokens=? cost=?"
    return (f"tokens={tokens_in}/{tokens_out} "
            f"cost={cost if cost is not None else '?'}")


def _cmd_artifact(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    log_path = _path_under(root, args.log)
    if args.command == "append":
        try:
            payload = json.loads(args.payload) if args.payload else {}
            provenance = json.loads(args.provenance) if args.provenance else {}
        except json.JSONDecodeError as exc:
            print(f"ERROR: invalid JSON: {exc}", file=sys.stderr)
            return 2
        try:
            record = artifact_mod.append(
                args.type, args.producer, payload,
                provenance=provenance, log_path=log_path,
            )
        except artifact_mod.ArtifactError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 2
        print(record.id)
        return 0
    records = artifact_mod.artifacts(log_path, artifact_type=args.type,
                                     producer=args.producer)
    for record in records[-args.limit:]:
        print(json.dumps(record, ensure_ascii=False, sort_keys=True))
    return 0


def _cmd_status(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    state_path = _path_under(root, args.state)
    state = load_json(state_path, {"version": 1, "jobs": {}})
    specs = _specs(root)
    print(f"agents={len(specs)} jobs={sum(len(spec.jobs) for spec in specs)}")
    print(f"scheduler_state={state_path} last_tick={state.get('last_tick_at', 'never')}")
    print(f"openclaw_delivery_target={'configured' if os.environ.get('PAP_OPENCLAW_DELIVERY_TARGET') else 'unset'}")
    print(f"openclaw_bin={os.environ.get('PAP_OPENCLAW_BIN', 'openclaw')}")
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


def _cmd_dismiss(args: argparse.Namespace) -> int:
    try:
        dismiss_mod.dismiss(
            args.agent, args.topic, args.term.split(","), args.reason,
            dismissed_at=args.date, db_path=args.db,
        )
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 0


def _cmd_dismissed(args: argparse.Namespace) -> int:
    try:
        entries = dismiss_mod.dismissed(args.agent, db_path=args.db)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    for entry in entries:
        dismissed_at = str(entry.get("dismissed_at", ""))
        print(f"- {entry.get('topic', '')} — 匹配词: {', '.join(entry.get('terms', []))} "
              f"— {entry.get('reason', '')} — {dismissed_at[:10]}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pap", description="Personal Agent Platform tooling")
    sub = parser.add_subparsers(dest="command", required=True)

    p_validate = sub.add_parser("validate", help="validate all agents/*/agent.yaml specs")
    p_validate.add_argument("--root", default=".", help="platform repo root (default: cwd)")
    p_validate.add_argument("--json", action="store_true", help="machine-readable output")
    p_validate.set_defaults(func=_cmd_validate)

    p_agents = sub.add_parser("agents", help="list declared agents")
    p_agents.add_argument("--root", default=".")
    p_agents.set_defaults(func=_cmd_agents)

    p_jobs = sub.add_parser("jobs", help="list manifest-declared jobs")
    p_jobs.add_argument("--root", default=".")
    p_jobs.add_argument("--agent")
    p_jobs.set_defaults(func=_cmd_jobs)

    p_invoke = sub.add_parser("invoke", help="invoke one agent skill through OpenClaw")
    p_invoke.add_argument("agent")
    p_invoke.add_argument("skill")
    p_invoke.add_argument("input", nargs="?", default="")
    p_invoke.add_argument("--arg", action="append", default=[], metavar="KEY=VALUE")
    p_invoke.add_argument("--root", default=".")
    p_invoke.add_argument("--runs", type=Path, default=run_mod.DEFAULT_RUN_LOG)
    p_invoke.set_defaults(func=_cmd_invoke)

    p_job = sub.add_parser("job", help="run a manifest-declared job")
    job_sub = p_job.add_subparsers(dest="job_command", required=True)
    p_job_run = job_sub.add_parser("run", help="run one declared job now")
    p_job_run.add_argument("agent")
    p_job_run.add_argument("job", nargs="?")
    p_job_run.add_argument("--arg", action="append", default=[], metavar="KEY=VALUE")
    p_job_run.add_argument("--root", default=".")
    p_job_run.add_argument("--runs", type=Path, default=run_mod.DEFAULT_RUN_LOG)
    p_job_run.set_defaults(func=_cmd_job_run)

    p_tick = sub.add_parser("tick", help="run due manifest jobs once")
    p_tick.add_argument("--root", default=".")
    p_tick.add_argument("--state", type=Path, default=scheduler_mod.DEFAULT_SCHEDULER_STATE)
    p_tick.add_argument("--runs", type=Path, default=run_mod.DEFAULT_RUN_LOG)
    p_tick.add_argument("--delivery-target", help="OpenClaw delivery target (or PAP_OPENCLAW_DELIVERY_TARGET)")
    p_tick.add_argument("--now", help="ISO timestamp override (testing/operations)")
    p_tick.add_argument("--dry-run", action="store_true", help="show due jobs without reserving/running")
    p_tick.set_defaults(func=_cmd_tick)

    p_runs = sub.add_parser("runs", help="inspect append-only run history")
    p_runs.add_argument("run_id", nargs="?")
    p_runs.add_argument("--agent")
    p_runs.add_argument("--limit", type=int, default=20)
    p_runs.add_argument("--json", action="store_true")
    p_runs.add_argument("--root", default=".")
    p_runs.add_argument("--runs", type=Path, default=run_mod.DEFAULT_RUN_LOG)
    p_runs.set_defaults(func=_cmd_runs)

    p_status = sub.add_parser("status", help="show platform scheduler status")
    p_status.add_argument("--root", default=".")
    p_status.add_argument("--state", type=Path, default=scheduler_mod.DEFAULT_SCHEDULER_STATE)
    p_status.set_defaults(func=_cmd_status)

    p_cognition = sub.add_parser("cognition", help="local derived Vault evidence index")
    p_cognition.add_argument("--vault", type=Path)
    p_cognition.add_argument("--db", type=Path)
    cognition_sub = p_cognition.add_subparsers(dest="cognition_command", required=True)
    cognition_sub.add_parser("status")
    p_cognition_index = cognition_sub.add_parser("index")
    p_cognition_index.add_argument("--dry-run", action="store_true")
    p_cognition_index.add_argument("--full", action="store_true")
    p_cognition_evidence = cognition_sub.add_parser("evidence")
    p_cognition_evidence.add_argument("evidence_id")
    p_cognition_evidence.add_argument("--excerpt", type=int, default=1200)
    p_cognition_search = cognition_sub.add_parser("search")
    p_cognition_search.add_argument("query")
    p_cognition_search.add_argument("--limit", type=int, default=10)
    p_cognition_search.add_argument("--source-type")
    p_cognition_search.add_argument("--voice")
    p_cognition_shadow = cognition_sub.add_parser("shadow", help="build a non-production ContextPack")
    p_cognition_shadow.add_argument("kind", choices=("serendipity", "intelligence"))
    p_cognition_shadow.add_argument("--run-id")
    p_cognition.set_defaults(func=_cmd_cognition)

    p_artifact = sub.add_parser("artifact", help="append-only cross-agent artifacts")
    artifact_sub = p_artifact.add_subparsers(dest="command", required=True)
    p_art_append = artifact_sub.add_parser("append", help="append one artifact")
    p_art_append.add_argument("type", help="artifact type, e.g. news.thread.created")
    p_art_append.add_argument("producer", help="producing agent id")
    p_art_append.add_argument("--payload", help="JSON object payload")
    p_art_append.add_argument("--provenance", help="JSON object provenance")
    p_art_append.add_argument("--log", type=Path, default=artifact_mod.DEFAULT_ARTIFACT_LOG)
    p_art_append.add_argument("--root", default=".")
    p_art_append.set_defaults(func=_cmd_artifact)
    p_art_list = artifact_sub.add_parser("list", help="list artifacts (JSON lines)")
    p_art_list.add_argument("--type", help="filter by artifact type")
    p_art_list.add_argument("--producer", help="filter by producing agent")
    p_art_list.add_argument("--limit", type=int, default=50)
    p_art_list.add_argument("--log", type=Path, default=artifact_mod.DEFAULT_ARTIFACT_LOG)
    p_art_list.add_argument("--root", default=".")
    p_art_list.set_defaults(func=_cmd_artifact)

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

    p_dismiss = sub.add_parser("dismiss", help="record a topic the user does not want surfaced")
    p_dismiss.add_argument("--agent", required=True, help="agent name")
    p_dismiss.add_argument("--topic", required=True, help="stable topic slug")
    p_dismiss.add_argument("--term", required=True, help="comma-separated match terms")
    p_dismiss.add_argument("--reason", required=True, help="user's reason for dismissing the topic")
    p_dismiss.add_argument("--date", help="ISO-8601 dismissal timestamp override")
    p_dismiss.add_argument("--db", type=Path, default=dismiss_mod.DEFAULT_DB,
                           help="dismissed-topic state file")
    p_dismiss.set_defaults(func=_cmd_dismiss)

    p_dismissed = sub.add_parser("dismissed", help="list an agent's dismissed topics")
    p_dismissed.add_argument("--agent", required=True, help="agent name")
    p_dismissed.add_argument("--db", type=Path, default=dismiss_mod.DEFAULT_DB,
                             help="dismissed-topic state file")
    p_dismissed.set_defaults(func=_cmd_dismissed)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
