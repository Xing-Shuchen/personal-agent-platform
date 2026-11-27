"""Entity disambiguation scorer, org canonicalizer, and bundle ingestion engine (Section 6 & 7)."""

from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass
from typing import Any

try:
    from .db import (
        PROVINCES_31,
        RANK_ORDER,
        ROLE_TIER_WEIGHTS,
        CadreError,
        make_claim_id,
        make_edu_id,
        make_org_id,
        make_person_id,
        make_source_id,
        make_tenure_id,
        refresh_fts_person,
        utc_now_iso,
    )
except ImportError:
    from db import (  # type: ignore[no-redef]
        PROVINCES_31,
        RANK_ORDER,
        ROLE_TIER_WEIGHTS,
        CadreError,
        make_claim_id,
        make_edu_id,
        make_org_id,
        make_person_id,
        make_source_id,
        make_tenure_id,
        refresh_fts_person,
        utc_now_iso,
    )

VALID_STATUSES = {
    "active", "anomaly_watch", "retired", "demoted",
    "under_investigation", "expelled", "sentenced", "deceased",
}
VALID_ROLE_TIERS = set(ROLE_TIER_WEIGHTS)
VALID_CLAIM_TYPES = {
    "appointment", "removal", "investigation", "voluntary_surrender",
    "expulsion_sanction", "dom_removal_anomaly", "co_worker_mention",
    "patronage_speculation", "disambiguation_conflict",
}
CLOSING_STATUSES = {"retired", "demoted", "deceased"}
SECTOR_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("planning", ("规划", "自然资源", "国土", "城建", "住建", "建筑")),
    ("finance", ("金融", "银行", "保险", "证券", "银保监", "证监", "财政", "税务")),
    ("environment", ("环保", "环境", "生态", "水利")),
    ("legal", ("政法", "公安", "法院", "检察", "司法", "纪检", "监察")),
    ("education", ("教育", "大学", "学院", "党校", "科技")),
)


@dataclass
class ResolutionResult:
    decision: str  # 'auto_merged' | 'create_new' | 'needs_review'
    person_id: str | None
    score: float
    candidates: list[dict[str, Any]]
    reason: str


def _infer_province_from_org(canonical_name: str) -> str | None:
    if canonical_name.startswith(("中共中央", "中华人民共和国", "国家", "国务院", "中央")):
        return "中央"
    for short_prov, full_prov, _ in PROVINCES_31:
        if full_prov in canonical_name or canonical_name.startswith(f"中共{short_prov}") or canonical_name.startswith(short_prov):
            return short_prov
    return None


def _infer_parent_org_id(
    conn: sqlite3.Connection,
    canonical_name: str,
    org_kind: str,
    province_name: str | None,
) -> str | None:
    prov = province_name or _infer_province_from_org(canonical_name)
    if not prov or prov == "中央":
        return None
    full_prov = next((fp for sp, fp, _ in PROVINCES_31 if sp == prov), None)
    if not full_prov:
        return None
    party_root_name = f"中共{full_prov}委员会"
    gov_root_name = f"{full_prov}人民政府"
    if canonical_name in (party_root_name, gov_root_name):
        return None
    target_parent = party_root_name if org_kind == "party_local" or canonical_name.startswith("中共") else gov_root_name
    row = conn.execute(
        "SELECT org_id FROM organizations WHERE canonical_name = ?", (target_parent,)
    ).fetchone()
    return row["org_id"] if row else None


