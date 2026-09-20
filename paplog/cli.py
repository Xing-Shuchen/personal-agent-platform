"""Operator CLI for the local paplog ledger."""
from __future__ import annotations
import argparse, json, os, signal, subprocess, sys, time
from collections import defaultdict
from pathlib import Path
from typing import Any
from . import observe
from .core import Ledger

def _ledger(args: argparse.Namespace) -> Ledger: return Ledger(args.directory)
def _print(rows: list[dict[str, Any]], as_json: bool = False) -> None:
    if as_json: print(json.dumps(rows, ensure_ascii=False, indent=2)); return
    for e in rows: print(f"{e['timestamp']}\t{e['event_name']}\t{e.get('outcome',{}).get('status','')}\t{e.get('execution',{}).get('run_id','')}")
def _query(args: argparse.Namespace) -> int:
    rows = _ledger(args).query(**{x: getattr(args, x, None) for x in ('since','until','event','kind','job','agent','skill','run','trace','outcome','node','subject')})
    _print(rows[-getattr(args, "limit", 100):], args.json)
    return 0
def _tail(args: argparse.Namespace) -> int:
    ledger = _ledger(args)
    filters = {x: getattr(args, x, None) for x in ('since', 'until', 'event', 'kind', 'job', 'agent', 'skill', 'run', 'trace', 'outcome', 'node', 'subject')}
    seen: set[str] = set()
    try:
        while True:
            rows = ledger.query(**filters)
            fresh = [row for row in rows if row.get("event_id") not in seen]
            for row in fresh:
                seen.add(str(row.get("event_id")))
            _print(fresh[-args.limit:] if not args.follow else fresh, args.json)
            if not args.follow:
                return 0
            time.sleep(args.interval)
    except KeyboardInterrupt:
        return 130
def _run(args: argparse.Namespace) -> int:
    rows = _ledger(args).query(run=args.run_id)
    if args.json:
        _print(rows, True); return 0
    nodes: dict[str, dict[str, Any]] = {}
    span_to_key: dict[str, str] = {}
    for index, event in enumerate(rows):
        execution = event.get("execution", {})
        is_scope = event.get("kind") in {"operation", "action"}
        identity = execution.get("action_id") or execution.get("operation_id") if is_scope else event.get("event_id")
        key = str(identity or event.get("event_id"))
        trace = event.get("trace", {})
        item = nodes.setdefault(key, {"name": event["event_name"], "kind": event.get("kind"), "started": None,
                                      "terminal": None, "event": event, "order": index,
                                      "span": trace.get("span_id") if is_scope else None,
                                      "parent_span": trace.get("parent_span_id") if is_scope else trace.get("span_id")})
        if item.get("span"):
            span_to_key[str(item["span"])] = key
        if event.get("phase") == "started": item["started"] = event
        elif event.get("phase") in {"completed", "failed", "abandoned"}: item["terminal"] = event
    print(args.run_id)
    children: dict[str, list[str]] = defaultdict(list)
    roots: list[str] = []
    for key, item in nodes.items():
        parent = span_to_key.get(str(item.get("parent_span"))) if item.get("parent_span") else None
        if parent and parent != key:
            children[parent].append(key)
        else:
            roots.append(key)
    for entries in children.values(): entries.sort(key=lambda child: nodes[child]["order"])
    roots.sort(key=lambda root: nodes[root]["order"])
    def render(key: str, prefix: str = "", last: bool = True) -> None:
        item = nodes[key]
        event = item["terminal"] or item["started"] or item["event"]
        terminal = item["terminal"] or {}
        outcome = terminal.get("outcome", {}).get("status", "running" if item["started"] else "event")
        duration = terminal.get("duration_ms")
        suffix = f" {duration:.1f}ms" if isinstance(duration, (int, float)) else ""
        print(f"{prefix}{'└──' if last else '├──'} {item['name']} [{outcome}]{suffix}")
        descendant_prefix = prefix + ("    " if last else "│   ")
        for position, child in enumerate(children.get(key, [])):
            render(child, descendant_prefix, position == len(children[key]) - 1)
    for position, root in enumerate(roots):
        render(root, "", position == len(roots) - 1)
    model_events = [event for event in rows if event["event_name"] == "pap.model.call"]
    if model_events:
        attrs = [event.get("attributes", {}) for event in model_events]
        input_values = [item.get("input_tokens") for item in attrs if isinstance(item.get("input_tokens"), (int, float))]
        output_values = [item.get("output_tokens") for item in attrs if isinstance(item.get("output_tokens"), (int, float))]
        cost_values = [item.get("cost.amount") for item in attrs if isinstance(item.get("cost.amount"), (int, float))]
        currencies = {str(item.get("cost.currency")) for item in attrs if item.get("cost.currency")}
        input_total = sum(input_values) if input_values else "?"
        output_total = sum(output_values) if output_values else "?"
        cost_total = sum(cost_values) if cost_values else "?"
        currency = next(iter(currencies)) if len(currencies) == 1 else ("mixed" if currencies else "")
        print(f"tokens: {input_total} input / {output_total} output; cost: {cost_total} {currency}".rstrip())
    return 0
