from pathlib import Path

from scripts.check_release import check, release_files, scan_files


def test_release_uses_tracked_files_without_office_or_local_openclaw_data():
    files = release_files()
    assert files
    assert not any("agent-office-floor" in path.parts for path in files)
    assert not any("var" in path.parts for path in files)
    assert Path("AGENTS.md") in files
    assert Path("config/agents.example.yaml") in files
    # The office README documents that the archive ships the portal declaration
    # and nothing else under .openclaw/.
    assert Path(".openclaw/portals.json") in files
    assert not any(".openclaw" in path.parts and path != Path(".openclaw/portals.json")
                   for path in files)


def test_privacy_scan_covers_office_sources_too():
    scanned = scan_files()
    assert Path("agent-office-floor/apps/server/src/index.ts") in scanned
    assert not any("node_modules" in path.parts for path in scanned)
    # The tracked manifests must not carry author model routes.
    assert check([Path("agents/world-historian/agent.yaml")]) == []
