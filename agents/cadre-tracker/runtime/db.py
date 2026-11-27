"""SQLite database connector, migrations, Batch 0 seeding, and Recursive CTE graph engine."""

from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

RUNTIME_DIR = Path(__file__).resolve().parent
AGENT_DIR = RUNTIME_DIR.parent
REPO_ROOT = Path(os.environ.get("PAP_ROOT", str(AGENT_DIR.parents[1])))
MIGRATIONS_DIR = RUNTIME_DIR / "migrations"
REFORM_LINEAGE_MD = AGENT_DIR / "profile" / "references" / "org-reform-lineage.md"

ROLE_TIER_WEIGHTS: dict[str, float] = {
    "chief": 4.0,
    "gov_head": 3.5,
    "deputy_chief": 3.0,
    "member": 2.0,
    "subordinate": 1.0,
}

RANK_ORDER: dict[str, int] = {
    "正国级": 6,
    "副国级": 5,
    "正省部级": 4,
    "副省部级": 3,
    "正厅局级": 2,
    "副厅局级": 1,
    "县处级": 0,
    "其他": 0,
}

PROVINCES_31: tuple[tuple[str, str, str], ...] = (
    ("北京", "北京市", "110000"),
    ("天津", "天津市", "120000"),
    ("河北", "河北省", "130000"),
    ("山西", "山西省", "140000"),
    ("内蒙古", "内蒙古自治区", "150000"),
    ("辽宁", "辽宁省", "210000"),
    ("吉林", "吉林省", "220000"),
    ("黑龙江", "黑龙江省", "230000"),
    ("上海", "上海市", "310000"),
    ("江苏", "江苏省", "320000"),
    ("浙江", "浙江省", "330000"),
    ("安徽", "安徽省", "340000"),
    ("福建", "福建省", "350000"),
    ("江西", "江西省", "360000"),
    ("山东", "山东省", "370000"),
    ("河南", "河南省", "410000"),
    ("湖北", "湖北省", "420000"),
    ("湖南", "湖南省", "430000"),
    ("广东", "广东省", "440000"),
    ("广西", "广西壮族自治区", "450000"),
    ("海南", "海南省", "460000"),
    ("重庆", "重庆市", "500000"),
    ("四川", "四川省", "510000"),
    ("贵州", "贵州省", "520000"),
    ("云南", "云南省", "530000"),
    ("西藏", "西藏自治区", "540000"),
    ("陕西", "陕西省", "610000"),
    ("甘肃", "甘肃省", "620000"),
    ("青海", "青海省", "630000"),
    ("宁夏", "宁夏回族自治区", "640000"),
    ("新疆", "新疆维吾尔自治区", "650000"),
)

COMMON_ORG_ALIASES: tuple[tuple[str, str], ...] = (
    ("北京市规自委", "北京市规划和自然资源委员会"),
    ("市规自委", "北京市规划和自然资源委员会"),
    ("北京市规划委", "北京市规划委员会"),
    ("市规划委", "北京市规划委员会"),
    ("北京市规土委", "北京市规划和国土资源管理委员会"),
    ("北京东城区委", "中共北京市东城区委员会"),
    ("北京市东城区委", "中共北京市东城区委员会"),
    ("北京密云区委", "中共北京市密云区委员会"),
    ("北京市密云区委", "中共北京市密云区委员会"),
    ("北京市石景山区政府", "北京市石景山区人民政府"),
    ("北京市政府", "北京市人民政府"),
    ("北京市委", "中共北京市委员会"),
    ("上海市委", "中共上海市委员会"),
    ("上海市政府", "上海市人民政府"),
    ("环保部", "中华人民共和国环境保护部"),
    ("原环保部", "中华人民共和国环境保护部"),
    ("生态环境部", "中华人民共和国生态环境部"),
    ("自然资源部", "中华人民共和国自然资源部"),
    ("银保监会", "中国银行保险监督管理委员会"),
    ("国家金融监管总局", "国家金融监督管理总局"),
    ("金融监管总局", "国家金融监督管理总局"),
    ("中央党校", "中共中央党校（国家行政学院）"),
    ("中共中央党校", "中共中央党校（国家行政学院）"),
    ("清华", "清华大学"),
)

FALLEN_STATUSES = ("under_investigation", "expelled", "sentenced")


class CadreError(RuntimeError):
    """Raised on validation or database contract errors."""


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def current_ym() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


def default_db_path() -> Path:
    data_dir = os.environ.get("PAP_DATA_DIR", "").strip()
    if data_dir:
        return Path(data_dir) / "cadre-tracker" / "cadre.sqlite3"
    return REPO_ROOT / "var" / "cadre-tracker" / "cadre.sqlite3"


def _sha_hex(text: str, length: int = 12) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:length]


def make_org_id(canonical_name: str) -> str:
    return f"org_{_sha_hex(canonical_name.strip(), 12)}"


