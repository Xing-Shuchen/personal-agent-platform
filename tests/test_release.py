from pathlib import Path

from scripts.check_release import release_files


def test_release_uses_tracked_files_without_office_or_local_openclaw_data():
    files = release_files()
    assert files
    assert not any("agent-office-floor" in path.parts for path in files)
    assert not any(".openclaw" in path.parts for path in files)
    assert not any("var" in path.parts for path in files)
    assert Path("AGENTS.md") in files
    assert Path("config/agents.example.yaml") in files