def resolve_or_create_org(
    conn: sqlite3.Connection,
    canonical_name: str,
    *,
    short_name: str | None = None,
    org_kind: str = "other",
    admin_level: str | None = None,
    province_name: str | None = None,
    parent_org_canonical_name: str | None = None,
) -> str:
    """Resolve canonical org by canonical_name -> org_aliases -> short_name, or create with auto-parent."""
    name = canonical_name.strip()
    if not name:
        raise CadreError("Organization canonical_name cannot be empty")

    row = conn.execute(
        "SELECT org_id, parent_org_id FROM organizations WHERE canonical_name = ?", (name,)
    ).fetchone()
    if row is None:
        alias = conn.execute(
            """SELECT o.org_id, o.parent_org_id FROM org_aliases a
               JOIN organizations o ON o.org_id = a.org_id
               WHERE a.alias_name = ?""",
            (name,),
        ).fetchone()
        row = alias
    if row is None:
        row = conn.execute(
            "SELECT org_id, parent_org_id FROM organizations WHERE short_name = ?", (name,)
        ).fetchone()

    parent_id: str | None = None
    if parent_org_canonical_name:
        parent_id = resolve_or_create_org(
            conn,
            parent_org_canonical_name,
            org_kind="party_local" if parent_org_canonical_name.startswith("中共") else org_kind,
            province_name=province_name or _infer_province_from_org(parent_org_canonical_name),
        )

    if row is not None:
        org_id = row["org_id"]
        if parent_id and not row["parent_org_id"] and parent_id != org_id:
            conn.execute("UPDATE organizations SET parent_org_id = ? WHERE org_id = ?", (parent_id, org_id))
        if short_name and short_name.strip() != name:
            conn.execute(
                "INSERT OR IGNORE INTO org_aliases(alias_name, org_id) VALUES (?, ?)",
                (short_name.strip(), org_id),
            )
        return org_id

    prov = province_name or _infer_province_from_org(name)
    if parent_id is None:
        parent_id = _infer_parent_org_id(conn, name, org_kind, prov)

    org_id = make_org_id(name)
    conn.execute(
        """INSERT INTO organizations
           (org_id, canonical_name, short_name, org_kind, admin_level, province_name, parent_org_id, is_defunct)
           VALUES (?, ?, ?, ?, ?, ?, ?, 0)""",
        (org_id, name, (short_name or name).strip(), org_kind, admin_level, prov, parent_id),
    )
    if short_name and short_name.strip() != name:
        conn.execute(
            "INSERT OR IGNORE INTO org_aliases(alias_name, org_id) VALUES (?, ?)",
            (short_name.strip(), org_id),
        )
    return org_id


def _sector_of(text: str | None) -> str | None:
    if not text:
        return None
    for sector, kws in SECTOR_KEYWORDS:
        if any(kw in text for kw in kws):
            return sector
    return None