def make_person_id(name: str, birth_ym: str | None = None, hint: str | None = None) -> str:
    base = name.strip()
    if birth_ym:
        suffix = birth_ym.replace("-", "")
        tag = _sha_hex(f"{base}|{birth_ym}", 6)
        return f"p_{tag}_{suffix}"
    tag = _sha_hex(f"{base}|{hint or ''}", 10)
    return f"p_{tag}"


def make_source_id(url: str | None, content_hash: str) -> str:
    url_part = url or ""
    return f"src_{_sha_hex(f'{url_part}|{content_hash}', 16)}"


def make_tenure_id(person_id: str, org_id: str, role_title: str, start_ym: str) -> str:
    return f"ten_{_sha_hex(f'{person_id}|{org_id}|{role_title}|{start_ym}', 14)}"


def make_edu_id(person_id: str, school_org_id: str, degree: str | None, start_ym: str | None) -> str:
    deg_part = degree or ""
    start_part = start_ym or ""
    return f"edu_{_sha_hex(f'{person_id}|{school_org_id}|{deg_part}|{start_part}', 14)}"


def make_claim_id(source_id: str, claim_type: str, subject_raw_name: str, evidence_quote: str) -> str:
    return f"clm_{_sha_hex(f'{source_id}|{claim_type}|{subject_raw_name}|{evidence_quote}', 16)}"


def connect(db_path: Path | str | None = None, *, readonly: bool = False, timeout: float = 10.0) -> sqlite3.Connection:
    path = Path(db_path) if db_path is not None else default_db_path()
    if readonly:
        uri = f"{path.resolve().as_uri()}?mode=ro"
        conn = sqlite3.connect(uri, uri=True, timeout=timeout)
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(path), timeout=timeout)
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
        conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def migrate(conn_or_path: sqlite3.Connection | Path | str | None = None) -> dict[str, Any]:
    close_after = not isinstance(conn_or_path, sqlite3.Connection)
    conn = conn_or_path if isinstance(conn_or_path, sqlite3.Connection) else connect(conn_or_path)
    try:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS schema_migrations (
                   version TEXT PRIMARY KEY,
                   applied_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
               )"""
        )
        applied = {
            row["version"] for row in conn.execute("SELECT version FROM schema_migrations").fetchall()
        }
        newly_applied: list[str] = []
        for sql_file in sorted(MIGRATIONS_DIR.glob("*.sql")):
            version = sql_file.name
            if version in applied:
                continue
            sql_text = sql_file.read_text(encoding="utf-8")
            conn.executescript(sql_text)
            # executescript resets PRAGMAs on implicit commit; re-assert foreign_keys
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute("INSERT OR IGNORE INTO schema_migrations(version) VALUES (?)", (version,))
            conn.commit()
            newly_applied.append(version)
        return {"applied": newly_applied, "total": len(applied) + len(newly_applied)}
    finally:
        if close_after:
            conn.close()


def _upsert_org(
    conn: sqlite3.Connection,
    canonical_name: str,
    *,
    short_name: str | None = None,
    org_kind: str = "other",
    admin_level: str | None = None,
    province_name: str | None = None,
    region_code: str | None = None,
    parent_org_id: str | None = None,
    is_defunct: int = 0,
) -> str:
    row = conn.execute(
        "SELECT org_id, parent_org_id FROM organizations WHERE canonical_name = ?",
        (canonical_name,),
    ).fetchone()
    if row is not None:
        org_id = row["org_id"]
        if parent_org_id and not row["parent_org_id"]:
            conn.execute(
                "UPDATE organizations SET parent_org_id = ? WHERE org_id = ?",
                (parent_org_id, org_id),
            )
        return org_id
    org_id = make_org_id(canonical_name)
    conn.execute(
        """INSERT INTO organizations
           (org_id, canonical_name, short_name, org_kind, admin_level, province_name, region_code, parent_org_id, is_defunct)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            org_id,
            canonical_name,
            short_name or canonical_name,
            org_kind,
            admin_level,
            province_name,
            region_code,
            parent_org_id,
            is_defunct,
        ),
    )
    return org_id


def parse_reform_lineage_markdown(md_path: Path = REFORM_LINEAGE_MD) -> list[dict[str, str]]:
    if not md_path.is_file():
        return []
    rows: list[dict[str, str]] = []
    for raw_line in md_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line.startswith("|") or line.startswith("| ---"):
            continue
        parts = [p.strip() for p in line.strip("|").split("|")]
        if len(parts) < 7 or parts[0] == "predecessor_canonical":
            continue
        rows.append(
            {
                "predecessor_canonical": parts[0],
                "successor_canonical": parts[1],
                "change_ym": parts[2],
                "reform_batch": parts[3],
                "org_kind": parts[4],
                "province_name": parts[5],
                "note": parts[6],
            }
        )
    return rows


