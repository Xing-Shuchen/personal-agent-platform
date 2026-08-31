#!/usr/bin/env python3
"""Install agents/*/ profiles into the local Hermes profile.

Reads each ``agents/*/agent.yaml`` and copies the profile directory plus its
skills into a Hermes profile. Job declarations remain owned by ``pap tick``;
this installer intentionally creates no Hermes cron jobs.

Dry-run by default; pass ``--apply`` to actually write.

Usage:
    python scripts/install_agents.py [--apply] [--root .] [--hermes-profile feishu3]
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


HERMES_HOME = Path(_real_home()) / ".hermes"


def hermes_profile_dir(profile: str) -> Path:
    return HERMES_HOME / "profiles" / profile


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


def plan_profile_copy(spec: AgentSpec, root: Path, profile_dir: Path) -> dict:
    src = root / "agents" / spec.name / "profile"
    dst = profile_dir / "agents" / spec.name / "profile"
    return {"src": str(src), "dst": str(dst), "exists": src.is_dir()}


def plan_skill_copies(spec: AgentSpec, root: Path, profile_dir: Path) -> list[dict]:
    """Hermes loads skills from <profile>/skills/, so each agent skill must be
    installed there by name (not left under the copied profile tree)."""
    src_root = root / "agents" / spec.name / "profile" / "skills"
    plans = []
    if src_root.is_dir():
        for skill_dir in sorted(src_root.iterdir()):
            if (skill_dir / "SKILL.md").is_file():
                plans.append({
                    "name": skill_dir.name,
                    "src": str(skill_dir),
                    "dst": str(profile_dir / "skills" / skill_dir.name),
                })
    return plans


def cmd_list(specs: list[AgentSpec], root: Path, profile: str) -> int:
    profile_dir = hermes_profile_dir(profile)
    print(f"Hermes profile: {profile_dir}")
    for spec in specs:
        print(f"\nagent: {spec.name}  (proactive={spec.proactive_enabled})")
        if not spec.proactive_enabled:
            print("  no platform jobs (proactive disabled)")
        for job in plan_jobs(spec):
            print(f"  platform job {job['name']}: '{job['schedule']}' skill={job['skill']} "
                  f"delivery={job['delivery']} args={json.dumps(job['args'], ensure_ascii=False)}")
        copy = plan_profile_copy(spec, root, profile_dir)
        print(f"  profile copy: {copy['src']} -> {copy['dst']}")
        for sk in plan_skill_copies(spec, root, profile_dir):
            print(f"  skill install: {sk['src']} -> {sk['dst']}")
    return 0


def cmd_apply(specs: list[AgentSpec], root: Path, profile: str, dry_run: bool) -> int:
    profile_dir = hermes_profile_dir(profile)
    if not profile_dir.is_dir():
        print(f"ERROR: Hermes profile dir not found: {profile_dir}", file=sys.stderr)
        return 1

    for spec in specs:
        # 1. Copy profile files (SOUL.md, config.yaml, distribution.yaml, skills/).
        copy = plan_profile_copy(spec, root, profile_dir)
        src, dst = Path(copy["src"]), Path(copy["dst"])
        if copy["exists"]:
            print(f"[{spec.name}] copying profile {src} -> {dst}")
            if not dry_run:
                if dst.exists():
                    shutil.rmtree(dst)
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copytree(src, dst)
        else:
            print(f"[{spec.name}] WARNING: profile dir missing: {src}", file=sys.stderr)

        # 1b. Install agent skills into the Hermes profile skills dir (shared
        # destination -> merge, never wipe).
        for sk in plan_skill_copies(spec, root, profile_dir):
            print(f"[{spec.name}] {'DRY-RUN ' if dry_run else ''}skill install: "
                  f"{sk['name']} -> {sk['dst']}")
            if not dry_run:
                shutil.copytree(sk["src"], sk["dst"], dirs_exist_ok=True)

    if dry_run:
        print("\nDry run only. Re-run with --apply to write changes.")
    print("Scheduling remains platform-owned. Configure one system cron entry for `pap tick`.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Install platform agents into Hermes")
    parser.add_argument("--apply", action="store_true", help="actually write (default: dry run)")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--hermes-profile", default="feishu3")
    parser.add_argument("--list-only", action="store_true", help="just show the plan")
    args = parser.parse_args(argv)

    root = Path(args.root)
    specs = load_platform(root)

    if args.list_only:
        return cmd_list(specs, root, args.hermes_profile)
    return cmd_apply(specs, root, args.hermes_profile, dry_run=not args.apply)


if __name__ == "__main__":
    sys.exit(main())
