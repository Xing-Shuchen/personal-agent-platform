#!/usr/bin/env python3
"""Apply or roll back the voice repair only on the exact supported runtime."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=["apply", "rollback", "status"])
    parser.add_argument("--dist", type=Path, required=True,
                        help="Installed OpenClaw dist directory; no default installation is assumed")
    args = parser.parse_args()
    dist = args.dist.resolve()
    manifest = json.loads((HERE / "manifest.json").read_text())
    package = json.loads((dist.parent / "package.json").read_text())
    if package["version"] != manifest["version"]:
        parser.error("OpenClaw version changed; review the new implementation before applying this patch.")
    snapshots = {}
    states = set()
    for name, hashes in manifest["files"].items():
        current = (dist / name).read_bytes()
        digest = sha(current)
        if digest not in hashes.values():
            parser.error(f"{name} has unrelated modifications; nothing was changed.")
        state = "patched" if digest == hashes["patched"] else "original"
        snapshots[name] = current
        states.add(state)
        print(f"{name}: {state}")
    if args.operation == "status":
        return
    wanted = "patched" if args.operation == "apply" else "original"
    if states == {wanted}:
        return
    if len(states) != 1:
        parser.error("Runtime contains a partial patch; restore consistent files before retrying.")
    if not shutil.which("patch"):
        parser.error("GNU patch is required; nothing was changed.")
    with tempfile.TemporaryDirectory(prefix="openclaw-voice-patch-") as temporary:
        stage = Path(temporary)
        (stage / "dist").mkdir()
        for name, data in snapshots.items():
            (stage / "dist" / name).write_bytes(data)
        command = ["patch", "--batch", "--forward", "--fuzz=0", "-p1", "-d", str(stage), "-i", str(HERE / "changes.patch")]
        if args.operation == "rollback":
            command.append("--reverse")
        subprocess.run(command, check=True)
        changes = {}
        for name, hashes in manifest["files"].items():
            data = (stage / "dist" / name).read_bytes()
            if sha(data) != hashes[wanted]:
                parser.error(f"Patched {name} does not match its expected hash; nothing was changed.")
            changes[name] = data
        # Check all inputs and outputs before replacing any runtime module.
        for name, original in snapshots.items():
            if (dist / name).read_bytes() != original:
                parser.error(f"{name} changed during preparation; nothing was changed.")
        for name, data in changes.items():
            target = dist / name
            fd, pending = tempfile.mkstemp(prefix=f".{name}.", dir=dist)
            try:
                with os.fdopen(fd, "wb") as stream:
                    stream.write(data)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.chmod(pending, target.stat().st_mode & 0o777)
                os.replace(pending, target)
            finally:
                Path(pending).unlink(missing_ok=True)
    print(f"Updated {len(changes)} modules. Restart your Gateway to load them.")


if __name__ == "__main__":
    main()
