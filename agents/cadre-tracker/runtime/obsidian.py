"""On-demand Obsidian Markdown projector with idempotent anchor replacement & Mermaid graphs (Section 9.3)."""

from __future__ import annotations

import os
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from .db import FALLEN_STATUSES, _resolve_person_row, query_shockwave
except ImportError:
    from db import FALLEN_STATUSES, _resolve_person_row, query_shockwave  # type: ignore[no-redef]

ANCHOR_START = "<!-- PAP:CADRE_GRAPH:START -->"
ANCHOR_END = "<!-- PAP:CADRE_GRAPH:END -->"
_UNSAFE_FILENAME = re.compile(r'[\\/:*?"<>|#\[\]^]+')


def resolve_vault_dir(override: Path | str | None = None) -> Path | None:
    if override is not None:
        val = str(override).strip()
        return Path(val) if val else None
    for env_key in ("OBSIDIAN_VAULT", "PAP_VAULT"):
        val = os.environ.get(env_key, "").strip()
        if val:
            return Path(val)
    return None


def _safe_filename(name: str) -> str:
    cleaned = _UNSAFE_FILENAME.sub("-", name.strip()).strip(".")
    return cleaned or "unnamed"


def _mermaid_node_id(person_id: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]", "_", person_id)


def _mermaid_label(text: str) -> str:
    return text.replace('"', "'").replace("\n", " ")


def render_person_graph_block(
    conn: sqlite3.Connection,
    person_row: sqlite3.Row,
    shockwave: dict[str, Any],
) -> str:
    pid = person_row["person_id"]
    tenures = conn.execute(
        """SELECT t.start_ym, t.end_ym, o.canonical_name, t.role_title, t.role_tier, t.is_concurrent
           FROM tenures t
           JOIN organizations o ON o.org_id = t.org_id
           WHERE t.person_id = ?
           ORDER BY t.start_ym DESC""",
        (pid,),
    ).fetchall()
    edus = conn.execute(
        """SELECT e.start_ym, e.end_ym, o.canonical_name, e.department, e.degree, e.major
           FROM education_records e
           JOIN organizations o ON o.org_id = e.school_org_id
           WHERE e.person_id = ?
           ORDER BY COALESCE(e.start_ym, '') DESC""",
        (pid,),
    ).fetchall()

    lines: list[str] = [
        ANCHOR_START,
        f"## 官员档案：{person_row['name']}",
        "",
        f"- **人物 ID**：`{pid}`",
        f"- **当前状态**：`{person_row['status']}` | **级别**：{person_row['current_rank']}",
        f"- **出生年月**：{person_row['birth_ym'] or '未知'} | **籍贯**：{person_row['native_place'] or '未知'}",
        "",
        "### 时态履历切片",
        "",
        "| 起止年月 | 机构 | 职务 | 层级 | 兼职 |",
        "| --- | --- | --- | --- | --- |",
    ]
    for t in tenures:
        span = f"{t['start_ym']} ~ {t['end_ym'] or '至今'}"
        conc = "是" if t["is_concurrent"] else "否"
        lines.append(f"| {span} | {t['canonical_name']} | {t['role_title']} | {t['role_tier']} | {conc} |")

    if edus:
        lines.extend(["", "### 学缘与党校经历", ""])
        for e in edus:
            span = f"{e['start_ym'] or '?'} ~ {e['end_ym'] or '?'}"
            detail = " ".join(x for x in (e["canonical_name"], e["department"], e["degree"], e["major"]) if x)
            lines.append(f"- `{span}` {detail}")

    # Mermaid relationship graph
    lines.extend(["", "### 关联震荡波图谱", "", "```mermaid", "flowchart LR"])
    subj_node = _mermaid_node_id(pid)
    subj_label = _mermaid_label(f"{person_row['name']} ({person_row['status']})")
    lines.append(f'    {subj_node}["{subj_label}"]')

    styled_fallen: list[str] = []
    styled_anomaly: list[str] = []
    if person_row["status"] in FALLEN_STATUSES:
        styled_fallen.append(subj_node)
    elif person_row["status"] == "anomaly_watch":
        styled_anomaly.append(subj_node)

    associates = (shockwave.get("already_fallen_associates") or [])[:8] + (
        shockwave.get("active_watch_list") or []
    )[:8]
    for assoc in associates:
        anode = _mermaid_node_id(assoc["person_id"])
        alabel = _mermaid_label(f"{assoc['name']} ({assoc['status']})")
        ci = assoc["closeness_index"]
        months = assoc["total_unique_overlap_months"]
        edge_label = _mermaid_label(f"CI {ci} / {months}m")
        lines.append(f'    {subj_node} ---|"{edge_label}"| {anode}["{alabel}"]')
        if assoc["status"] in FALLEN_STATUSES:
            styled_fallen.append(anode)
        elif assoc["status"] == "anomaly_watch":
            styled_anomaly.append(anode)

    for node in dict.fromkeys(styled_fallen):
        lines.append(f"    style {node} fill:#ef4444,color:#ffffff,stroke:#991b1b")
    for node in dict.fromkeys(styled_anomaly):
        lines.append(f"    style {node} fill:#f59e0b,color:#ffffff,stroke:#b45309")

    lines.extend(["```", ANCHOR_END])
    return "\n".join(lines)


