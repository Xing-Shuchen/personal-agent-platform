#!/usr/bin/env python3
"""Install agents/*/ profiles into the local Hermes profile.

Reads each ``agents/*/agent.yaml``, then for every agent with proactive jobs
creates Hermes cron jobs (schedule + skill carried over from the spec), and
copies the profile directory (SOUL.md, config.yaml, distribution.yaml,
skills/) into the Hermes profile.

Dry-run by default; pass ``--apply`` to actually write.

Usage:
    python scripts/install_agents.py [--apply] [--root .] [--hermes-profile feishu3]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pap.spec import AgentSpec, load_platform  # noqa: E402

SCHEDULE_TO_CRON = {
    "every 30m": "30m",
    "every 1h": "1h",
    "every 2h": "2h",
    "every 4h": "4h",
    "every 6h": "6h",
    "every 12h": "12h",
    "every 24h": "24h",
    "every 1d": "24h",
}

def _real_home() -> str:
    """True user home even when $HOME is redirected (cron, daemons, sandboxes)."""
    import getpass
    import pwd

    try:
        return pwd.getpwnam(getpass.getuser()).pw_dir
    except KeyError:
        return os.path.expanduser("~")


HERMES_HOME = Path(_real_home()) / ".hermes"


def cron_schedule(spec_schedule: str) -> str | None:
    """Pass the spec schedule through verbatim.

    NOTE: the Hermes cron CLI treats a bare '1h' as a ONE-SHOT job
    ('once in 1h', Repeat: 1) while 'every 1h' is recurring (Repeat: ∞).
    Verified live 2026-08-28.
    """
    s = spec_schedule.strip()
    if s.startswith(("every ", "cron ")) or re.match(r"^\d{2}:\d{2}", s):
        return s
    return None


def hermes_profile_dir(profile: str) -> Path:
    return HERMES_HOME / "profiles" / profile


def plan_jobs(spec: AgentSpec) -> list[dict]:
    plan = []
    for job in spec.jobs:
        plan.append({
            "name": job.name,
            "schedule": cron_schedule(job.schedule),
            "spec_schedule": job.schedule,
            "skill": job.skill,
            "attach_to_session": job.attach_to_session,
            "delivery": job.delivery,
            "prompt": (
                f"Run the '{job.skill}' skill exactly as written and follow its "
                f"procedure. Remember the agent SOUL discipline: if no candidate "
                f"passes the shared gate, respond with exactly [SILENT]."
            ),
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
            print("  no cron jobs (proactive disabled)")
            continue
        for job in plan_jobs(spec):
            if job["schedule"] is None:
                print(f"  job {job['name']}: UNSUPPORTED schedule {job['spec_schedule']!r} -> skipped")
            else:
                print(f"  job {job['name']}: cron '{job['schedule']}' (spec: "
                      f"{job['spec_schedule']}) skill={job['skill']} "
                      f"delivery={job['delivery']}")
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

        # 2. Create cron jobs for proactive schedules.
        if not spec.proactive_enabled:
            continue
        for job in plan_jobs(spec):
            if job["schedule"] is None:
                print(f"[{spec.name}] skip job {job['name']}: unsupported schedule "
                      f"{job['spec_schedule']!r}", file=sys.stderr)
                continue
            cmd = [
                "hermes", "cron", "create",
                job["schedule"],
                job["prompt"],
                "--name", job["name"],
                "--skill", job["skill"],
            ]
            if job["delivery"] == "user-home":
                cmd += ["--deliver", "feishu"]
            elif job["delivery"] == "local":
                cmd += ["--deliver", "local"]
            # 'origin' -> omit --deliver (default behavior)
            print(f"[{spec.name}] {'DRY-RUN ' if dry_run else ''}cron create: "
                  f"{job['name']} ({job['schedule']})")
            if not dry_run:
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    print(f"  FAILED: {result.stderr.strip() or result.stdout.strip()}",
                          file=sys.stderr)
                else:
                    job_id = "?"
                    for line in result.stdout.splitlines():
                        if line.startswith("Created job:"):
                            job_id = line.split(":", 1)[1].strip()
                            break
                    print(f"  created job_id={job_id}")

    if dry_run:
        print("\nDry run only. Re-run with --apply to write changes.")
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
