#!/usr/bin/env python3
"""Check and optionally package the shareable worktree without Git history.

Two file sets are maintained:

* ``scan_files()`` — every tracked text file the privacy/policy checks run
  against (including ``agent-office-floor`` sources; only build output and
  dependency caches are dropped).
* ``release_files()`` — the shareable template archive: the scan set minus the
  workspace-only ``agent-office-floor`` app. ``.openclaw/portals.json`` is
  deliberately included (the office README documents this), while any other
  ``.openclaw/`` file stays out.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_PATHS = (
    re.compile(r"/(?:home|Users)/[A-Za-z0-9._-]+"),
    re.compile(r"(?:wxid_[A-Za-z0-9]{8,}|ou_[0-9a-f]{16,})"),
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
)
FORBIDDEN_PARTS = {".git", ".venv", "__pycache__", "var", "dist", "node_modules"}
# Tracked manifests must stay free of provider-specific model routes (AGENTS.md);
# deployments pin job models in the ignored var/config/agents.yaml instead.
MODEL_ROUTE = re.compile(r"^\s*model:\s*(\S.*)$", re.MULTILINE)


def _tracked_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "-z"],
        cwd=ROOT, check=True, capture_output=True,
    )
    files: list[Path] = []
    for raw in result.stdout.split(b"\0"):
        if not raw:
            continue
        path = Path(raw.decode("utf-8"))
        if any(part in FORBIDDEN_PARTS for part in path.parts):
            continue
        source = ROOT / path
        if source.is_file() and not source.is_symlink():
            files.append(path)
    return sorted(set(files))


def scan_files() -> list[Path]:
    """Files the privacy/policy checks cover (all tracked source, office included)."""
    files = []
    for path in _tracked_files():
        if ".openclaw" in path.parts and path != Path(".openclaw/portals.json"):
            continue
        files.append(path)
    return files


def release_files() -> list[Path]:
    """Files that go into the shareable clean-source archive."""
    return [path for path in scan_files() if "agent-office-floor" not in path.parts]


def check(files: list[Path]) -> list[str]:
    problems = []
    for path in files:
        data = (ROOT / path).read_bytes()
        if b"\0" in data:
            continue
        value = data.decode("utf-8", errors="replace")
        for pattern in FORBIDDEN_PATHS:
            for match in pattern.finditer(value):
                line = value.count("\n", 0, match.start()) + 1
                problems.append(
                    f"{path}:{line}: contains a personal path, account ID, or credential pattern")
        if path.match("agents/*/agent.yaml"):
            for match in MODEL_ROUTE.finditer(value):
                route = match.group(1).split("#", 1)[0].strip()
                if route and "/" in route:
                    line = value.count("\n", 0, match.start()) + 1
                    problems.append(
                        f"{path}:{line}: tracked manifest carries a provider-specific "
                        f"model route ({route}); pin it in var/config/agents.yaml instead")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--zip", type=Path, help="write a clean source archive after checks pass")
    args = parser.parse_args()
    problems = check(scan_files())
    for problem in problems:
        print(problem, file=sys.stderr)
    if problems:
        print(f"Release check failed: {len(problems)} finding(s)", file=sys.stderr)
        return 1
    files = release_files()
    print(f"Release check passed: {len(files)} release file(s), "
          f"{len(scan_files())} scanned")
    if args.zip:
        dest = args.zip if args.zip.is_absolute() else ROOT / args.zip
        dest.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(dest, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path in files:
                archive.write(ROOT / path, arcname=Path("personal-agent-platform") / path)
        print(f"Wrote {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
