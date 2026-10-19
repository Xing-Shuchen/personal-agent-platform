"""Compiler briefing archiving must keep a complete, deduplicated vault index."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

SCRIPT = (Path(__file__).resolve().parents[1] / "agents/compiler-news/profile/skills/"
          "compiler-hpc-brief/scripts/archive.py")
spec = importlib.util.spec_from_file_location("compiler_brief_archive", SCRIPT)
archive = importlib.util.module_from_spec(spec)
spec.loader.exec_module(archive)


def body(day: str, topic: str = "Compiler update") -> str:
    return (f"{archive.TITLE}｜{day}\n\n"
            f"- **{topic}**：New lowering rule. 来源：[Release](https://example.test/release)\n\n"
            f"{archive.FOOTER}\n")


def test_historical_index_is_complete_idempotent_and_preserves_notes(tmp_path, monkeypatch):
    monkeypatch.setattr(archive, "_today", lambda: "2026-01-03")
    folder = tmp_path / archive.ARCHIVE_DIR
    folder.mkdir(parents=True)
    histories = {"2026-01-01": "old text one", "2026-01-02": "old text two"}
    for day, text in histories.items():
        (folder / f"AI编译器简报-{day}.md").write_text(text)
    (folder / "AI编译器简报-2026-02-30.md").write_text("invalid filename date")
    result = archive.update_index(tmp_path)
    assert result["brief_count"] == 2 and result["index_updated"]
    index = Path(result["index"])
    initial = index.read_text()
    assert initial.index("[[AI编译器简报-2026-01-01|") < initial.index("[[AI编译器简报-2026-01-02|")
    index.write_text(initial + "\n## 我的备注\nKeep this.\n")
    before = index.stat().st_mtime_ns
    assert not archive.update_index(tmp_path)["index_updated"]
    assert index.stat().st_mtime_ns == before
    monkeypatch.setattr(archive, "_today", lambda: "2026-01-04")
    added = archive.archive_brief(tmp_path, "2026-01-03", body("2026-01-03"), "example-model")
    assert added["brief_count"] == 3 and added["index_updated"]
    updated = index.read_text()
    assert "created: 2026-01-03" in updated and "updated: 2026-01-04" in updated
    assert updated.endswith("## 我的备注\nKeep this.\n")
    assert updated.count("[[AI编译器简报-2026-01-03|") == 1
    for day, text in histories.items():
        assert (folder / f"AI编译器简报-{day}.md").read_text() == text


def test_archive_updates_same_day_without_duplicate_directory_entry(tmp_path, monkeypatch):
    monkeypatch.setattr(archive, "_today", lambda: "2026-01-03")
    result = archive.archive_brief(tmp_path, "2026-01-03", body("2026-01-03"), "example-model")
    note, index = Path(result["brief"]), Path(result["index"])
    rendered = note.read_text()
    assert f"# {archive.TITLE}｜2026-01-03" in rendered
    assert body("2026-01-03").splitlines()[2] in rendered
    assert archive.FOOTER not in rendered and "model=example-model" in rendered
    before = (note.stat().st_mtime_ns, index.stat().st_mtime_ns)
    monkeypatch.setattr(archive, "_today", lambda: "2026-01-04")
    same = archive.archive_brief(tmp_path, "2026-01-03", body("2026-01-03"), "example-model")
    assert not same["brief_updated"] and not same["index_updated"]
    assert before == (note.stat().st_mtime_ns, index.stat().st_mtime_ns)
    changed = archive.archive_brief(tmp_path, "2026-01-03", body("2026-01-03", "Corrected update"), "example-model")
    assert changed["brief_updated"] and not changed["index_updated"]
    assert "Corrected update" in note.read_text() and "archived: 2026-01-03" in note.read_text()
    assert index.read_text().count("[[AI编译器简报-2026-01-03|") == 1


def test_invalid_index_blocks_archive_without_overwriting_a_brief(tmp_path):
    folder = tmp_path / archive.ARCHIVE_DIR
    folder.mkdir(parents=True)
    note = folder / "AI编译器简报-2026-01-03.md"
    note.write_text("Existing briefing")
    index = folder / archive.INDEX_NAME
    index.write_text("Manual notes\n" + archive.START)
    with pytest.raises(ValueError, match="markers"):
        archive.archive_brief(tmp_path, "2026-01-03", body("2026-01-03"), "example-model")
    assert note.read_text() == "Existing briefing"
    assert index.read_text() == "Manual notes\n" + archive.START


def test_unmanaged_index_is_preserved_and_custom_directory_is_supported(tmp_path):
    folder = tmp_path / "News"
    folder.mkdir()
    index = folder / archive.INDEX_NAME
    index.write_text("# My catalog\n\nKeep my introduction.\n")
    result = archive.archive_brief(tmp_path, "2026-01-01", body("2026-01-01"), "example-model", archive_dir=Path("News"))
    assert result["brief_count"] == 1 and index.read_text().startswith("# My catalog\n\nKeep my introduction.")
    assert not (tmp_path / archive.ARCHIVE_DIR).exists()
    with pytest.raises(ValueError, match="relative"):
        archive.update_index(tmp_path, archive_dir=Path("../elsewhere"))


@pytest.mark.parametrize("day,text", [
    ("2026-01-01", body("2026-01-02")),
    ("2026-02-30", body("2026-02-30")),
    ("../elsewhere", body("2026-01-01")),
    ("2026-01-01", f"{archive.TITLE}｜2026-01-01\n\n{archive.FOOTER}"),
])
def test_invalid_input_creates_no_archive(tmp_path, day, text):
    with pytest.raises(ValueError):
        archive.archive_brief(tmp_path, day, text, "example-model")
    assert not (tmp_path / archive.ARCHIVE_DIR).exists()


def test_installed_script_concurrent_archives_keep_both_entries(tmp_path):
    installed = tmp_path / "installed-skill/scripts/archive.py"
    installed.parent.mkdir(parents=True)
    shutil.copy2(SCRIPT, installed)
    vault = tmp_path / "vault"
    vault.mkdir()
    env = {**os.environ, "PAP_VAULT": str(vault)}
    jobs = []
    for day in ("2026-01-01", "2026-01-02"):
        source = tmp_path / f"{day}.txt"
        source.write_text(body(day))
        jobs.append(subprocess.Popen(
            [sys.executable, str(installed), "archive", "--date", day,
             "--body-file", str(source), "--model", "example-model"],
            env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True))
    for job in jobs:
        stdout, stderr = job.communicate(timeout=10)
        assert job.returncode == 0, stderr
        assert Path(json.loads(stdout)["brief"]).is_file()
    folder = vault / archive.ARCHIVE_DIR
    index = (folder / archive.INDEX_NAME).read_text()
    for day in ("2026-01-01", "2026-01-02"):
        assert index.count(f"[[AI编译器简报-{day}|") == 1
    assert len(list(folder.iterdir())) == 3  # no lock or temporary files in vault


def test_cli_requires_explicit_vault_even_when_environment_is_empty(tmp_path):
    result = subprocess.run([sys.executable, str(SCRIPT), "index"], cwd=tmp_path,
                            env={**os.environ, "PAP_VAULT": ""}, capture_output=True, text=True)
    assert result.returncode != 0 and "set PAP_VAULT" in result.stderr
    assert not list(tmp_path.iterdir())