def resolve_person(
    conn: sqlite3.Connection,
    *,
    name: str,
    birth_ym: str | None = None,
    native_place: str | None = None,
    gender: str | None = None,
    wikidata_qid: str | None = None,
    incoming_rank: str | None = None,
    incoming_org_name: str | None = None,
    incoming_action: str | None = None,
    allow_create: bool = True,
) -> ResolutionResult:
    """4-stage entity disambiguation scorer (Section 7.1)."""
    clean_name = name.strip()
    if not clean_name:
        raise CadreError("Person name cannot be empty")

    # Stage 1a: exact wikidata_qid match
    if wikidata_qid:
        qrow = conn.execute(
            "SELECT person_id, name FROM persons WHERE wikidata_qid = ?", (wikidata_qid,)
        ).fetchone()
        if qrow is not None:
            return ResolutionResult(
                decision="auto_merged",
                person_id=qrow["person_id"],
                score=1.0,
                candidates=[{"person_id": qrow["person_id"], "score": 1.0, "reason": "wikidata_qid_exact"}],
                reason="wikidata_qid_exact",
            )

    same_name_rows = conn.execute(
        "SELECT * FROM persons WHERE name = ?", (clean_name,)
    ).fetchall()

    if not same_name_rows:
        rank_val = RANK_ORDER.get(incoming_rank or "副省部级", 3)
        if allow_create and (rank_val >= 3 or birth_ym or wikidata_qid or incoming_rank is None):
            return ResolutionResult(
                decision="create_new",
                person_id=None,
                score=0.0,
                candidates=[],
                reason="no_existing_same_name",
            )
        return ResolutionResult(
            decision="needs_review",
            person_id=None,
            score=0.0,
            candidates=[],
            reason="below_rank_threshold_no_existing",
        )

    scored: list[dict[str, Any]] = []
    incoming_prov = _infer_province_from_org(incoming_org_name) if incoming_org_name else None
    incoming_sector = _sector_of(incoming_org_name)

    for cand in same_name_rows:
        cid = cand["person_id"]
        # Stage 2: hard conflict veto
        if birth_ym and cand["birth_ym"] and birth_ym != cand["birth_ym"]:
            continue
        if gender and cand["gender"] and gender != cand["gender"]:
            continue

        # Stage 1b: hard feature exact match
        if birth_ym and cand["birth_ym"] == birth_ym:
            if not native_place or not cand["native_place"] or native_place == cand["native_place"]:
                return ResolutionResult(
                    decision="auto_merged",
                    person_id=cid,
                    score=1.0,
                    candidates=[{"person_id": cid, "score": 1.0, "reason": "birth_ym_exact"}],
                    reason="birth_ym_exact",
                )

        # Stage 3: career continuity & rank step scoring
        last_tenure = conn.execute(
            """SELECT t.*, o.canonical_name, o.short_name, o.province_name
               FROM tenures t
               JOIN organizations o ON o.org_id = t.org_id
               WHERE t.person_id = ?
               ORDER BY CASE WHEN t.end_ym IS NULL THEN 0 ELSE 1 END, t.start_ym DESC
               LIMIT 1""",
            (cid,),
        ).fetchone()

        # Removal exact org match -> 0.98
        if (
            incoming_action == "CLOSE_SPAN"
            and incoming_org_name
            and last_tenure is not None
            and (
                incoming_org_name in (last_tenure["canonical_name"], last_tenure["short_name"])
            )
        ):
            scored.append({"person_id": cid, "score": 0.98, "reason": "exact_removal_org_match"})
            continue

        cand_rank = (last_tenure["rank_at_time"] if last_tenure and last_tenure["rank_at_time"] else cand["current_rank"])
        rank_step_valid = 0.0
        if incoming_rank and cand_rank in RANK_ORDER and incoming_rank in RANK_ORDER:
            if abs(RANK_ORDER[incoming_rank] - RANK_ORDER[cand_rank]) <= 1 and cand["status"] not in ("retired", "expelled", "sentenced", "deceased"):
                rank_step_valid = 1.0
        elif incoming_rank is None and cand["status"] in ("active", "anomaly_watch"):
            rank_step_valid = 0.5

        org_or_region = 0.0
        if incoming_org_name and last_tenure is not None:
            if incoming_org_name in (last_tenure["canonical_name"], last_tenure["short_name"]):
                org_or_region = 1.0
            elif incoming_prov and last_tenure["province_name"] == incoming_prov:
                org_or_region = 1.0
            elif incoming_sector and _sector_of(last_tenure["canonical_name"]) == incoming_sector:
                org_or_region = 1.0

        status_active = 1.0 if cand["status"] in ("active", "anomaly_watch") else 0.0
        score = round(0.45 * rank_step_valid + 0.35 * org_or_region + 0.20 * status_active, 4)
        scored.append(
            {
                "person_id": cid,
                "name": cand["name"],
                "birth_ym": cand["birth_ym"],
                "current_rank": cand["current_rank"],
                "status": cand["status"],
                "score": score,
            }
        )

    if not scored:
        # All existing same-name candidates were hard-vetoed by birth_ym or gender -> genuinely different person
        return ResolutionResult(
            decision="create_new",
            person_id=None,
            score=0.0,
            candidates=[],
            reason="all_existing_vetoed_by_hard_features",
        )

    scored.sort(key=lambda item: (-item["score"], item["person_id"]))
    top = scored[0]
    second_score = scored[1]["score"] if len(scored) > 1 else 0.0
    gap = top["score"] - second_score

    # Stage 4: threshold decision
    if top["score"] >= 0.85 and (len(scored) == 1 or gap >= 0.30):
        return ResolutionResult(
            decision="auto_merged",
            person_id=top["person_id"],
            score=top["score"],
            candidates=scored,
            reason="high_confidence_score",
        )

    # Ambiguous match (especially when multiple same-name candidates exist or 0.40 <= S < 0.85)
    if len(scored) > 1 or 0.40 <= top["score"] < 0.85 or (not birth_ym and len(scored) >= 1):
        return ResolutionResult(
            decision="needs_review",
            person_id=None,
            score=top["score"],
            candidates=scored,
            reason="ambiguous_same_name_candidates",
        )

    return ResolutionResult(
        decision="create_new",
        person_id=None,
        score=top["score"],
        candidates=scored,
        reason="low_similarity_new_person",
    )


def _validate_ym(value: str | None, field_name: str, *, required: bool = False) -> str | None:
    if value is None:
        if required:
            raise CadreError(f"Missing required YYYY-MM field: {field_name}")
        return None
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}", value):
        raise CadreError(f"Field {field_name} must be YYYY-MM, got {value!r}")
    return value