def _failures(args: argparse.Namespace) -> int:
    filters = {name: getattr(args, name, None) for name in ("since", "until", "event", "kind", "job", "agent", "skill", "run", "trace", "outcome", "node", "subject")}
    rows = [x for x in _ledger(args).query(**filters) if x.get("outcome", {}).get("status") in {"error", "failed", "abandoned"}]
    _print(rows[-args.limit:], args.json)
    return 0
def _artifacts(args: argparse.Namespace) -> int:
    filters = {name: getattr(args, name, None) for name in ('since', 'until', 'run', 'trace', 'job', 'agent', 'skill', 'outcome', 'node', 'subject')}
    rows = _ledger(args).query(**filters)
    if args.event:
        rows = [row for row in rows if row["event_name"].startswith(args.event.rstrip("*"))]
    else:
        rows = [row for row in rows if ".artifact." in row["event_name"] or ".context_pack." in row["event_name"] or ".event_revision." in row["event_name"]]
    _print(rows[-args.limit:], args.json)
    return 0
def _lineage(args: argparse.Namespace) -> int:
    links = _ledger(args).lineage(args.identifier, depth=args.depth)
    if args.json:
        print(json.dumps(links, ensure_ascii=False, indent=2)); return 0
    print(args.identifier)
    if not links:
        print("└── (no recorded provenance links)")
    for link in links:
        prefix = "  " * (link.get("depth", 1) - 1)
        if args.depth > 1:
            print(f"{prefix}├── {link['source_id']} → {link['type']} → {link['target_type']}:{link['target_id']}")
        elif link["source_id"] == args.identifier:
            print(f"{prefix}├── {link['type']} → {link['target_type']}:{link['target_id']}")
        else:
            print(f"{prefix}├── {link['source_id']} → {link['type']} → {args.identifier}")
    return 0
def _reconcile(args: argparse.Namespace) -> int: a,b=_ledger(args).reconcile(); print(f"imported={a} quarantined={b}"); return 1 if b else 0
def _rebuild(args: argparse.Namespace) -> int: print(f"rebuilt={_ledger(args).rebuild_index()}"); return 0
def _doctor(args: argparse.Namespace) -> int:
    ledger = _ledger(args)
    try:
        with ledger._connect() as con:
            event_count = con.execute("SELECT count(*) FROM events").fetchone()[0]
        sqlite_status = "ok"
    except Exception as exc:
        event_count, sqlite_status = None, f"error:{type(exc).__name__}"
    spool_count = len(list(ledger.spool.glob("*.json"))) if ledger.spool.exists() else 0
    print(json.dumps({'directory':str(ledger.directory),'sqlite':sqlite_status,'event_count':event_count,
                      'abandoned':ledger.abandon_stale(args.older_than) if sqlite_status == 'ok' else None,
                      'spool':str(ledger.spool),'spool_records':spool_count},ensure_ascii=False))
    return 0 if sqlite_status == 'ok' else 1