def seed_org_skeleton(conn: sqlite3.Connection) -> dict[str, int]:
    """Batch 0: seed 31 provincial roots, central roots, aliases, and 2018/2023 reform lineage."""
    orgs_seeded = 0
    lineage_seeded = 0
    aliases_seeded = 0

    # Central roots
    cpc_central = _upsert_org(
        conn, "中国共产党中央委员会", short_name="中共中央", org_kind="party_central",
        admin_level="国级", province_name="中央",
    )
    state_council = _upsert_org(
        conn, "中华人民共和国国务院", short_name="国务院", org_kind="gov_central",
        admin_level="国级", province_name="中央", parent_org_id=cpc_central,
    )
    _upsert_org(
        conn, "中国共产党中央纪律检查委员会", short_name="中央纪委", org_kind="commission_ccdi",
        admin_level="国级", province_name="中央", parent_org_id=cpc_central,
    )
    _upsert_org(
        conn, "清华大学", short_name="清华大学", org_kind="university",
        admin_level="副部级", province_name="北京",
    )
    _upsert_org(
        conn, "中共中央党校（国家行政学院）", short_name="中央党校", org_kind="party_school",
        admin_level="正部级", province_name="中央", parent_org_id=cpc_central,
    )
    orgs_seeded += 5

    # 31 provincial four-set leadership roots
    prov_gov_ids: dict[str, str] = {}
    prov_party_ids: dict[str, str] = {}
    for short_prov, full_prov, code in PROVINCES_31:
        party_name = f"中共{full_prov}委员会"
        gov_name = f"{full_prov}人民政府"
        npc_name = f"{full_prov}人民代表大会常务委员会"
        cppcc_name = f"中国人民政治协商会议{full_prov}委员会"

        pid = _upsert_org(
            conn, party_name, short_name=f"{short_prov}委", org_kind="party_local",
            admin_level="正部级", province_name=short_prov, region_code=code,
            parent_org_id=cpc_central,
        )
        gid = _upsert_org(
            conn, gov_name, short_name=f"{short_prov}政府", org_kind="gov_local",
            admin_level="正部级", province_name=short_prov, region_code=code,
            parent_org_id=state_council,
        )
        _upsert_org(
            conn, npc_name, short_name=f"{short_prov}人大常委会", org_kind="npc",
            admin_level="正部级", province_name=short_prov, region_code=code,
        )
        _upsert_org(
            conn, cppcc_name, short_name=f"{short_prov}政协", org_kind="cppcc",
            admin_level="正部级", province_name=short_prov, region_code=code,
        )
        prov_party_ids[short_prov] = pid
        prov_gov_ids[short_prov] = gid
        orgs_seeded += 4

    # Reform lineage pairs from profile/references/org-reform-lineage.md
    for item in parse_reform_lineage_markdown():
        prov = item["province_name"]
        kind = item["org_kind"]
        parent_id: str | None = None
        if prov == "中央":
            parent_id = cpc_central if kind == "party_central" else state_council
        elif prov in prov_gov_ids:
            parent_id = prov_party_ids[prov] if kind == "party_local" else prov_gov_ids[prov]

        pred_id = _upsert_org(
            conn,
            item["predecessor_canonical"],
            org_kind=kind,
            province_name=prov,
            parent_org_id=parent_id,
            is_defunct=1,
        )
        succ_id = _upsert_org(
            conn,
            item["successor_canonical"],
            org_kind=kind,
            province_name=prov,
            parent_org_id=parent_id,
            is_defunct=0,
        )
        if pred_id != succ_id:
            cur = conn.execute(
                """INSERT OR IGNORE INTO org_lineage
                   (predecessor_org_id, successor_org_id, change_ym, reform_batch, note)
                   VALUES (?, ?, ?, ?, ?)""",
                (pred_id, succ_id, item["change_ym"], item["reform_batch"], item["note"]),
            )
            lineage_seeded += cur.rowcount

    # Seed common aliases (only when target org exists)
    for alias, canonical in COMMON_ORG_ALIASES:
        row = conn.execute(
            "SELECT org_id FROM organizations WHERE canonical_name = ?", (canonical,)
        ).fetchone()
        if row is not None:
            cur = conn.execute(
                "INSERT OR IGNORE INTO org_aliases(alias_name, org_id) VALUES (?, ?)",
                (alias, row["org_id"]),
            )
            aliases_seeded += cur.rowcount

    conn.commit()
    return {
        "orgs_seeded": orgs_seeded,
        "lineage_pairs_added": lineage_seeded,
        "aliases_added": aliases_seeded,
    }


def _cjk_augment(text: str) -> str:
    """Emit original text plus CJK 2-gram tokens so unicode61 FTS5 matches Chinese substrings."""
    tokens: list[str] = [text]
    for span in re.findall(r"[\u4e00-\u9fff]{2,}", text):
        if len(span) >= 2:
            tokens.extend(span[i : i + 2] for i in range(len(span) - 1))
    return " ".join(tokens)