def _replace_anchor_block(existing_text: str, new_block: str) -> str:
    pattern = re.compile(
        re.escape(ANCHOR_START) + r".*?" + re.escape(ANCHOR_END),
        flags=re.DOTALL,
    )
    if pattern.search(existing_text):
        return pattern.sub(new_block, existing_text, count=1)
    sep = "\n\n" if existing_text.endswith("\n") else "\n\n"
    return existing_text + sep + new_block + "\n"


def project_person_note(
    conn: sqlite3.Connection,
    person: str,
    *,
    vault_dir: Path | str | None = None,
    top_k: int = 15,
) -> dict[str, Any]:
    """Write or idempotently update ${VAULT}/Cadre-Graph/People/<姓名>.md preserving manual notes."""
    vault = resolve_vault_dir(vault_dir)
    if vault is None:
        return {"skipped": True, "reason": "OBSIDIAN_VAULT / PAP_VAULT not configured"}

    prow = _resolve_person_row(conn, person)
    sw = query_shockwave(conn, prow["person_id"], top_k=top_k)
    block = render_person_graph_block(conn, prow, sw)

    people_dir = vault / "Cadre-Graph" / "People"
    people_dir.mkdir(parents=True, exist_ok=True)
    target_path = people_dir / f"{_safe_filename(prow['name'])}.md"

    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if target_path.is_file():
        old_text = target_path.read_text(encoding="utf-8")
        new_text = _replace_anchor_block(old_text, block)
        changed = new_text != old_text
        if changed:
            target_path.write_text(new_text, encoding="utf-8")
        return {
            "skipped": False,
            "path": str(target_path),
            "person_id": prow["person_id"],
            "updated": changed,
        }

    frontmatter = "\n".join(
        [
            "---",
            f"person_id: {prow['person_id']}",
            f"name: {prow['name']}",
            f"status: {prow['status']}",
            f"current_rank: {prow['current_rank']}",
            f"updated_at: {now_str}",
            "tags: [cadre-graph, person]",
            "---",
            "",
        ]
    )
    footer = "\n\n## 个人研判笔记\n\n<!-- 此区域由用户维护，系统刷新时永不覆盖 -->\n"
    target_path.write_text(frontmatter + block + footer, encoding="utf-8")
    return {
        "skipped": False,
        "path": str(target_path),
        "person_id": prow["person_id"],
        "updated": True,
    }


def write_shockwave_brief(
    conn: sqlite3.Connection,
    person: str,
    event_title: str,
    *,
    vault_dir: Path | str | None = None,
    event_date: str | None = None,
    top_k: int = 20,
) -> dict[str, Any]:
    """Write ${VAULT}/Cadre-Graph/Briefs/YYYY-MM-DD-<事件简题>.md."""
    vault = resolve_vault_dir(vault_dir)
    if vault is None:
        return {"skipped": True, "reason": "OBSIDIAN_VAULT / PAP_VAULT not configured"}

    prow = _resolve_person_row(conn, person)
    sw = query_shockwave(conn, prow["person_id"], top_k=top_k)
    day = event_date or datetime.now(timezone.utc).strftime("%Y-%m-%d")

    briefs_dir = vault / "Cadre-Graph" / "Briefs"
    briefs_dir.mkdir(parents=True, exist_ok=True)
    target_path = briefs_dir / f"{day}-{_safe_filename(event_title)}.md"

    lines = [
        "---",
        f"date: {day}",
        f"subject_person_id: {prow['person_id']}",
        f"subject_name: {prow['name']}",
        f"subject_status: {prow['status']}",
        "tags: [cadre-graph, shockwave-brief]",
        "---",
        "",
        f"# 【政经人事异动与关联快报】{event_title}",
        "",
        f"- **涉事官员**：[[{prow['name']}]]（`{prow['status']}`，{prow['current_rank']}）",
        "",
        "## 一、历史已爆雷关联人（反向溯源）",
        "",
    ]
    if sw["already_fallen_associates"]:
        lines.append("| 姓名 | 状态 | 紧密度指数 (CI) | 共事月数 | 学缘关系 |")
        lines.append("| --- | --- | --- | --- | --- |")
        for item in sw["already_fallen_associates"]:
            edu = "、".join(item["edu_relations"]) or "-"
            lines.append(
                f"| [[{item['name']}]] | `{item['status']}` | {item['closeness_index']} | {item['total_unique_overlap_months']} | {edu} |"
            )
    else:
        lines.append("暂无库内已落马高关联人员。")

    lines.extend(["", "## 二、现役高危观察名单（前瞻预警）", ""])
    lines.append("> 注：客观共事、上下级辖属与学缘交集仅反映历史履历相关性，不构成涉案结论。")
    lines.append("")
    if sw["active_watch_list"]:
        lines.append("| 姓名 | 级别 | 紧密度指数 (CI) | 共事月数 | 学缘关系 |")
        lines.append("| --- | --- | --- | --- | --- |")
        for item in sw["active_watch_list"]:
            edu = "、".join(item["edu_relations"]) or "-"
            lines.append(
                f"| [[{item['name']}]] | {item['current_rank']} | {item['closeness_index']} | {item['total_unique_overlap_months']} | {edu} |"
            )
    else:
        lines.append("暂无库内现役高关联人员。")

    target_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"skipped": False, "path": str(target_path), "person_id": prow["person_id"]}