def _cost(args: argparse.Namespace) -> int:
    groups=defaultdict(lambda:{'calls':0,'input_tokens':0,'output_tokens':0,'cost':0.0,'reported_cost':0,'estimated_cost':0,'unknown_cost':0})
    for e in _ledger(args).query(since=args.since):
        if e['event_name'] != 'pap.model.call': continue
        a=e.get('attributes',{})
        dimensions = {
            'job': e.get('job', {}).get('id'), 'agent': e.get('agent', {}).get('id'),
            'skill': e.get('skill', {}).get('id'), 'provider': a.get('provider'),
            'model': a.get('returned_model') or a.get('requested_model'),
            'routing_profile': a.get('routing_profile'), 'credential_profile': a.get('credential_profile'),
            'workload_class': a.get('workload_class'),
            'routing-profile': a.get('routing_profile'), 'credential-profile': a.get('credential_profile'),
            'workload': a.get('workload_class'),
        }
        key=str(dimensions.get(args.group_by, a.get(args.group_by)) or 'unknown'); g=groups[key]; g['calls']+=1; g['input_tokens']+=int(a.get('input_tokens') or 0);g['output_tokens']+=int(a.get('output_tokens') or 0)
        if isinstance(a.get('cost.amount'),(int,float)):
            g['cost']+=a['cost.amount']
            source = a.get('cost.source')
            if source == 'estimated': g['estimated_cost'] += 1
            elif source == 'provider-reported': g['reported_cost'] += 1
            else: g['reported_cost'] += 1
        else:g['unknown_cost']+=1
    print(json.dumps(groups,ensure_ascii=False,indent=2)); return 0
def _models(args: argparse.Namespace) -> int:
    groups: dict[str, dict[str, Any]] = {}
    filters = {name: getattr(args, name, None) for name in ("since", "until", "job", "agent", "skill", "run", "trace")}
    for event in _ledger(args).query(**filters):
        if event["event_name"] != "pap.model.call":
            continue
        attrs = event.get("attributes", {})
        provider = attrs.get("provider") or "unknown"
        model = attrs.get("returned_model") or attrs.get("requested_model") or "unknown"
        key = f"{provider}/{model}"
        row = groups.setdefault(key, {"provider": provider, "model": model, "routing_profiles": set(),
                                      "credential_profiles": set(), "workload_classes": set(), "calls": 0,
                                      "input_tokens": 0, "output_tokens": 0, "cost": 0.0,
                                      "unknown_cost": 0, "reported_cost": 0, "estimated_cost": 0,
                                      "fallback_calls": 0, "retries": 0,
                                      "latency_ms": 0.0, "errors": 0})
        row["calls"] += 1
        row["input_tokens"] += int(attrs.get("input_tokens") or 0)
        row["output_tokens"] += int(attrs.get("output_tokens") or 0)
        row["fallback_calls"] += int(attrs.get("fallback_count") or 0)
        row["retries"] += int(attrs.get("retry_count") or 0)
        row["latency_ms"] += float(attrs.get("latency_ms") or event.get("duration_ms") or 0)
        if (event.get("outcome") or {}).get("status") in {"error", "failed"}: row["errors"] += 1
        for field, value in (("routing_profiles", attrs.get("routing_profile")), ("credential_profiles", attrs.get("credential_profile")), ("workload_classes", attrs.get("workload_class"))):
            if value: row[field].add(str(value))
        if isinstance(attrs.get("cost.amount"), (int, float)):
            row["cost"] += attrs["cost.amount"]
            if attrs.get("cost.source") == "estimated": row["estimated_cost"] += 1
            elif attrs.get("cost.source") == "provider-reported": row["reported_cost"] += 1
        else:
            row["unknown_cost"] += 1
    rows = []
    for key in sorted(groups):
        row = groups[key]
        for field in ("routing_profiles", "credential_profiles", "workload_classes"):
            row[field] = sorted(row[field])
            if not row[field]:
                row.pop(field)
            elif len(row[field]) == 1:
                row[field[:-1]] = row[field][0]
        if not row["retries"]:
            row.pop("retries")
        if not row["latency_ms"]:
            row.pop("latency_ms")
        if not row["errors"]:
            row.pop("errors")
        if not row["reported_cost"]:
            row.pop("reported_cost")
        if not row["estimated_cost"]:
            row.pop("estimated_cost")
        rows.append(row)
    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
    else:
        for row in rows:
            print(f"{row['provider']}/{row['model']}\tcalls={row['calls']}\tinput={row['input_tokens']}\toutput={row['output_tokens']}\tcost={row['cost']}\tunknown_cost={row['unknown_cost']}\tfallbacks={row['fallback_calls']}\tretries={row.get('retries', 0)}\terrors={row.get('errors', 0)}")
    return 0