def refresh_fts_person(conn: sqlite3.Connection, person_id: str) -> None:
    person = conn.execute(
        "SELECT person_id, name, native_place, summary_note FROM persons WHERE person_id = ?",
        (person_id,),
    ).fetchone()
    conn.execute("DELETE FROM cadre_fts WHERE person_id = ?", (person_id,))
    if person is None:
        return

    parts: list[str] = [person["name"] or "", person["native_place"] or "", person["summary_note"] or ""]
    tenures = conn.execute(
        """SELECT t.role_title, t.raw_role_text, o.canonical_name, o.short_name, o.province_name
           FROM tenures t
           JOIN organizations o ON o.org_id = t.org_id
           WHERE t.person_id = ?""",
        (person_id,),
    ).fetchall()
    for t in tenures:
        parts.extend(
            str(x) for x in (t["canonical_name"], t["short_name"], t["province_name"], t["role_title"], t["raw_role_text"]) if x
        )
    edus = conn.execute(
        """SELECT e.department, e.degree, e.major, o.canonical_name, o.short_name
           FROM education_records e
           JOIN organizations o ON o.org_id = e.school_org_id
           WHERE e.person_id = ?""",
        (person_id,),
    ).fetchall()
    for e in edus:
        parts.extend(
            str(x) for x in (e["canonical_name"], e["short_name"], e["department"], e["degree"], e["major"]) if x
        )

    raw_blob = " ".join(p for p in parts if p)
    conn.execute(
        "INSERT INTO cadre_fts(person_id, name, native_place, resume_blob) VALUES (?, ?, ?, ?)",
        (
            person["person_id"],
            person["name"],
            person["native_place"] or "",
            _cjk_augment(raw_blob),
        ),
    )


def rebuild_fts(conn: sqlite3.Connection) -> int:
    conn.execute("DELETE FROM cadre_fts")
    ids = [r["person_id"] for r in conn.execute("SELECT person_id FROM persons").fetchall()]
    for pid in ids:
        refresh_fts_person(conn, pid)
    conn.commit()
    return len(ids)


# ---------------------------------------------------------------------------
# Temporal & Graph Inference Engine (Section 8)
# ---------------------------------------------------------------------------


def ym_to_int(ym: str) -> int:
    year_s, month_s = ym.split("-")
    return int(year_s) * 12 + int(month_s)


def int_to_ym(val: int) -> str:
    year = (val - 1) // 12
    month = ((val - 1) % 12) + 1
    return f"{year:04d}-{month:02d}"


def compute_overlap_span(
    start_a: str,
    end_a: str | None,
    start_b: str,
    end_b: str | None,
    *,
    now_ym: str | None = None,
) -> tuple[str, str, int] | None:
    now = now_ym or current_ym()
    ea = end_a or now
    eb = end_b or now
    max_start = max(start_a, start_b)
    min_end = min(ea, eb)
    if max_start > min_end:
        return None
    months = ym_to_int(min_end) - ym_to_int(max_start) + 1
    return max_start, min_end, months


def _merge_ym_intervals(intervals: list[tuple[str, str]]) -> tuple[list[tuple[str, str]], int]:
    if not intervals:
        return [], 0
    numeric = sorted((ym_to_int(s), ym_to_int(e)) for s, e in intervals)
    merged: list[tuple[int, int]] = [numeric[0]]
    for s, e in numeric[1:]:
        prev_s, prev_e = merged[-1]
        if s <= prev_e + 1:
            merged[-1] = (prev_s, max(prev_e, e))
        else:
            merged.append((s, e))
    total_months = sum(e - s + 1 for s, e in merged)
    return [(int_to_ym(s), int_to_ym(e)) for s, e in merged], total_months


def get_org_equivalence_cluster(conn: sqlite3.Connection, org_id: str, max_hops: int = 4) -> set[str]:
    """Bidirectional Recursive CTE over org_lineage up to max_hops."""
    rows = conn.execute(
        """WITH RECURSIVE equiv(org_id, depth) AS (
               SELECT ?, 0
               UNION
               SELECT CASE WHEN l.predecessor_org_id = e.org_id THEN l.successor_org_id ELSE l.predecessor_org_id END,
                      e.depth + 1
               FROM org_lineage l
               JOIN equiv e ON l.predecessor_org_id = e.org_id OR l.successor_org_id = e.org_id
               WHERE e.depth < ?
           )
           SELECT DISTINCT org_id FROM equiv""",
        (org_id, max_hops),
    ).fetchall()
    return {r["org_id"] for r in rows}


def _get_org_ancestors(conn: sqlite3.Connection, org_id: str, max_hops: int = 2) -> dict[str, int]:
    """Return {ancestor_org_id: hop_distance} via parent_org_id using WITH RECURSIVE."""
    rows = conn.execute(
        """WITH RECURSIVE anc(org_id, hop) AS (
               SELECT ?, 0
               UNION
               SELECT o.parent_org_id, a.hop + 1
               FROM organizations o
               JOIN anc a ON o.org_id = a.org_id
               WHERE o.parent_org_id IS NOT NULL AND a.hop < ?
           )
           SELECT org_id, MIN(hop) AS hop FROM anc GROUP BY org_id""",
        (org_id, max_hops),
    ).fetchall()
    return {r["org_id"]: int(r["hop"]) for r in rows}


