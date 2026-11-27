"""Contract & golden-fixture test suite for Cadre Tracker (SPEC v0.9 Section 10.2 T1-T6+)."""

from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CADRE_RUNTIME = ROOT / "agents" / "cadre-tracker" / "runtime"
WH_RUNTIME = ROOT / "agents" / "world-historian" / "runtime"


import types


def _load_package_modules():
    pkg_name = "_cadre_tracker_runtime"
    pkg = types.ModuleType(pkg_name)
    pkg.__path__ = [str(CADRE_RUNTIME)]
    sys.modules[pkg_name] = pkg
    loaded = {}
    for mod_name in ("db", "resolver", "collectors", "gate_precheck", "obsidian", "cli"):
        full_name = f"{pkg_name}.{mod_name}"
        spec = importlib.util.spec_from_file_location(full_name, CADRE_RUNTIME / f"{mod_name}.py")
        assert spec is not None and spec.loader is not None
        mod = importlib.util.module_from_spec(spec)
        sys.modules[full_name] = mod
        spec.loader.exec_module(mod)
        loaded[mod_name] = mod
    return loaded


def _load_standalone(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_mods = _load_package_modules()
db_mod = _mods["db"]
resolver_mod = _mods["resolver"]
collectors_mod = _mods["collectors"]
gate_mod = _mods["gate_precheck"]
obsidian_mod = _mods["obsidian"]
cli_mod = _mods["cli"]
lookup_mod = _load_standalone("_wh_cadre_lookup", WH_RUNTIME / "cadre_lookup.py")


@pytest.fixture
def cadre_conn(tmp_path: Path):
    db_path = tmp_path / "cadre.sqlite3"
    conn = db_mod.connect(db_path)
    db_mod.migrate(conn)
    db_mod.seed_org_skeleton(conn)
    yield conn, db_path
    conn.close()


# ---------------------------------------------------------------------------
# T1: 嵌套简历拆解与幂等入库
# ---------------------------------------------------------------------------
def test_t1_nested_cv_split_and_idempotent_ingest(cadre_conn):
    conn, _ = cadre_conn
    bundle = {
        "schema_version": "1.0",
        "source_id": "src_t1_cv_0001",
        "source": {
            "source_type": "official_cv",
            "source_name": "人民网地方领导资料库",
            "credibility_tier": 2,
            "url": "https://ldzl.people.com.cn/t1",
            "title": "测试干部简历",
            "published_at": "2026-01-01T00:00:00Z",
            "raw_content": "2021.02—2023.01 北京市委常委、常务副市长（其间：2022.03—2022.07中央党校中青班学习）",
        },
        "persons": [
            {
                "name": "张测试",
                "gender": "男",
                "birth_ym": "1971-04",
                "native_place": "河北保定",
                "current_rank": "副省部级",
                "status": "active",
                "educations": [
                    {
                        "school_name": "中共中央党校（国家行政学院）",
                        "department": "中青年干部培训一班",
                        "degree": "党校培训",
                        "is_full_time": False,
                        "start_ym": "2022-03",
                        "end_ym": "2022-07",
                    }
                ],
            }
        ],
        "tenures": [
            {
                "person_name": "张测试",
                "person_birth_ym": "1971-04",
                "action": "UPSERT_SPAN",
                "org_canonical_name": "中共北京市委员会",
                "org_short_name": "北京市委",
                "org_kind": "party_local",
                "role_title": "常委",
                "raw_role_text": "北京市委常委、常务副市长",
                "role_tier": "member",
                "rank_at_time": "副省部级",
                "start_ym": "2021-02",
                "end_ym": "2023-01",
                "is_concurrent": 0,
            },
            {
                "person_name": "张测试",
                "person_birth_ym": "1971-04",
                "action": "UPSERT_SPAN",
                "org_canonical_name": "北京市人民政府",
                "org_short_name": "北京市政府",
                "org_kind": "gov_local",
                "role_title": "常务副市长",
                "raw_role_text": "北京市委常委、常务副市长",
                "role_tier": "deputy_chief",
                "rank_at_time": "副省部级",
                "start_ym": "2021-02",
                "end_ym": "2023-01",
                "is_concurrent": 0,
            },
            {
                "person_name": "张测试",
                "person_birth_ym": "1971-04",
                "action": "UPSERT_SPAN",
                "org_canonical_name": "中共中央党校（国家行政学院）",
                "org_short_name": "中央党校",
                "org_kind": "party_school",
                "role_title": "中青年干部培训一班学员",
                "raw_role_text": "中央党校中青班学习",
                "role_tier": "subordinate",
                "start_ym": "2022-03",
                "end_ym": "2022-07",
                "is_concurrent": 1,
            },
        ],
        "claims": [],
    }

    r1 = resolver_mod.ingest_bundle(conn, bundle)
    assert r1["persons_inserted"] == 1
    assert r1["tenures_inserted"] == 3
    assert r1["educations_inserted"] == 1

    # Second ingest must be strictly idempotent (0 new rows, no PK conflict)
    r2 = resolver_mod.ingest_bundle(conn, bundle)
    assert r2["persons_inserted"] == 0
    assert r2["tenures_inserted"] == 0
    assert r2["educations_inserted"] == 0

    rows = conn.execute(
        "SELECT role_title, is_concurrent FROM tenures WHERE person_id = ? ORDER BY start_ym, is_concurrent",
        (r1["touched_person_ids"][0],),
    ).fetchall()
    assert len(rows) == 3
    assert sum(1 for r in rows if r["is_concurrent"] == 0) == 2
    assert sum(1 for r in rows if r["is_concurrent"] == 1) == 1


# ---------------------------------------------------------------------------
# T2: 机构改名跨期穿透
# ---------------------------------------------------------------------------
def test_t2_org_rename_cross_period_overlap_and_succession(cadre_conn):
    conn, _ = cadre_conn
    bundle = {
        "schema_version": "1.0",
        "source_id": "src_t2_rename",
        "source": {
            "source_type": "official_cv",
            "source_name": "北京市政府官网",
            "credibility_tier": 2,
            "url": "https://www.beijing.gov.cn/t2",
            "title": "规划系统履历",
            "published_at": "2026-01-01T00:00:00Z",
            "raw_content": "规划委 -> 规土委 -> 规自委",
        },
        "persons": [
            {"name": "甲干部", "birth_ym": "1968-01", "current_rank": "正厅局级", "status": "active"},
            {"name": "乙干部", "birth_ym": "1965-05", "current_rank": "副省部级", "status": "active"},
            {"name": "丙干部", "birth_ym": "1967-08", "current_rank": "正厅局级", "status": "active"},
        ],
        "tenures": [
            {
                "person_name": "甲干部",
                "person_birth_ym": "1968-01",
                "org_canonical_name": "北京市规划委员会",
                "org_kind": "gov_local",
                "role_title": "副主任",
                "role_tier": "member",
                "start_ym": "2015-01",
                "end_ym": "2017-12",
            },
            {
                "person_name": "乙干部",
                "person_birth_ym": "1965-05",
                "org_canonical_name": "北京市规划和自然资源委员会",
                "org_kind": "gov_local",
                "role_title": "主任",
                "role_tier": "gov_head",
                "start_ym": "2016-07",
                "end_ym": "2019-11",
            },
            {
                "person_name": "丙干部",
                "person_birth_ym": "1967-08",
                "org_canonical_name": "北京市规划委员会",
                "org_kind": "gov_local",
                "role_title": "主任",
                "role_tier": "gov_head",
                "start_ym": "2013-01",
                "end_ym": "2016-07",
            },
        ],
        "claims": [],
    }
    resolver_mod.ingest_bundle(conn, bundle)

    ov = db_mod.query_overlap(conn, "甲干部", "乙干部")
    assert len(ov["work_overlaps"]) == 1
    w = ov["work_overlaps"][0]
    assert w["hop"] == 0
    assert w["overlap_start"] == "2016-07"
    assert w["overlap_end"] == "2017-12"
    assert w["overlap_months"] == 18

    # Query succession via alias "北京市规自委" must traverse org_lineage back to 北京市规划委员会
    suc = db_mod.query_succession(conn, "北京市规自委", "主任")
    names = [item["name"] for item in suc["chain"]]
    assert names == ["丙干部", "乙干部"]
    assert "北京市规划委员会" in suc["equivalent_orgs"]
    assert "北京市规划和自然资源委员会" in suc["equivalent_orgs"]


# ---------------------------------------------------------------------------
# T3: 黄金案例（陈吉宁—夏林茂多维耦合）
# ---------------------------------------------------------------------------
def _seed_golden_chen_xia(conn):
    bundle = {
        "schema_version": "1.0",
        "source_id": "src_t3_golden",
        "source": {
            "source_type": "ccdi_investigation",
            "source_name": "中央纪委国家监委网站",
            "credibility_tier": 1,
            "url": "https://www.ccdi.gov.cn/t3",
            "title": "陈吉宁与夏林茂履历夹具",
            "published_at": "2026-10-22T10:00:00Z",
            "raw_content": "Golden fixture for Chen Jining & Xia Linmao",
        },
        "persons": [
            {
                "name": "陈吉宁",
                "gender": "男",
                "birth_ym": "1964-02",
                "native_place": "吉林梨树",
                "current_rank": "副国级",
                "cc_membership": ["二十届中央委员", "二十届中央政治局委员"],
                "status": "under_investigation",
                "educations": [
                    {
                        "school_name": "清华大学",
                        "department": "土木与环境工程系",
                        "degree": "学士",
                        "major": "环境工程",
                        "is_full_time": True,
                        "start_ym": "1981-09",
                        "end_ym": "1986-07",
                    }
                ],
            },
            {
                "name": "夏林茂",
                "gender": "男",
                "birth_ym": "1970-05",
                "native_place": "江苏建湖",
                "current_rank": "副省部级",
                "cc_membership": ["二十届中央候补委员"],
                "status": "under_investigation",
                "educations": [
                    {
                        "school_name": "清华大学",
                        "department": "水利水电工程系",
                        "degree": "学士",
                        "major": "水工建筑",
                        "is_full_time": True,
                        "start_ym": "1988-09",
                        "end_ym": "1993-07",
                    },
                    {
                        "school_name": "清华大学",
                        "department": "建筑学院",
                        "degree": "博士",
                        "major": "城市规划与设计",
                        "is_full_time": False,
                        "start_ym": "2005-09",
                        "end_ym": "2011-01",
                    },
                ],
            },
            {
                "name": "其他落马官员",
                "gender": "男",
                "birth_ym": "1963-06",
                "current_rank": "副省部级",
                "status": "under_investigation",
                "educations": [
                    {
                        "school_name": "清华大学",
                        "department": "经管学院",
                        "degree": "硕士",
                        "start_ym": "1990-09",
                        "end_ym": "1993-07",
                    }
                ],
            },
            {
                "name": "现役北京同僚",
                "gender": "男",
                "birth_ym": "1969-08",
                "current_rank": "副省部级",
                "status": "active",
            },
        ],
        "tenures": [
            # Chen Jining
            {
                "person_name": "陈吉宁",
                "person_birth_ym": "1964-02",
                "org_canonical_name": "清华大学",
                "org_kind": "university",
                "role_title": "校长",
                "role_tier": "gov_head",
                "rank_at_time": "副省部级",
                "start_ym": "2012-01",
                "end_ym": "2015-01",
            },
            {
                "person_name": "陈吉宁",
                "person_birth_ym": "1964-02",
                "org_canonical_name": "中华人民共和国环境保护部",
                "org_kind": "gov_central",
                "role_title": "部长",
                "role_tier": "gov_head",
                "rank_at_time": "正省部级",
                "start_ym": "2015-02",
                "end_ym": "2017-05",
            },
            {
                "person_name": "陈吉宁",
                "person_birth_ym": "1964-02",
                "org_canonical_name": "北京市人民政府",
                "org_kind": "gov_local",
                "role_title": "市长",
                "role_tier": "gov_head",
                "rank_at_time": "正省部级",
                "start_ym": "2017-05",
                "end_ym": "2022-10",
            },
            {
                "person_name": "陈吉宁",
                "person_birth_ym": "1964-02",
                "org_canonical_name": "中共北京市委员会",
                "org_kind": "party_local",
                "role_title": "副书记",
                "role_tier": "deputy_chief",
                "rank_at_time": "正省部级",
                "start_ym": "2017-05",
                "end_ym": "2022-10",
            },
            {
                "person_name": "陈吉宁",
                "person_birth_ym": "1964-02",
                "org_canonical_name": "中共上海市委员会",
                "org_kind": "party_local",
                "role_title": "书记",
                "role_tier": "chief",
                "rank_at_time": "副国级",
                "start_ym": "2022-10",
                "end_ym": None,
            },
            # Xia Linmao
            {
                "person_name": "夏林茂",
                "person_birth_ym": "1970-05",
                "org_canonical_name": "北京市石景山区人民政府",
                "org_kind": "gov_local",
                "parent_org_canonical_name": "北京市人民政府",
                "role_title": "区长",
                "role_tier": "gov_head",
                "rank_at_time": "正厅局级",
                "start_ym": "2011-02",
                "end_ym": "2017-05",
            },
            {
                "person_name": "夏林茂",
                "person_birth_ym": "1970-05",
                "org_canonical_name": "中共北京市密云区委员会",
                "org_kind": "party_local",
                "parent_org_canonical_name": "中共北京市委员会",
                "role_title": "书记",
                "role_tier": "chief",
                "rank_at_time": "正厅局级",
                "start_ym": "2017-05",
                "end_ym": "2018-12",
            },
            {
                "person_name": "夏林茂",
                "person_birth_ym": "1970-05",
                "org_canonical_name": "中共北京市东城区委员会",
                "org_kind": "party_local",
                "parent_org_canonical_name": "中共北京市委员会",
                "role_title": "书记",
                "role_tier": "chief",
                "rank_at_time": "正厅局级",
                "start_ym": "2018-12",
                "end_ym": "2021-02",
            },
            {
                "person_name": "夏林茂",
                "person_birth_ym": "1970-05",
                "org_canonical_name": "中共北京市委员会",
                "org_kind": "party_local",
                "role_title": "常委",
                "role_tier": "member",
                "rank_at_time": "副省部级",
                "start_ym": "2021-02",
                "end_ym": "2026-10",
            },
            {
                "person_name": "夏林茂",
                "person_birth_ym": "1970-05",
                "org_canonical_name": "北京市人民政府",
                "org_kind": "gov_local",
                "role_title": "常务副市长",
                "role_tier": "deputy_chief",
                "rank_at_time": "副省部级",
                "start_ym": "2023-01",
                "end_ym": "2026-10",
            },
            # Active Beijing colleague
            {
                "person_name": "现役北京同僚",
                "person_birth_ym": "1969-08",
                "org_canonical_name": "北京市人民政府",
                "org_kind": "gov_local",
                "role_title": "副市长",
                "role_tier": "member",
                "rank_at_time": "副省部级",
                "start_ym": "2019-01",
                "end_ym": None,
            },
        ],
        "claims": [],
    }
    return resolver_mod.ingest_bundle(conn, bundle)


def test_t3_golden_chen_xia_multidimensional_coupling(cadre_conn):
    conn, _ = cadre_conn
    _seed_golden_chen_xia(conn)

    ov = db_mod.query_overlap(conn, "陈吉宁", "夏林茂", now_ym="2026-11")
    assert ov["work_overlaps"]
    assert ov["merged_work_spans"] == [["2017-05", "2022-10"]]
    assert ov["total_unique_overlap_months"] == 66
    assert any(e["school"] == "清华大学" for e in ov["edu_links"])

    sw = db_mod.query_shockwave(conn, "陈吉宁", top_k=20, reference_year=2026, now_ym="2026-11")
    fallen = sw["already_fallen_associates"]
    assert fallen, "Expected already_fallen_associates to be non-empty"
    assert fallen[0]["name"] == "夏林茂"
    assert fallen[0]["closeness_index"] > fallen[-1]["closeness_index"]
    assert any(a["name"] == "现役北京同僚" for a in sw["active_watch_list"])


# ---------------------------------------------------------------------------
# T4: 重名官员消歧拦截
# ---------------------------------------------------------------------------
def test_t4_same_name_disambiguation_intercept(cadre_conn):
    conn, _ = cadre_conn
    seed_bundle = {
        "schema_version": "1.0",
        "source_id": "src_t4_seed",
        "source": {
            "source_type": "official_cv",
            "source_name": "新华网",
            "credibility_tier": 1,
            "url": "https://news.cn/t4-seed",
            "title": "两位王勇基线",
            "published_at": "2025-01-01T00:00:00Z",
            "raw_content": "两位同名王勇",
        },
        "persons": [
            {
                "name": "王勇",
                "gender": "男",
                "birth_ym": "1955-12",
                "native_place": "辽宁盖州",
                "current_rank": "副国级",
                "status": "active",
            },
            {
                "name": "王勇",
                "gender": "男",
                "birth_ym": "1957-02",
                "native_place": "山东阳谷",
                "current_rank": "副省部级",
                "status": "expelled",
            },
        ],
        "tenures": [
            {
                "person_name": "王勇",
                "person_birth_ym": "1955-12",
                "org_canonical_name": "中华人民共和国国务院",
                "org_kind": "gov_central",
                "role_title": "国务委员",
                "role_tier": "member",
                "rank_at_time": "副国级",
                "start_ym": "2013-03",
                "end_ym": "2023-03",
            },
            {
                "person_name": "王勇",
                "person_birth_ym": "1957-02",
                "org_canonical_name": "中国人民政治协商会议海南省委员会",
                "org_kind": "cppcc",
                "role_title": "副主席",
                "role_tier": "member",
                "rank_at_time": "副省部级",
                "start_ym": "2016-01",
                "end_ym": "2020-07",
            },
        ],
        "claims": [],
    }
    resolver_mod.ingest_bundle(conn, seed_bundle)
    before_person_count = conn.execute("SELECT COUNT(*) FROM persons WHERE name = '王勇'").fetchone()[0]
    before_tenure_count = conn.execute("SELECT COUNT(*) FROM tenures").fetchone()[0]
    assert before_person_count == 2

    ambiguous_bundle = {
        "schema_version": "1.0",
        "source_id": "src_t4_clue",
        "source": {
            "source_type": "deep_media",
            "source_name": "地方志资料",
            "credibility_tier": 2,
            "url": "https://example.org/t4-clue",
            "title": "早年地方处级线索",
            "published_at": "2026-05-01T00:00:00Z",
            "raw_content": "1995年王勇任某县发改局局长",
        },
        "persons": [],
        "tenures": [
            {
                "person_name": "王勇",
                "org_canonical_name": "某县发展和改革局",
                "org_kind": "gov_local",
                "role_title": "局长",
                "role_tier": "gov_head",
                "rank_at_time": "县处级",
                "start_ym": "1995-03",
                "end_ym": "1997-06",
            }
        ],
        "claims": [],
    }
    res = resolver_mod.ingest_bundle(conn, ambiguous_bundle)
    assert res["needs_review_count"] == 1
    assert res["tenures_inserted"] == 0
    assert conn.execute("SELECT COUNT(*) FROM persons WHERE name = '王勇'").fetchone()[0] == 2
    assert conn.execute("SELECT COUNT(*) FROM tenures").fetchone()[0] == before_tenure_count

    queue = resolver_mod.list_review_queue(conn)
    assert len(queue) == 1
    assert queue[0]["claim_type"] == "disambiguation_conflict"
    assert len(queue[0]["payload"]["candidates"]) == 2

    # Resolve via reject
    dec = resolver_mod.decide_review(conn, queue[0]["claim_id"], "reject")
    assert dec["review_status"] == "rejected"
    assert resolver_mod.list_review_queue(conn) == []


# ---------------------------------------------------------------------------
# T5: 信源权威等级锁保护
# ---------------------------------------------------------------------------
def test_t5_credibility_lock_protection(cadre_conn):
    conn, _ = cadre_conn
    tier1_bundle = {
        "schema_version": "1.0",
        "source_id": "src_t5_tier1",
        "source": {
            "source_type": "ccdi_investigation",
            "source_name": "中央纪委国家监委网站",
            "credibility_tier": 1,
            "url": "https://www.ccdi.gov.cn/t5",
            "title": "李某被查通报",
            "published_at": "2026-10-01T10:00:00Z",
            "raw_content": "某省副省长李某涉嫌严重违纪违法",
        },
        "persons": [
            {
                "name": "李某",
                "birth_ym": "1968-03",
                "native_place": "江苏南京",
                "current_rank": "副省部级",
                "status": "under_investigation",
            }
        ],
        "tenures": [],
        "claims": [
            {
                "claim_type": "investigation",
                "event_date": "2026-10-01",
                "subject_raw_name": "李某",
                "subject_birth_ym": "1968-03",
                "certainty": "FACT",
                "payload": {"in_office_fallen": True},
                "evidence_quote": "某省副省长李某涉嫌严重违纪违法，目前正接受中央纪委国家监委纪律审查和监察调查。",
            }
        ],
    }
    resolver_mod.ingest_bundle(conn, tier1_bundle)

    # Lagging Tier 3 wiki article claims status='active' -> must be blocked by credibility_lock=1
    tier3_bundle = {
        "schema_version": "1.0",
        "source_id": "src_t5_tier3",
        "source": {
            "source_type": "wikipedia_wikitext",
            "source_name": "中文维基百科",
            "credibility_tier": 3,
            "url": "https://zh.wikipedia.org/wiki/t5",
            "title": "滞后维基词条",
            "published_at": "2026-10-02T00:00:00Z",
            "raw_content": "李某现任副省长",
        },
        "persons": [
            {
                "name": "李某",
                "birth_ym": "1968-03",
                "status": "active",
            }
        ],
        "tenures": [],
        "claims": [],
    }
    r3 = resolver_mod.ingest_bundle(conn, tier3_bundle)
    assert any(b["target"] == "persons.status" for b in r3["credibility_lock_blocks"])
    row = conn.execute("SELECT status, credibility_lock FROM persons WHERE name = '李某'").fetchone()
    assert row["status"] == "under_investigation"
    assert row["credibility_lock"] == 1

    # Tier 4 rumor attempts to mutate persons & tenures and mark claim as FACT
    tier4_bundle = {
        "schema_version": "1.0",
        "source_id": "src_t5_tier4",
        "source": {
            "source_type": "manual_note",
            "source_name": "海外自媒体视频转写",
            "credibility_tier": 4,
            "url": "https://example.org/t5-rumor",
            "title": "外围传闻",
            "published_at": "2026-10-03T00:00:00Z",
            "raw_content": "据传李某平安落地",
        },
        "persons": [{"name": "李某", "birth_ym": "1968-03", "status": "active"}],
        "tenures": [],
        "claims": [
            {
                "claim_type": "patronage_speculation",
                "event_date": "2026-10-03",
                "subject_raw_name": "李某",
                "subject_birth_ym": "1968-03",
                "certainty": "FACT",
                "payload": {"rumor": True},
                "evidence_quote": "据传李某并未落马。",
            }
        ],
    }
    r4 = resolver_mod.ingest_bundle(conn, tier4_bundle)
    assert any(b["target"] == "tier4_main_tables" for b in r4["credibility_lock_blocks"])
    assert conn.execute("SELECT status FROM persons WHERE name = '李某'").fetchone()["status"] == "under_investigation"
    cl = conn.execute(
        "SELECT certainty FROM claims_and_clues WHERE source_id = 'src_t5_tier4'"
    ).fetchone()
    assert cl is not None
    assert cl["certainty"] == "SPECULATION"


# ---------------------------------------------------------------------------
# T6: Gate 静默短路与 DOM 撤下告警
# ---------------------------------------------------------------------------
def test_t6_gate_short_circuit_and_dom_removal_alert(cadre_conn):
    conn, _ = cadre_conn
    # Seed a 54-year-old vice governor (born 1972-03, age ~54 in 2026, below 60)
    org_id = resolver_mod.resolve_or_create_org(conn, "江苏省人民政府", org_kind="gov_local", province_name="江苏")
    conn.execute(
        """INSERT INTO persons (person_id, name, birth_ym, current_rank, status)
           VALUES ('p_vg_54', '周副省长', '1972-03', '副省部级', 'active')"""
    )
    conn.execute(
        """INSERT INTO gov_roster_targets (target_id, org_id, page_url, css_selector, enabled)
           VALUES ('jiangsu_gov_leaders', ?, 'https://www.jiangsu.gov.cn/leaders', 'li.leader-item', 1)""",
        (org_id,),
    )
    conn.commit()

    ccdi_html = """
    <html><body>
      <a href="/notice/1.html">某省副省长赵某涉嫌严重违纪违法接受中央纪委国家监委纪律审查和监察调查</a>
    </body></html>
    """
    dom_html_v1 = """
    <html><body><ul>
      <li class="leader-item">许省长 省长</li>
      <li class="leader-item">周副省长 副省长</li>
    </ul></body></html>
    """
    dom_html_v2 = """
    <html><body><ul>
      <li class="leader-item">许省长 省长</li>
    </ul></body></html>
    """

    cfg = {
        "sources": {
            "ccdi": {
                "enabled": True,
                "endpoints": [
                    {
                        "name": "中纪委审查调查",
                        "source_type": "ccdi_investigation",
                        "url": "https://www.ccdi.gov.cn/list",
                    }
                ],
            }
        }
    }

    state = {"dom": dom_html_v1}

    def fake_fetcher(url: str) -> str:
        if "ccdi.gov.cn" in url:
            return ccdi_html
        if "jiangsu.gov.cn" in url:
            return state["dom"]
        return ""

    # Run 1: captures new CCDI notice + establishes DOM baseline
    out1 = gate_mod.run_precheck(
        conn, sources=["ccdi", "dom"], config=cfg, fetcher=fake_fetcher, captured_date="2026-11-25"
    )
    assert out1["gate_open"] is True
    assert out1["priority"] == "urgent"
    assert len(out1["pending_source_ids"]) == 1

    # Run 2: identical CCDI HTML & identical DOM -> must short-circuit gate_open=False
    out2 = gate_mod.run_precheck(
        conn, sources=["ccdi", "dom"], config=cfg, fetcher=fake_fetcher, captured_date="2026-11-26"
    )
    assert out2["gate_open"] is False
    assert out2["reason"] == "no_new_sources"

    # Run 3: 54-year-old vice governor removed from leadership page -> urgent anomaly!
    state["dom"] = dom_html_v2
    out3 = gate_mod.run_precheck(
        conn, sources=["ccdi", "dom"], config=cfg, fetcher=fake_fetcher, captured_date="2026-11-27"
    )
    assert out3["gate_open"] is True
    assert out3["priority"] == "urgent"
    assert any("周副省长" in r for r in out3["trigger_reasons"])

    anomaly_claim = conn.execute(
        "SELECT claim_type, subject_raw_name FROM claims_and_clues WHERE claim_type = 'dom_removal_anomaly'"
    ).fetchone()
    assert anomaly_claim is not None
    assert anomaly_claim["subject_raw_name"] == "周副省长"


# ---------------------------------------------------------------------------
# Extra: FTS5 Search, Obsidian Idempotent Projection, World-Historian Federation, CLI
# ---------------------------------------------------------------------------
def test_fts5_search_and_obsidian_projection_and_federation(cadre_conn, tmp_path: Path):
    conn, db_path = cadre_conn
    _seed_golden_chen_xia(conn)

    # FTS5 Chinese multi-term search
    hits = db_mod.search_cadres(conn, "清华大学 规划", status="under_investigation")
    assert any(h["name"] == "夏林茂" for h in hits)

    # Obsidian projection + manual note preservation
    vault = tmp_path / "vault"
    p1 = obsidian_mod.project_person_note(conn, "陈吉宁", vault_dir=vault)
    assert p1["skipped"] is False
    md_path = Path(p1["path"])
    assert md_path.is_file()
    content1 = md_path.read_text(encoding="utf-8")
    assert "flowchart LR" in content1
    assert "#ef4444" in content1  # Fallen node red highlight

    # Append personal manual note outside anchor and re-project
    manual_note = "\n我的手写研判：持续关注北京城建系统后续动向。\n"
    md_path.write_text(content1 + manual_note, encoding="utf-8")
    obsidian_mod.project_person_note(conn, "陈吉宁", vault_dir=vault)
    content2 = md_path.read_text(encoding="utf-8")
    assert "我的手写研判：持续关注北京城建系统后续动向。" in content2

    brief = obsidian_mod.write_shockwave_brief(conn, "陈吉宁", "陈吉宁被查震荡波", vault_dir=vault, event_date="2026-11-27")
    assert Path(brief["path"]).is_file()

    # World-historian read-only federated lookup
    missing_res = lookup_mod.lookup_cadre_context(["陈吉宁"], db_path=tmp_path / "nonexistent.sqlite3")
    assert missing_res == {"db_available": False, "entities": []}

    fed_res = lookup_mod.lookup_cadre_context(["陈吉宁", "夏林茂"], db_path=db_path, reference_year=2026)
    assert fed_res["db_available"] is True
    assert len(fed_res["entities"]) == 2
    chen_ctx = next(e for e in fed_res["entities"] if e["name"] == "陈吉宁")
    assert chen_ctx["shockwave_context"]["already_fallen"][0]["name"] == "夏林茂"


def test_cli_end_to_end(tmp_path: Path, capsys):
    db_path = tmp_path / "cli_cadre.sqlite3"
    assert cli_mod.main(["--db", str(db_path), "migrate", "--seed"]) == 0
    mig_out = json.loads(capsys.readouterr().out)
    assert mig_out["total"] == 3
    assert mig_out["seed"]["lineage_pairs_added"] >= 80

    bundle_path = tmp_path / "bundle.json"
    bundle_path.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "source_id": "src_cli_1",
                "source": {
                    "source_type": "hrss_appoint",
                    "source_name": "人社部",
                    "credibility_tier": 1,
                    "url": "https://mohrss.gov.cn/1",
                    "title": "任免",
                    "published_at": "2026-01-01T00:00:00Z",
                    "raw_content": "任命测试人员",
                },
                "persons": [
                    {"name": "林测试", "birth_ym": "1972-01", "current_rank": "副省部级", "status": "active"}
                ],
                "tenures": [
                    {
                        "person_name": "林测试",
                        "person_birth_ym": "1972-01",
                        "org_canonical_name": "中华人民共和国生态环境部",
                        "org_kind": "gov_central",
                        "role_title": "副部长",
                        "role_tier": "member",
                        "start_ym": "2024-01",
                        "end_ym": None,
                    }
                ],
                "claims": [],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    assert cli_mod.main(["--db", str(db_path), "ingest-bundle", "--file", str(bundle_path)]) == 0
    ing_out = json.loads(capsys.readouterr().out)
    assert ing_out["persons_inserted"] == 1

    assert cli_mod.main(["--db", str(db_path), "search", "--query", "生态环境 副部长", "--status", "active"]) == 0
    srch_out = json.loads(capsys.readouterr().out)
    assert srch_out["count"] == 1
    assert srch_out["results"][0]["name"] == "林测试"


def test_agent_manifest_validates():
    from pap.spec import load_spec

    spec = load_spec(ROOT / "agents" / "cadre-tracker" / "agent.yaml")
    assert spec.name == "cadre-tracker"
    assert spec.enabled is False
    assert spec.proactive_enabled is True
    assert len(spec.jobs) >= 2