def _scheduler(args: argparse.Namespace) -> int:
    print(json.dumps(_ledger(args).scheduler_health(), ensure_ascii=False, indent=2)); return 0
def _jobs(args: argparse.Namespace) -> int:
    """Summarize scheduler and run lifecycle by the canonical job identity."""
    filters = {name: getattr(args, name, None) for name in ("since", "until", "job", "agent", "skill", "outcome", "node")}
    summaries: dict[str, dict[str, Any]] = {}
    for event in _ledger(args).query(**filters):
        job = event.get("job", {}).get("id")
        if not isinstance(job, str) or not job:
            continue
        row = summaries.setdefault(job, {"job_id": job, "due": 0, "dispatched": 0, "started": 0,
                                         "completed": 0, "failed": 0, "abandoned": 0,
                                         "last_scheduled_for": None, "last_dispatched_at": None,
                                         "last_started_at": None, "last_completed_at": None,
                                         "last_outcome": None})
        name = event.get("event_name")
        attrs = event.get("attributes", {})
        if name == "pap.schedule.due":
            row["due"] += 1; row["last_scheduled_for"] = attrs.get("scheduled_for")
        elif name == "pap.schedule.dispatched":
            row["dispatched"] += 1; row["last_dispatched_at"] = attrs.get("dispatched_at")
        elif name == "pap.run.started":
            row["started"] += 1; row["last_started_at"] = attrs.get("started_at") or event.get("timestamp")
        elif name == "pap.run.completed":
            row["completed"] += 1; row["last_completed_at"] = event.get("timestamp"); row["last_outcome"] = event.get("outcome", {}).get("status")
        elif name == "pap.run.failed":
            row["failed"] += 1; row["last_completed_at"] = event.get("timestamp"); row["last_outcome"] = event.get("outcome", {}).get("status")
        elif name == "pap.operation.abandoned":
            row["abandoned"] += 1; row["last_completed_at"] = event.get("timestamp"); row["last_outcome"] = "abandoned"
    rows = [summaries[key] for key in sorted(summaries)]
    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2)); return 0
    for row in rows:
        print(f"{row['job_id']}\tdue={row['due']}\tdispatched={row['dispatched']}\tstarted={row['started']}\tcompleted={row['completed']}\tfailed={row['failed']}\tabandoned={row['abandoned']}\tlast={row['last_outcome'] or '-'}")
    return 0
def _exec(args: argparse.Namespace) -> int:
    env=os.environ.copy(); ledger = observe.configure(args.directory)
    class _ExecFailure(Exception):
        def __init__(self, code: int): self.code = code
    try:
        with observe.operation('pap.exec', job={'id':args.job} if args.job else {}, agent={'id':args.agent} if args.agent else {}, skill={'id':args.skill} if args.skill else {}, runtime={'backend':'direct','mode':'oneshot'}, attributes={'service':args.service or 'pap'}):
            ctx=observe.current(); execution=ctx['execution']; trace=ctx['trace']; env.update({'PAP_OBSERVABILITY_DIR':str(ledger.directory),'PAP_RUN_ID':execution['run_id'],'PAP_PARENT_OPERATION_ID':execution['operation_id'],'PAP_AGENT':args.agent or '','PAP_SKILL':args.skill or '','PAP_JOB_ID':args.job or '','PAP_NODE_ID':execution.get('node_id',''),'TRACEPARENT':f"00-{trace['trace_id']}-{trace['span_id']}-01"})
            with observe.action('pap.process.exec', effect='execute', scope='local',
                                subject={'type': 'process', 'id': args.child_command[0] if args.child_command else ''},
                                attributes={'program': args.child_command[0] if args.child_command else None,
                                            'argv_count': len(args.child_command)}):
                try:
                    completed=subprocess.run(args.child_command,env=env)
                except KeyboardInterrupt:
                    raise _ExecFailure(128 + signal.SIGINT)
                if completed.returncode:
                    raise _ExecFailure(completed.returncode)
    except _ExecFailure as exc:
        return exc.code
    return 0