def _resolve_person_row(conn: sqlite3.Connection, identifier: str) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM persons WHERE person_id = ?", (identifier,)).fetchone()
    if row is not None:
        return row
    rows = conn.execute(
        "SELECT * FROM persons WHERE name = ? ORDER BY updated_at DESC", (identifier,)
    ).fetchall()
    if not rows:
        raise CadreError(f"Person not found: {identifier}")
    return rows[0]


def _resolve_org_row(conn: sqlite3.Connection, identifier: str) -> sqlite3.Row:
    row = conn.execute(
        "SELECT * FROM organizations WHERE org_id = ? OR canonical_name = ? OR short_name = ?",
        (identifier, identifier, identifier),
    ).fetchone()
    if row is not None:
        return row
    alias = conn.execute(
        """SELECT o.* FROM org_aliases a
           JOIN organizations o ON o.org_id = a.org_id
           WHERE a.alias_name = ?""",
        (identifier,),
    ).fetchone()
    if alias is not None:
        return alias
    raise CadreError(f"Organization not found: {identifier}")


def _classify_pair_topology(
    conn: sqlite3.Connection,
    t_a: sqlite3.Row,
    t_b: sqlite3.Row,
    equiv_cache: dict[str, set[str]],
    anc_cache: dict[str, dict[str, int]],
) -> tuple[int, str, float, str] | None:
    """Return (hop, relation_label, topology_weight, direction) or None if unrelated."""
    org_a = t_a["org_id"]
    org_b = t_b["org_id"]

    if org_a not in equiv_cache:
        equiv_cache[org_a] = get_org_equivalence_cluster(conn, org_a)
    if org_b not in equiv_cache:
        equiv_cache[org_b] = get_org_equivalence_cluster(conn, org_b)

    # Hop 0: same org or org_lineage equivalence cluster
    if org_b in equiv_cache[org_a]:
        wa = float(t_a["role_tier_weight"])
        wb = float(t_b["role_tier_weight"])
        tier_a = t_a["role_tier"]
        tier_b = t_b["role_tier"]
        if wa > wb and tier_a in ("chief", "gov_head", "deputy_chief"):
            weight = 3.0 if tier_a in ("chief", "gov_head") else 2.5
            return (0, "same_org_leader", weight, "A_leads_B")
        if wb > wa and tier_b in ("chief", "gov_head", "deputy_chief"):
            weight = 3.0 if tier_b in ("chief", "gov_head") else 2.5
            return (0, "same_org_leader", weight, "B_leads_A")
        if tier_a in ("chief", "gov_head") or tier_b in ("chief", "gov_head"):
            return (0, "same_org_leader", 3.0, "peer")
        return (0, "same_org_peer", 2.0, "peer")

    # Hop 1..2 via parent_org_id (also checking equivalence cluster of ancestors)
    if org_a not in anc_cache:
        anc_cache[org_a] = _get_org_ancestors(conn, org_a, max_hops=2)
    if org_b not in anc_cache:
        anc_cache[org_b] = _get_org_ancestors(conn, org_b, max_hops=2)

    # Check if org_a (or its equiv) is an ancestor of org_b
    for anc_id, hop in anc_cache[org_b].items():
        if hop > 0 and anc_id in equiv_cache[org_a]:
            if hop == 1 and t_a["role_tier"] in ("chief", "gov_head", "deputy_chief") and t_b["role_tier"] in ("chief", "gov_head", "deputy_chief"):
                return (1, "parent_child_direct", 2.2, "A_supervises_B")
            return (hop, "subordinate_tree", 1.0, "A_supervises_B")

    # Check if org_b (or its equiv) is an ancestor of org_a
    for anc_id, hop in anc_cache[org_a].items():
        if hop > 0 and anc_id in equiv_cache[org_b]:
            if hop == 1 and t_b["role_tier"] in ("chief", "gov_head", "deputy_chief") and t_a["role_tier"] in ("chief", "gov_head", "deputy_chief"):
                return (1, "parent_child_direct", 2.2, "B_supervises_A")
            return (hop, "subordinate_tree", 1.0, "B_supervises_A")

    # Cross-branch municipal/provincial dual-track supervision:
    # e.g., Mayor of Beijing (gov_local, gov_head) supervising a Beijing District Party Secretary
    # (party_local, chief, parent = 中共北京市委员会) in the same province.
    prov_a = t_a["province_name"]
    prov_b = t_b["province_name"]
    if prov_a and prov_a == prov_b and prov_a != "中央":
        if (
            t_a["org_kind"] == "gov_local"
            and t_a["admin_level"] == "正部级"
            and t_a["role_tier"] in ("chief", "gov_head", "deputy_chief")
            and t_b["org_kind"] in ("party_local", "gov_local")
            and t_b["admin_level"] != "正部级"
            and t_b["role_tier"] in ("chief", "gov_head")
        ):
            return (1, "parent_child_direct", 2.2, "A_supervises_B")
        if (
            t_b["org_kind"] == "gov_local"
            and t_b["admin_level"] == "正部级"
            and t_b["role_tier"] in ("chief", "gov_head", "deputy_chief")
            and t_a["org_kind"] in ("party_local", "gov_local")
            and t_a["admin_level"] != "正部级"
            and t_a["role_tier"] in ("chief", "gov_head")
        ):
            return (1, "parent_child_direct", 2.2, "B_supervises_A")

    return None