def _ensure_source(conn: sqlite3.Connection, bundle: dict[str, Any]) -> tuple[str, int]:
    source_id = bundle.get("source_id")
    if not isinstance(source_id, str) or not source_id.strip():
        raise CadreError("bundle.source_id is required")
    row = conn.execute(
        "SELECT source_id, credibility_tier FROM raw_sources WHERE source_id = ?",
        (source_id,),
    ).fetchone()
    if row is not None:
        return row["source_id"], int(row["credibility_tier"])

    inline = bundle.get("source")
    if not isinstance(inline, dict):
        raise CadreError(f"source_id {source_id!r} not found in raw_sources and no inline 'source' provided")

    raw_content = str(inline.get("raw_content", ""))
    content_hash = str(inline.get("content_hash") or make_source_id(inline.get("url"), raw_content)[4:])
    tier = int(inline.get("credibility_tier", 2))
    conn.execute(
        """INSERT INTO raw_sources
           (source_id, source_type, source_name, credibility_tier, url, title, published_at, content_hash, raw_content, ingest_status)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending')""",
        (
            source_id,
            inline.get("source_type", "manual_note"),
            inline.get("source_name", "manual"),
            tier,
            inline.get("url"),
            inline.get("title"),
            inline.get("published_at", utc_now_iso()),
            content_hash,
            raw_content,
        ),
    )
    return source_id, tier


