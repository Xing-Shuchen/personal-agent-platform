"""Tests for per-agent dismissed-topic state and CLI projections."""

from pap.cli import main
from pap.dismiss import dismissed


def test_write_read_round_trip_and_date_db_overrides(tmp_path, capsys):
    db = tmp_path / "dismissed.json"
    assert main([
        "dismiss", "--agent", "intelligence", "--topic", "zhipu-zcode",
        "--term", "zcode,zhipu-zcode,智谱 zcode", "--reason", "不关心",
        "--date", "2026-09-22T10:30:00+08:00", "--db", str(db),
    ]) == 0
    assert dismissed("intelligence", db_path=db) == [{
        "topic": "zhipu-zcode", "terms": ["zcode", "zhipu-zcode", "智谱 zcode"],
        "reason": "不关心", "dismissed_at": "2026-09-22T10:30:00+08:00",
    }]
    assert main(["dismissed", "--agent", "intelligence", "--db", str(db)]) == 0
    assert capsys.readouterr().out == "- zhipu-zcode — 匹配词: zcode, zhipu-zcode, 智谱 zcode — 不关心 — 2026-09-22\n"


def test_redismiss_is_idempotent_and_projection_is_sorted(tmp_path, capsys):
    db = tmp_path / "dismissed.json"
    base = ["--agent", "intelligence", "--db", str(db)]
    assert main(["dismiss", *base, "--topic", "zeta", "--term", "z", "--reason", "old", "--date", "2026-09-20"]) == 0
    assert main(["dismiss", *base, "--topic", "zeta", "--term", "new", "--reason", "new reason", "--date", "2026-09-21"]) == 0
    assert main(["dismiss", *base, "--topic", "alpha", "--term", "a", "--reason", "first", "--date", "2026-09-19"]) == 0
    assert main(["dismissed", *base]) == 0
    assert capsys.readouterr().out.splitlines() == [
        "- alpha — 匹配词: a — first — 2026-09-19",
        "- zeta — 匹配词: new — new reason — 2026-09-21",
    ]
    assert len(dismissed("intelligence", db_path=db)) == 2


def test_missing_file_has_empty_projection(tmp_path, capsys):
    assert main(["dismissed", "--agent", "intelligence", "--db", str(tmp_path / "absent.json")]) == 0
    assert capsys.readouterr().out == ""