def _fetch_person_tenures(conn: sqlite3.Connection, person_id: str) -> list[sqlite3.Row]:
    return conn.execute(
        """SELECT t.*, o.canonical_name, o.short_name, o.org_kind, o.admin_level,
                  o.province_name, o.parent_org_id
           FROM tenures t
           JOIN organizations o ON o.org_id = t.org_id
           WHERE t.person_id = ?
           ORDER BY t.start_ym ASC""",
        (person_id,),
    ).fetchall()


def query_overlap(
    conn: sqlite3.Connection,
    person_a: str,
    person_b: str,
    *,
    now_ym: str | None = None,
) -> dict[str, Any]:
    """Full 4-cluster overlap query between two cadres (Section 8.1)."""
    pa = _resolve_person_row(conn, person_a)
    pb = _resolve_person_row(conn, person_b)
    pid_a, pid_b = pa["person_id"], pb["person_id"]
    now = now_ym or current_ym()

    tenures_a = _fetch_person_tenures(conn, pid_a)
    tenures_b = _fetch_person_tenures(conn, pid_b)
    equiv_cache: dict[str, set[str]] = {}
    anc_cache: dict[str, dict[str, int]] = {}

    work_overlaps: list[dict[str, Any]] = []
    succession_links: list[dict[str, Any]] = []
    seen_successions: set[tuple[str, str]] = set()

    for ta in tenures_a:
        for tb in tenures_b:
            # 1. Work overlap
            topo = _classify_pair_topology(conn, ta, tb, equiv_cache, anc_cache)
            if topo is not None:
                span = compute_overlap_span(ta["start_ym"], ta["end_ym"], tb["start_ym"], tb["end_ym"], now_ym=now)
                if span is not None:
                    ov_start, ov_end, months = span
                    hop, rel_label, weight, direction = topo
                    work_overlaps.append(
                        {
                            "hop": hop,
                            "relation": rel_label,
                            "direction": direction,
                            "topology_weight": weight,
                            "overlap_start": ov_start,
                            "overlap_end": ov_end,
                            "overlap_months": months,
                            "a_org": ta["canonical_name"],
                            "a_role": ta["role_title"],
                            "a_span": [ta["start_ym"], ta["end_ym"]],
                            "b_org": tb["canonical_name"],
                            "b_role": tb["role_title"],
                            "b_span": [tb["start_ym"], tb["end_ym"]],
                        }
                    )

            # 2. Succession links (same equiv cluster & same role_title)
            if ta["org_id"] not in equiv_cache:
                equiv_cache[ta["org_id"]] = get_org_equivalence_cluster(conn, ta["org_id"])
            if tb["org_id"] in equiv_cache[ta["org_id"]] and ta["role_title"] == tb["role_title"]:
                pair_key = (ta["tenure_id"], tb["tenure_id"])
                if pair_key in seen_successions:
                    continue
                is_a_then_b = False
                is_b_then_a = False
                if ta["end_ym"] and abs(ym_to_int(tb["start_ym"]) - ym_to_int(ta["end_ym"])) <= 2:
                    is_a_then_b = True
                if tb["end_ym"] and abs(ym_to_int(ta["start_ym"]) - ym_to_int(tb["end_ym"])) <= 2:
                    is_b_then_a = True
                if ta["successor_name"] == pb["name"] or tb["predecessor_name"] == pa["name"]:
                    is_a_then_b = True
                if tb["successor_name"] == pa["name"] or ta["predecessor_name"] == pb["name"]:
                    is_b_then_a = True
                if is_a_then_b or is_b_then_a:
                    seen_successions.add(pair_key)
                    succession_links.append(
                        {
                            "org": ta["canonical_name"],
                            "role_title": ta["role_title"],
                            "role_tier": ta["role_tier"],
                            "direction": "A_precedes_B" if is_a_then_b else "B_precedes_A",
                            "a_span": [ta["start_ym"], ta["end_ym"]],
                            "b_span": [tb["start_ym"], tb["end_ym"]],
                        }
                    )

    # 3. Education / alumni links
    edus_a = conn.execute(
        """SELECT e.*, o.canonical_name, o.org_kind FROM education_records e
           JOIN organizations o ON o.org_id = e.school_org_id WHERE e.person_id = ?""",
        (pid_a,),
    ).fetchall()
    edus_b = conn.execute(
        """SELECT e.*, o.canonical_name, o.org_kind FROM education_records e
           JOIN organizations o ON o.org_id = e.school_org_id WHERE e.person_id = ?""",
        (pid_b,),
    ).fetchall()

    edu_links: list[dict[str, Any]] = []
    for ea in edus_a:
        if ea["school_org_id"] not in equiv_cache:
            equiv_cache[ea["school_org_id"]] = get_org_equivalence_cluster(conn, ea["school_org_id"])
        for eb in edus_b:
            if eb["school_org_id"] not in equiv_cache[ea["school_org_id"]]:
                continue
            overlap_span = None
            if ea["start_ym"] and eb["start_ym"]:
                overlap_span = compute_overlap_span(
                    ea["start_ym"], ea["end_ym"] or ea["start_ym"],
                    eb["start_ym"], eb["end_ym"] or eb["start_ym"],
                    now_ym=now,
                )
            same_dept = bool(ea["department"] and eb["department"] and ea["department"] == eb["department"])
            is_party_school = ea["org_kind"] == "party_school" or "中央党校" in ea["canonical_name"]
            if is_party_school and ea["start_ym"] and ea["start_ym"] == eb["start_ym"] and ea["end_ym"] == eb["end_ym"]:
                tag = "中青班同期同窗"
            elif same_dept:
                tag = "同院系校友"
            elif overlap_span is not None:
                tag = "同期同校校友"
            else:
                tag = "同校校友"
            edu_links.append(
                {
                    "school": ea["canonical_name"],
                    "relation": tag,
                    "a_department": ea["department"],
                    "b_department": eb["department"],
                    "a_span": [ea["start_ym"], ea["end_ym"]],
                    "b_span": [eb["start_ym"], eb["end_ym"]],
                    "overlap_months": overlap_span[2] if overlap_span else 0,
                }
            )

    # 4. External clues involving both A and B
    clues = conn.execute(
        """SELECT c.claim_id, c.claim_type, c.event_date, c.certainty, c.evidence_quote,
                  c.payload_json, s.source_name, s.credibility_tier
           FROM claims_and_clues c
           JOIN raw_sources s ON s.source_id = c.source_id
           WHERE (c.subject_person_id = ? AND c.related_person_id = ?)
              OR (c.subject_person_id = ? AND c.related_person_id = ?)
           ORDER BY c.created_at DESC""",
        (pid_a, pid_b, pid_b, pid_a),
    ).fetchall()
    external_clues = [
        {
            "claim_id": r["claim_id"],
            "claim_type": r["claim_type"],
            "event_date": r["event_date"],
            "certainty": r["certainty"],
            "evidence_quote": r["evidence_quote"],
            "source_name": r["source_name"],
            "credibility_tier": r["credibility_tier"],
            "payload": json.loads(r["payload_json"]),
        }
        for r in clues
    ]

    merged_spans, total_unique_months = _merge_ym_intervals(
        [(w["overlap_start"], w["overlap_end"]) for w in work_overlaps]
    )

    return {
        "person_a": {"person_id": pid_a, "name": pa["name"], "status": pa["status"]},
        "person_b": {"person_id": pid_b, "name": pb["name"], "status": pb["status"]},
        "work_overlaps": work_overlaps,
        "merged_work_spans": [[s, e] for s, e in merged_spans],
        "total_unique_overlap_months": total_unique_months,
        "succession_links": succession_links,
        "edu_links": edu_links,
        "external_clues": external_clues,
    }