def build_parser() -> argparse.ArgumentParser:
 p=argparse.ArgumentParser(prog='paplog');p.add_argument('--directory');sub=p.add_subparsers(dest='command',required=True)
 q=sub.add_parser('query');
 for name in ('since','until','event','kind','job','agent','skill','run','trace','outcome','node','subject'):q.add_argument('--'+name)
 q.add_argument('--limit',type=int,default=100);q.add_argument('--json',action='store_true');q.set_defaults(func=_query)
 defaults = {'actions': {'kind': 'action'}, 'runs': {'event': 'pap.run.*'}}
 for name,func in [('tail',_tail),('actions',_query),('artifacts',_artifacts),('models',_models),('jobs',_jobs),('runs',_query)]:
  x=sub.add_parser(name);x.add_argument('--limit',type=int,default=100);x.add_argument('--json',action='store_true');x.add_argument('--event');x.add_argument('--run');x.add_argument('--trace');x.add_argument('--since');x.add_argument('--until');x.add_argument('--kind');x.add_argument('--job');x.add_argument('--agent');x.add_argument('--skill');x.add_argument('--outcome');x.add_argument('--node');x.add_argument('--subject');x.set_defaults(func=func, **defaults.get(name, {}))
  if name == 'tail': x.add_argument('--follow', action='store_true'); x.add_argument('--interval', type=float, default=1.0)
 t=sub.add_parser('trace');t.add_argument('trace_id');t.add_argument('--json',action='store_true');t.set_defaults(func=lambda a: _print(_ledger(a).query(trace=a.trace_id), a.json) or 0)
 r=sub.add_parser('run');r.add_argument('run_id');r.add_argument('--json',action='store_true');r.set_defaults(func=_run)
 l=sub.add_parser('lineage');l.add_argument('identifier');l.add_argument('--depth',type=int,default=3);l.add_argument('--json',action='store_true');l.set_defaults(func=_lineage)
 f=sub.add_parser('failures');f.add_argument('--limit',type=int,default=100);f.add_argument('--json',action='store_true');
 for name in ('since','until','event','kind','job','agent','skill','run','trace','outcome','node','subject'): f.add_argument('--'+name)
 f.set_defaults(func=_failures)
 c=sub.add_parser('cost');c.add_argument('--since',default='7d');c.add_argument('--group-by',default='provider');c.set_defaults(func=_cost)
 s=sub.add_parser('scheduler');s.set_defaults(func=_scheduler)
 sub.add_parser('reconcile').set_defaults(func=_reconcile);sub.add_parser('rebuild-index').set_defaults(func=_rebuild)
 d=sub.add_parser('doctor');d.add_argument('--older-than',type=int,default=3600);d.set_defaults(func=_doctor)
 e=sub.add_parser('exec');e.add_argument('--service');e.add_argument('--job');e.add_argument('--agent');e.add_argument('--skill');e.add_argument('child_command',nargs=argparse.REMAINDER);e.set_defaults(func=_exec)
 return p
def main(argv:list[str]|None=None)->int:
 args=build_parser().parse_args(argv)
 if args.command=='exec' and args.child_command and args.child_command[0]=='--': args.child_command=args.child_command[1:]
 return args.func(args)
if __name__=='__main__':raise SystemExit(main())