def ingest_bundle(conn: sqlite3.Connection, bundle: dict[str, Any]) -> dict[str, Any]:
    """Validate and idempotently ingest a cadre-bundle v1.0 JSON payload."""
    if not isinstance(bundle, dict):
        raise CadreError("Bundle must be a JSON object")
    if str(bundle.get("schema_version")) != "1.0":
        raise CadreError(f"Unsupported schema_version: {bundle.get('schema_version')!r}")

    source_id, source_tier = _ensure_source(conn, bundle)
    now_iso = utc_now_iso()

    stats: dict[str, Any] = {
        "source_id": source_id,
        "credibility_tier": source_tier,
        "persons_inserted": 0,
        "persons_updated": 0,
        "tenures_inserted": 0,
        "tenures_updated": 0,
        "educations_inserted": 0,
        "claims_inserted": 0,
        "needs_review_count": 0,
        "credibility_lock_blocks": [],
        "touched_person_ids": [],
        "shockwave_trigger_person_ids": [],
    }
    touched_persons: set[str] = set()
    bundle_person_map: dict[tuple[str, str | None], str] = {}

    # Tier 4 rule: zero write access to persons / tenures / educations!
    if source_tier < 4:
        for p in bundle.get("persons", []) or []:
            name = str(p.get("name", "")).strip()
            birth_ym = _validate_ym(p.get("birth_ym"), "persons[].birth_ym")
            party_join_ym = _validate_ym(p.get("party_join_ym"), "persons[].party_join_ym")
            work_start_ym = _validate_ym(p.get("work_start_ym"), "persons[].work_start_ym")
            status = p.get("status", "active")
            if status not in VALID_STATUSES:
                raise CadreError(f"Invalid person status: {status!r}")

            res = resolve_person(
                conn,
                name=name,
                birth_ym=birth_ym,
                native_place=p.get("native_place"),
                gender=p.get("gender"),
                wikidata_qid=p.get("wikidata_qid"),
                incoming_rank=p.get("current_rank"),
            )

            if res.decision == "needs_review":
                cid = make_claim_id(source_id, "disambiguation_conflict", name, f"person:{name}:{p.get('current_rank')}")
                cur = conn.execute(
                    """INSERT OR IGNORE INTO claims_and_clues
                       (claim_id, source_id, claim_type, subject_raw_name, certainty, payload_json, evidence_quote, confidence, review_status)
                       VALUES (?, ?, 'disambiguation_conflict', ?, 'INFERRED', ?, ?, ?, 'needs_review')""",
                    (
                        cid,
                        source_id,
                        name,
                        json.dumps({"entity_kind": "person", "incoming": p, "candidates": res.candidates}, ensure_ascii=False),
                        f"Disambiguation required for person {name}",
                        res.score,
                    ),
                )
                if cur.rowcount:
                    stats["claims_inserted"] += 1
                    stats["needs_review_count"] += 1
                continue

            cc_json = json.dumps(p["cc_membership"], ensure_ascii=False) if p.get("cc_membership") is not None else None

            if res.decision == "create_new":
                pid = make_person_id(name, birth_ym, p.get("native_place") or p.get("wikidata_qid"))
                conn.execute(
                    """INSERT INTO persons
                       (person_id, name, gender, ethnicity, birth_ym, native_place, birth_place,
                        party_join_ym, work_start_ym, current_rank, cc_membership, status,
                        status_updated_at, credibility_lock, is_tracked_target, wikidata_qid, summary_note)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        pid,
                        name,
                        p.get("gender"),
                        p.get("ethnicity"),
                        birth_ym,
                        p.get("native_place"),
                        p.get("birth_place"),
                        party_join_ym,
                        work_start_ym,
                        p.get("current_rank") or "副省部级",
                        cc_json,
                        status,
                        p.get("status_updated_at") or now_iso,
                        source_tier,
                        int(p.get("is_tracked_target", 1)),
                        p.get("wikidata_qid"),
                        p.get("summary_note"),
                    ),
                )
                stats["persons_inserted"] += 1
                if status in ("under_investigation", "expelled", "anomaly_watch"):
                    stats["shockwave_trigger_person_ids"].append(pid)
            else:
                pid = str(res.person_id)
                existing = conn.execute("SELECT * FROM persons WHERE person_id = ?", (pid,)).fetchone()
                new_status = existing["status"]
                new_lock = int(existing["credibility_lock"])
                new_status_ts = existing["status_updated_at"]

                if "status" in p and p["status"] != existing["status"]:
                    if source_tier <= new_lock:
                        new_status = p["status"]
                        new_lock = source_tier
                        new_status_ts = p.get("status_updated_at") or now_iso
                        if new_status in ("under_investigation", "expelled", "anomaly_watch"):
                            stats["shockwave_trigger_person_ids"].append(pid)
                    else:
                        stats["credibility_lock_blocks"].append(
                            {
                                "target": "persons.status",
                                "person_id": pid,
                                "existing_status": existing["status"],
                                "existing_lock": new_lock,
                                "attempted_status": p["status"],
                                "incoming_tier": source_tier,
                            }
                        )
                elif "status" in p and source_tier < new_lock:
                    new_lock = source_tier

                conn.execute(
                    """UPDATE persons SET
                         gender = COALESCE(gender, ?),
                         ethnicity = COALESCE(ethnicity, ?),
                         birth_ym = COALESCE(birth_ym, ?),
                         native_place = COALESCE(native_place, ?),
                         birth_place = COALESCE(birth_place, ?),
                         party_join_ym = COALESCE(party_join_ym, ?),
                         work_start_ym = COALESCE(work_start_ym, ?),
                         current_rank = CASE WHEN ? <= credibility_lock AND ? IS NOT NULL THEN ? ELSE current_rank END,
                         cc_membership = COALESCE(?, cc_membership),
                         status = ?,
                         status_updated_at = ?,
                         credibility_lock = ?,
                         wikidata_qid = COALESCE(wikidata_qid, ?),
                         summary_note = COALESCE(?, summary_note),
                         updated_at = ?
                       WHERE person_id = ?""",
                    (
                        p.get("gender"),
                        p.get("ethnicity"),
                        birth_ym,
                        p.get("native_place"),
                        p.get("birth_place"),
                        party_join_ym,
                        work_start_ym,
                        source_tier,
                        p.get("current_rank"),
                        p.get("current_rank"),
                        cc_json,
                        new_status,
                        new_status_ts,
                        new_lock,
                        p.get("wikidata_qid"),
                        p.get("summary_note"),
                        now_iso,
                        pid,
                    ),
                )
                stats["persons_updated"] += 1

            touched_persons.add(pid)
            bundle_person_map[(name, birth_ym)] = pid
            bundle_person_map[(name, None)] = pid

            # Educations nested under person
            for edu in p.get("educations", []) or []:
                school_name = str(edu.get("school_name", "")).strip()
                if not school_name:
                    continue
                school_kind = "party_school" if "党校" in school_name else "university"
                school_org_id = resolve_or_create_org(conn, school_name, org_kind=school_kind)
                e_start = _validate_ym(edu.get("start_ym"), "educations[].start_ym")
                e_end = _validate_ym(edu.get("end_ym"), "educations[].end_ym")
                degree = edu.get("degree")
                edu_id = make_edu_id(pid, school_org_id, degree, e_start)
                is_ft = edu.get("is_full_time")
                is_ft_int = None if is_ft is None else (1 if bool(is_ft) else 0)
                cur = conn.execute(
                    """INSERT OR IGNORE INTO education_records
                       (edu_id, person_id, school_org_id, department, degree, major, is_full_time, start_ym, end_ym, source_id)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        edu_id, pid, school_org_id, edu.get("department"), degree,
                        edu.get("major"), is_ft_int, e_start, e_end, source_id,
                    ),
                )
                if cur.rowcount:
                    stats["educations_inserted"] += 1

        # Tenures
        for t in bundle.get("tenures", []) or []:
            pname = str(t.get("person_name", "")).strip()
            pbirth = _validate_ym(t.get("person_birth_ym"), "tenures[].person_birth_ym")
            action = str(t.get("action") or "UPSERT_SPAN")
            org_name = str(t.get("org_canonical_name", "")).strip()
            role_title = str(t.get("role_title", "")).strip()
            role_tier = str(t.get("role_tier") or "member")
            if role_tier not in VALID_ROLE_TIERS:
                raise CadreError(f"Invalid role_tier: {role_tier!r}")

            pid = bundle_person_map.get((pname, pbirth)) or bundle_person_map.get((pname, None))
            if pid is None:
                res = resolve_person(
                    conn,
                    name=pname,
                    birth_ym=pbirth,
                    native_place=t.get("person_native_place"),
                    wikidata_qid=t.get("person_wikidata_qid"),
                    incoming_rank=t.get("rank_at_time"),
                    incoming_org_name=org_name,
                    incoming_action=action,
                )
                if res.decision == "needs_review":
                    cid = make_claim_id(source_id, "disambiguation_conflict", pname, f"tenure:{pname}:{org_name}:{role_title}")
                    cur = conn.execute(
                        """INSERT OR IGNORE INTO claims_and_clues
                           (claim_id, source_id, claim_type, subject_raw_name, certainty, payload_json, evidence_quote, confidence, review_status)
                           VALUES (?, ?, 'disambiguation_conflict', ?, 'INFERRED', ?, ?, ?, 'needs_review')""",
                        (
                            cid,
                            source_id,
                            pname,
                            json.dumps({"entity_kind": "tenure", "incoming": t, "candidates": res.candidates}, ensure_ascii=False),
                            t.get("raw_role_text") or f"{pname} {org_name} {role_title}",
                            res.score,
                        ),
                    )
                    if cur.rowcount:
                        stats["claims_inserted"] += 1
                        stats["needs_review_count"] += 1
                    continue
                if res.decision == "create_new":
                    pid = make_person_id(pname, pbirth)
                    conn.execute(
                        """INSERT INTO persons (person_id, name, birth_ym, current_rank, credibility_lock)
                           VALUES (?, ?, ?, ?, ?)""",
                        (pid, pname, pbirth, t.get("rank_at_time") or "副省部级", source_tier),
                    )
                    stats["persons_inserted"] += 1
                else:
                    pid = str(res.person_id)

            org_id = resolve_or_create_org(
                conn,
                org_name,
                short_name=t.get("org_short_name"),
                org_kind=t.get("org_kind") or "other",
                admin_level=t.get("admin_level"),
                province_name=t.get("province_name"),
                parent_org_canonical_name=t.get("parent_org_canonical_name"),
            )

            if action == "CLOSE_SPAN":
                end_ym = _validate_ym(t.get("end_ym"), "tenures[].end_ym", required=True)
                cur = conn.execute(
                    """UPDATE tenures SET end_ym = ?, credibility_lock = MIN(credibility_lock, ?)
                       WHERE person_id = ? AND org_id = ? AND role_title = ? AND end_ym IS NULL
                         AND ? <= credibility_lock""",
                    (end_ym, source_tier, pid, org_id, role_title, source_tier),
                )
                stats["tenures_updated"] += cur.rowcount
                touched_persons.add(pid)
                continue

            start_ym = _validate_ym(t.get("start_ym"), "tenures[].start_ym", required=True)
            end_ym = _validate_ym(t.get("end_ym"), "tenures[].end_ym")
            certainty = str(t.get("certainty") or "FACT")
            if certainty not in ("FACT", "INFERRED"):
                certainty = "FACT"

            existing_t = conn.execute(
                """SELECT tenure_id, end_ym, credibility_lock, predecessor_name, successor_name
                   FROM tenures WHERE person_id = ? AND org_id = ? AND role_title = ? AND start_ym = ?""",
                (pid, org_id, role_title, start_ym),
            ).fetchone()

            if existing_t is None:
                tid = make_tenure_id(pid, org_id, role_title, start_ym)
                conn.execute(
                    """INSERT INTO tenures
                       (tenure_id, person_id, org_id, role_title, raw_role_text, role_tier, role_tier_weight,
                        rank_at_time, start_ym, end_ym, date_precision, is_concurrent, is_acting,
                        predecessor_name, successor_name, certainty, source_id, credibility_lock)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        tid,
                        pid,
                        org_id,
                        role_title,
                        t.get("raw_role_text"),
                        role_tier,
                        ROLE_TIER_WEIGHTS[role_tier],
                        t.get("rank_at_time"),
                        start_ym,
                        end_ym,
                        t.get("date_precision") or "MONTH",
                        int(bool(t.get("is_concurrent", 0))),
                        int(bool(t.get("is_acting", 0))),
                        t.get("predecessor_name"),
                        t.get("successor_name"),
                        certainty,
                        source_id,
                        source_tier,
                    ),
                )
                stats["tenures_inserted"] += 1
            else:
                if source_tier <= int(existing_t["credibility_lock"]):
                    new_end = end_ym if end_ym is not None else existing_t["end_ym"]
                    changed = (
                        new_end != existing_t["end_ym"]
                        or (t.get("predecessor_name") and t.get("predecessor_name") != existing_t["predecessor_name"])
                        or (t.get("successor_name") and t.get("successor_name") != existing_t["successor_name"])
                    )
                    if changed:
                        conn.execute(
                            """UPDATE tenures SET
                                 end_ym = ?,
                                 predecessor_name = COALESCE(?, predecessor_name),
                                 successor_name = COALESCE(?, successor_name),
                                 credibility_lock = MIN(credibility_lock, ?)
                               WHERE tenure_id = ?""",
                            (
                                new_end,
                                t.get("predecessor_name"),
                                t.get("successor_name"),
                                source_tier,
                                existing_t["tenure_id"],
                            ),
                        )
                        stats["tenures_updated"] += 1
                else:
                    if end_ym != existing_t["end_ym"]:
                        stats["credibility_lock_blocks"].append(
                            {
                                "target": "tenures.end_ym",
                                "tenure_id": existing_t["tenure_id"],
                                "existing_lock": existing_t["credibility_lock"],
                                "incoming_tier": source_tier,
                            }
                        )
            touched_persons.add(pid)
    else:
        # Tier 4 attempted writes to persons/tenures are strictly rejected & logged
        if bundle.get("persons") or bundle.get("tenures"):
            stats["credibility_lock_blocks"].append(
                {
                    "target": "tier4_main_tables",
                    "incoming_tier": 4,
                    "reason": "Tier 4 sources have zero write permission on persons/tenures",
                }
            )

    # Claims & Clues (allowed for all tiers 1..4; Tier 4 locked to SPECULATION/RUMOR)
    for cl in bundle.get("claims", []) or []:
        ctype = str(cl.get("claim_type", "")).strip()
        if ctype not in VALID_CLAIM_TYPES:
            raise CadreError(f"Invalid claim_type: {ctype!r}")
        subj_name = str(cl.get("subject_raw_name", "")).strip()
        rel_name = cl.get("related_raw_name")
        evidence_quote = str(cl.get("evidence_quote", "")).strip()
        if not evidence_quote:
            raise CadreError("claims[].evidence_quote is required")

        certainty = str(cl.get("certainty") or "SPECULATION")
        if source_tier == 4 and certainty not in ("SPECULATION", "RUMOR"):
            certainty = "SPECULATION"

        subj_pid = bundle_person_map.get((subj_name, cl.get("subject_birth_ym"))) or bundle_person_map.get((subj_name, None))
        review_status = "auto_merged"
        payload = dict(cl.get("payload") or {})

        if subj_pid is None:
            res = resolve_person(
                conn,
                name=subj_name,
                birth_ym=cl.get("subject_birth_ym"),
                incoming_rank=payload.get("rank_at_time"),
                incoming_org_name=payload.get("org_name"),
                allow_create=False,
            )
            if res.decision == "auto_merged":
                subj_pid = res.person_id
            elif res.decision == "needs_review":
                review_status = "needs_review"
                payload["candidates"] = res.candidates
                ctype = "disambiguation_conflict" if not payload.get("preserve_claim_type") else ctype

        rel_pid = None
        if rel_name:
            rel_name_s = str(rel_name).strip()
            rel_pid = bundle_person_map.get((rel_name_s, cl.get("related_birth_ym"))) or bundle_person_map.get((rel_name_s, None))
            if rel_pid is None:
                rres = resolve_person(conn, name=rel_name_s, birth_ym=cl.get("related_birth_ym"), allow_create=False)
                if rres.decision == "auto_merged":
                    rel_pid = rres.person_id

        cid = make_claim_id(source_id, ctype, subj_name, evidence_quote)
        vcodes = cl.get("violation_codes")
        vcodes_json = json.dumps(vcodes, ensure_ascii=False) if vcodes is not None else None
        cur = conn.execute(
            """INSERT OR IGNORE INTO claims_and_clues
               (claim_id, source_id, claim_type, event_date, subject_person_id, subject_raw_name,
                related_person_id, related_raw_name, certainty, violation_codes_json,
                payload_json, evidence_quote, confidence, review_status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                cid,
                source_id,
                ctype,
                cl.get("event_date"),
                subj_pid,
                subj_name,
                rel_pid,
                rel_name,
                certainty,
                vcodes_json,
                json.dumps(payload, ensure_ascii=False),
                evidence_quote,
                float(cl.get("confidence", 1.0)),
                review_status,
            ),
        )
        if cur.rowcount:
            stats["claims_inserted"] += 1
            if review_status == "needs_review":
                stats["needs_review_count"] += 1

    # Refresh FTS5 for all touched persons
    for pid in touched_persons:
        refresh_fts_person(conn, pid)

    conn.execute("UPDATE raw_sources SET ingest_status = 'ingested' WHERE source_id = ?", (source_id,))
    conn.commit()
    stats["touched_person_ids"] = sorted(touched_persons)
    stats["shockwave_trigger_person_ids"] = sorted(set(stats["shockwave_trigger_person_ids"]))
    return stats