def _recency_weight(overlap_end_ym: str, reference_year: int) -> float:
    end_year = int(overlap_end_ym.split("-")[0])
    age = reference_year - end_year
    if age <= 5:
        return 1.2
    if age <= 12:
        return 1.0
    return 0.6


def query_shockwave(
    conn: sqlite3.Connection,
    person: str,
    *,
    top_k: int = 20,
    reference_year: int = 2026,
    now_ym: str | None = None,
) -> dict[str, Any]:
    """Compute Closeness Index (CI) shockwave ranking (Section 8.2)."""
    subject = _resolve_person_row(conn, person)
    subject_id = subject["person_id"]
    now = now_ym or current_ym()

    others = conn.execute(
        "SELECT * FROM persons WHERE person_id != ?", (subject_id,)
    ).fetchall()

    fallen_list: list[dict[str, Any]] = []
    active_list: list[dict[str, Any]] = []
    other_list: list[dict[str, Any]] = []

    for candidate in others:
        cid = candidate["person_id"]
        ov = query_overlap(conn, subject_id, cid, now_ym=now)
        if not ov["work_overlaps"] and not ov["edu_links"] and not ov["succession_links"]:
            continue

        work_score = 0.0
        for w in ov["work_overlaps"]:
            m_k = min(int(w["overlap_months"]), 60)
            w_topo = float(w["topology_weight"])
            w_rec = _recency_weight(w["overlap_end"], reference_year)
            work_score += m_k * w_topo * w_rec

        # Alumni bonus (take highest qualifying bonus)
        alumni_bonus = 0.0
        for e in ov["edu_links"]:
            rel = e["relation"]
            if rel == "中青班同期同窗":
                alumni_bonus = max(alumni_bonus, 20.0)
            elif rel == "同院系校友":
                alumni_bonus = max(alumni_bonus, 15.0)
            else:
                alumni_bonus = max(alumni_bonus, 6.0)

        # Direct chief succession bonus
        succession_bonus = 0.0
        for s in ov["succession_links"]:
            if s["role_tier"] in ("chief", "gov_head"):
                succession_bonus = 25.0
                break

        ci = round(work_score + alumni_bonus + succession_bonus, 2)
        if ci <= 0:
            continue

        entry = {
            "person_id": cid,
            "name": candidate["name"],
            "status": candidate["status"],
            "current_rank": candidate["current_rank"],
            "closeness_index": ci,
            "work_score": round(work_score, 2),
            "alumni_bonus": alumni_bonus,
            "succession_bonus": succession_bonus,
            "total_unique_overlap_months": ov["total_unique_overlap_months"],
            "merged_work_spans": ov["merged_work_spans"],
            "edu_relations": sorted({e["relation"] for e in ov["edu_links"]}),
            "work_overlap_count": len(ov["work_overlaps"]),
            "succession_count": len(ov["succession_links"]),
        }
        if candidate["status"] in FALLEN_STATUSES:
            fallen_list.append(entry)
        elif candidate["status"] in ("active", "anomaly_watch"):
            active_list.append(entry)
        else:
            other_list.append(entry)

    fallen_list.sort(key=lambda x: (-x["closeness_index"], x["person_id"]))
    active_list.sort(key=lambda x: (-x["closeness_index"], x["person_id"]))
    other_list.sort(key=lambda x: (-x["closeness_index"], x["person_id"]))

    return {
        "subject": {
            "person_id": subject_id,
            "name": subject["name"],
            "status": subject["status"],
            "current_rank": subject["current_rank"],
        },
        "already_fallen_associates": fallen_list[:top_k],
        "active_watch_list": active_list[:top_k],
        "other_associates": other_list[:top_k],
    }


