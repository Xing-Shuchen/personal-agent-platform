#!/usr/bin/env python3
"""Install PAP agent skills into their OpenClaw agent workspaces.

Reads each ``agents/*/agent.yaml`` and merges its skills into that agent's
existing OpenClaw workspace. Workspace profile files remain OpenClaw-owned.
Job declarations remain owned by ``pap tick``; this installer intentionally
creates no OpenClaw automations or cron jobs.

Dry-run by default; pass ``--apply`` to actually write.

Usage:
    python scripts/install_agents.py [--apply] [--root .] [--openclaw-home ~/.openclaw]
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pap.spec import AgentSpec, load_platform  # noqa: E402

def _real_home() -> str:
    """True user home even when $HOME is redirected (cron, daemons, sandboxes)."""
    import getpass
    import pwd

    try:
        return pwd.getpwnam(getpass.getuser()).pw_dir
    except KeyError:
        return os.path.expanduser("~")


def default_openclaw_home() -> Path:
    return Path(_real_home()) / ".openclaw"


def openclaw_workspace_dir(openclaw_home: Path, agent_name: str) -> Path:
    return openclaw_home / f"workspace-{agent_name}"


def plan_jobs(spec: AgentSpec) -> list[dict]:
    """Describe platform-owned jobs; the installer never creates cron jobs."""
    plan = []
    for job in spec.jobs:
        plan.append({
            "name": job.name,
            "schedule": job.schedule,
            "skill": job.skill,
            "args": job.args,
            "attach_to_session": job.attach_to_session,
            "delivery": job.delivery,
        })
    return plan


def plan_skill_copies(spec: AgentSpec, root: Path, workspace_dir: Path) -> list[dict]:
    """Install each PAP skill into its corresponding OpenClaw workspace."""
    src_root = root / "agents" / spec.name / "profile" / "skills"
    plans = []
    if src_root.is_dir():
        for skill_dir in sorted(src_root.iterdir()):
            if (skill_dir / "SKILL.md").is_file():
                plans.append({
                    "name": skill_dir.name,
                    "src": str(skill_dir),
                    "dst": str(workspace_dir / "skills" / skill_dir.name),
                })
    return plans


def cmd_list(specs: list[AgentSpec], root: Path, openclaw_home: Path) -> int:
    print(f"OpenClaw home: {openclaw_home}")
    for spec in specs:
        print(f"\nagent: {spec.name}  (proactive={spec.proactive_enabled})")
        workspace_dir = openclaw_workspace_dir(openclaw_home, spec.name)
        print(f"  OpenClaw workspace: {workspace_dir}")
        if not spec.proactive_enabled:
            print("  no platform jobs (proactive disabled)")
        for job in plan_jobs(spec):
            print(f"  platform job {job['name']}: '{job['schedule']}' skill={job['skill']} "
                  f"delivery={job['delivery']} args={json.dumps(job['args'], ensure_ascii=False)}")
        for sk in plan_skill_copies(spec, root, workspace_dir):
            print(f"  skill install: {sk['src']} -> {sk['dst']}")
    return 0


def cmd_apply(specs: list[AgentSpec], root: Path, openclaw_home: Path, dry_run: bool) -> int:
    workspace_dirs = {
        spec.name: openclaw_workspace_dir(openclaw_home, spec.name) for spec in specs
    }
    for workspace_dir in workspace_dirs.values():
        if not workspace_dir.is_dir():
            print(f"ERROR: OpenClaw workspace dir not found: {workspace_dir}", file=sys.stderr)
            return 1

    for spec in specs:
        workspace_dir = workspace_dirs[spec.name]
        # Merge skills into the agent-specific workspace; do not overwrite
        # OpenClaw-owned workspace profile files.
        for sk in plan_skill_copies(spec, root, workspace_dir):
            print(f"[{spec.name}] {'DRY-RUN ' if dry_run else ''}skill install: "
                  f"{sk['name']} -> {sk['dst']}")
            if not dry_run:
                shutil.copytree(sk["src"], sk["dst"], dirs_exist_ok=True)

    if dry_run:
        print("\nDry run only. Re-run with --apply to write changes.")
    print("Scheduling remains platform-owned. Configure one system cron entry for `pap tick`.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Install platform agent skills into OpenClaw workspaces")
    parser.add_argument("--apply", action="store_true", help="actually write (default: dry run)")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--openclaw-home", default=str(default_openclaw_home()))
    parser.add_argument("--list-only", action="store_true", help="just show the plan")
    args = parser.parse_args(argv)

    root = Path(args.root)
    specs = load_platform(root)

    openclaw_home = Path(args.openclaw_home).expanduser()
    if args.list_only:
        return cmd_list(specs, root, openclaw_home)
    return cmd_apply(specs, root, openclaw_home, dry_run=not args.apply)


if __name__ == "__main__":
    sys.exit(main())