def list_review_queue(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = conn.execute(
        """SELECT c.claim_id, c.source_id, c.claim_type, c.event_date, c.subject_raw_name,
                  c.related_raw_name, c.certainty, c.payload_json, c.evidence_quote,
                  c.confidence, c.created_at, s.source_name, s.credibility_tier
           FROM claims_and_clues c
           JOIN raw_sources s ON s.source_id = c.source_id
           WHERE c.review_status = 'needs_review'
           ORDER BY c.created_at ASC"""
    ).fetchall()
    return [
        {
            **{k: r[k] for k in r.keys() if k != "payload_json"},
            "payload": json.loads(r["payload_json"]),
        }
        for r in rows
    ]


def decide_review(
    conn: sqlite3.Connection,
    claim_id: str,
    action: str,
    *,
    person_id: str | None = None,
) -> dict[str, Any]:
    row = conn.execute(
        "SELECT * FROM claims_and_clues WHERE claim_id = ?", (claim_id,)
    ).fetchone()
    if row is None:
        raise CadreError(f"Review claim not found: {claim_id}")
    if action not in ("bind", "create", "reject"):
        raise CadreError(f"Invalid review action: {action!r}")

    now_iso = utc_now_iso()
    if action == "reject":
        conn.execute(
            "UPDATE claims_and_clues SET review_status = 'rejected', reviewed_at = ? WHERE claim_id = ?",
            (now_iso, claim_id),
        )
        conn.commit()
        return {"claim_id": claim_id, "action": "reject", "review_status": "rejected"}

    if action == "bind":
        if not person_id:
            raise CadreError("--person-id is required for action 'bind'")
        prow = conn.execute("SELECT person_id FROM persons WHERE person_id = ?", (person_id,)).fetchone()
        if prow is None:
            raise CadreError(f"Target person_id not found: {person_id}")
        target_pid = person_id
    else:
        payload = json.loads(row["payload_json"])
        incoming = payload.get("incoming") or {}
        target_pid = make_person_id(row["subject_raw_name"], incoming.get("birth_ym"), claim_id[:8])
        conn.execute(
            """INSERT INTO persons (person_id, name, birth_ym, current_rank, status)
               VALUES (?, ?, ?, ?, 'active')""",
            (target_pid, row["subject_raw_name"], incoming.get("birth_ym"), incoming.get("current_rank") or "其他"),
        )
        refresh_fts_person(conn, target_pid)

    conn.execute(
        """UPDATE claims_and_clues
           SET subject_person_id = ?, review_status = 'approved', reviewed_at = ?
           WHERE claim_id = ?""",
        (target_pid, now_iso, claim_id),
    )
    conn.commit()
    return {
        "claim_id": claim_id,
        "action": action,
        "person_id": target_pid,
        "review_status": "approved",
    }