def query_succession(
    conn: sqlite3.Connection,
    org_identifier: str,
    role_title: str,
) -> dict[str, Any]:
    """Chronological succession chain across org_lineage equivalence cluster."""
    org = _resolve_org_row(conn, org_identifier)
    cluster = sorted(get_org_equivalence_cluster(conn, org["org_id"], max_hops=4))
    placeholders = ",".join("?" for _ in cluster)
    rows = conn.execute(
        f"""SELECT t.tenure_id, t.person_id, p.name, p.status, p.current_rank,
                   o.canonical_name AS org_name, t.role_title, t.role_tier,
                   t.start_ym, t.end_ym, t.predecessor_name, t.successor_name
            FROM tenures t
            JOIN persons p ON p.person_id = t.person_id
            JOIN organizations o ON o.org_id = t.org_id
            WHERE t.org_id IN ({placeholders}) AND t.role_title = ?
            ORDER BY t.start_ym ASC, COALESCE(t.end_ym, '9999-12') ASC""",
        (*cluster, role_title),
    ).fetchall()

    org_names = [
        r["canonical_name"]
        for r in conn.execute(
            f"SELECT canonical_name FROM organizations WHERE org_id IN ({placeholders}) ORDER BY canonical_name",
            cluster,
        ).fetchall()
    ]
    return {
        "queried_org": org["canonical_name"],
        "equivalent_orgs": org_names,
        "role_title": role_title,
        "chain": [dict(r) for r in rows],
    }


def search_cadres(
    conn: sqlite3.Connection,
    query: str,
    *,
    status: str | None = None,
    rank: str | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Full-text search cadres via FTS5 cadre_fts with Chinese bigram support."""
    terms = [t.strip() for t in re.split(r"\s+", query.strip()) if t.strip()]
    if not terms:
        return []

    fts_parts: list[str] = []
    for term in terms:
        if re.fullmatch(r"[\u4e00-\u9fff]+", term) and len(term) >= 2:
            bigrams = [term[i : i + 2] for i in range(len(term) - 1)]
            fts_parts.append("(" + " AND ".join(f'"{b}"' for b in bigrams) + ")")
        else:
            safe = term.replace('"', "")
            fts_parts.append(f'"{safe}"')
    fts_expr = " AND ".join(fts_parts)

    where_extra = []
    params: list[Any] = [fts_expr]
    if status:
        where_extra.append("p.status = ?")
        params.append(status)
    if rank:
        where_extra.append("p.current_rank = ?")
        params.append(rank)
    extra_sql = (" AND " + " AND ".join(where_extra)) if where_extra else ""
    params.append(limit)

    rows = conn.execute(
        f"""SELECT p.person_id, p.name, p.birth_ym, p.native_place, p.current_rank, p.status, p.summary_note
            FROM cadre_fts f
            JOIN persons p ON p.person_id = f.person_id
            WHERE cadre_fts MATCH ?{extra_sql}
            LIMIT ?""",
        params,
    ).fetchall()
    return [dict(r) for r in rows]
