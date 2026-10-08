"""Export World Historian threads to the Obsidian vault.

Target: a locally configured Obsidian directory — one file per thread.
The Chronicle database stays the single source of truth: files
are projections, overwritten from the database on every sync. A file is
written only when the corresponding thread is created or modified in a
committed bundle (``touched_threads``); the caller decides when to sync.

Manual notes: readers may write personal annotations under the final
「手工批注」section; that section is carried over on re-sync. Thread renames
migrate the file (the old file is deleted only when its frontmatter
``thread_id`` matches, never a foreign file).

Re-sync is idempotent: when the rendered text differs from the file on disk
only in the ``updated:`` frontmatter line, the file is left alone (no mtime
bump, no git diff) and the path is reported under ``unchanged`` instead of
``written``. ``原文素材/<slug>.md`` follows the same rule.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

CLOSED_DIR = "closed_threads"
MANUAL_SECTION = "手工批注"
_INDEX_VERSION = 1


class SyncError(RuntimeError):
    """Raised when a thread file cannot be written."""


def _now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _real_home() -> Path:
    """True user home even when $HOME is redirected (sandbox, cron, daemons)."""
    try:
        import getpass
        import pwd

        return Path(pwd.getpwnam(getpass.getuser()).pw_dir)
    except Exception:
        return Path.home()


def vault_dir() -> Path | None:
    """Resolve the sync target directory; ``None`` disables syncing.

    The environment variable wins, including an empty value that disables
    export. Otherwise read the machine-local config beside this checkout.
    """
    env = os.environ.get("WORLD_HISTORIAN_VAULT_DIR")
    if env is not None:
        value = env.strip()
        return Path(value) if value else None
    config_path = Path(__file__).resolve().parents[3] / "var" / "config" / "world-historian.yaml"
    try:
        config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    if not isinstance(config, dict):
        return None
    value = config.get("vault_dir")
    if not isinstance(value, str) or not value.strip():
        return None
    path = Path(value.strip())
    return path if path.is_absolute() else None


_UNSAFE_CHARS = re.compile(r'[\\/:*?"<>|#\[\]^]+')
_WHITESPACE = re.compile(r"\s+")


def thread_filename(title: str, thread_id: str, taken: set[str]) -> str:
    """Deterministic filename for a thread, avoiding names used by others."""
    base = _UNSAFE_CHARS.sub("-", title or "").strip().strip(".")
    base = _WHITESPACE.sub(" ", base).strip()
    if not base:
        base = "untitled"
    base = base[:80].rstrip(" -")
    name = f"{base}.md"
    if name in taken:
        suffix = thread_id.rsplit("_", 1)[-1][:6] or thread_id[:6]
        name = f"{base}-{suffix}.md"
    return name


def _thread_relpath(snapshot: dict[str, Any], name: str) -> str:
    """Vault-relative thread file path; closed threads live in a subfolder."""
    if str(snapshot.get("status") or "active") == "closed":
        return f"{CLOSED_DIR}/{name}"
    return name


def _split_rel(rel: str) -> tuple[str, str]:
    """Split a vault-relative path into (directory key, filename)."""
    path = Path(str(rel))
    parent = str(path.parent)
    return ("" if parent == "." else parent), path.name


def _yaml_str(value: Any) -> str:
    return json.dumps("" if value is None else str(value), ensure_ascii=False)


def _one_line(value: Any) -> str:
    if value is None:
        return ""
    return _WHITESPACE.sub(" ", str(value)).strip()


_TAG_HASH = re.compile(r"(?<![\\#])#")  # 正文 # 会渲染为 Obsidian tag


def _escape_tags(value: Any) -> str:
    """Escape bare ``#`` so Obsidian does not parse body text as tags.

    Applies to database-sourced text (event summaries, claim statements,
    questions…) rendered into the note body. Leading ``#`` of markdown
    headings is written by render_snapshot itself and never passes through
    here, and ``\\#`` sequences already present are left untouched.
    """
    return _TAG_HASH.sub(r"\\#", str(value))


def _fmt(value: Any) -> str:
    return str(value) if value not in (None, "") else "—"


def _frontmatter(snapshot: dict[str, Any], synced_at: str) -> str:
    created = str(snapshot.get("created_at") or synced_at)[:10]
    lines = [
        "---",
        "type: note",
        "area: world-historian",
        f"thread_id: {_yaml_str(snapshot['id'])}",
        f"status: {_yaml_str(snapshot.get('status', 'active'))}",
        f"priority: {_yaml_str(snapshot.get('priority', 'normal'))}",
        f"last_event_ingested_at: {_yaml_str(snapshot.get('last_event_ingested_at'))}",
        f"created: {_yaml_str(created)}",
        f"updated: {_yaml_str(synced_at)}",
        "source: world-historian chronicle",
        "---",
        "",
    ]
    return "\n".join(lines)


def _load_evidence(raw: Any) -> list[Any]:
    if not raw:
        return []
    try:
        loaded = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return []
    return loaded if isinstance(loaded, list) else []


def _event_heading(event: dict[str, Any]) -> str:
    """Return a short event heading, never the full event body.

    Events written before ``events.title`` was introduced receive a stable,
    compact fallback.  This makes legacy projections readable without
    pretending a substring of their summary is a real editorial title.
    """
    title = _one_line(event.get("title"))
    if title:
        return _escape_tags(title)
    timestamp = event.get("occurred_at") or event.get("reported_at") or event.get("observed_at")
    date = str(timestamp)[:10] if timestamp else "日期未知"
    return f"{date} · 事件记录"


def _endpoint_label(endpoint_type: str, endpoint_id: str,
                    snapshot: dict[str, Any]) -> str:
    if endpoint_type == "thread":
        if endpoint_id == snapshot["id"]:
            return "本 Thread"
        return f"thread `{endpoint_id}`"
    for event in snapshot.get("events", []):
        if event["id"] == endpoint_id:
            return _event_heading(event)
    return f"event `{endpoint_id}`"


def render_snapshot(snapshot: dict[str, Any], synced_at: str,
                    manual_notes: str | None = None) -> str:
    """Render one thread snapshot (from ``db.thread_snapshot``) as Markdown."""
    tid = snapshot["id"]
    lines: list[str] = [_frontmatter(snapshot, synced_at), ""]

    lines.append(
        f"> [!info] 本文件由 World Historian 从 Chronicle 数据库自动生成并覆盖同步"
        f"（thread_id: `{tid}`）。机器生成部分请勿手工编辑；个人批注写在文末"
        f"「{MANUAL_SECTION}」一节，重新同步时会保留。\n"
    )

    lines.append(
        f"- **状态**：`{snapshot.get('status', 'active')}` · "
        f"**优先级**：`{snapshot.get('priority', 'normal')}`"
    )
    lines.append(
        f"- **最近检查**：{_fmt(snapshot.get('last_checked_at'))} · "
        f"**静默轮次**：{snapshot.get('quiet_count', 0)}"
    )
    if snapshot.get("seed_text"):
        lines.append(
            f"- **种子**：{_escape_tags(_one_line(snapshot['seed_text']))}"
            f"（{snapshot.get('seed_type', 'user_instruction')}）"
        )
    thread_entities = snapshot.get("thread_entities", [])
    if thread_entities:
        names = "、".join(
            f"{_one_line(e.get('name'))}（{e.get('kind', 'unknown')}）"
            for e in thread_entities
        )
        lines.append(f"- **实体**：{names}")
    lines.append("")

    current_state = snapshot.get("current_state")
    if current_state:
        lines.append("# 当前状态\n")
        lines.append(_escape_tags(str(current_state["body"])))
        lines.append("")
        lines.append(
            f"- **来源类型**：`{current_state['provenance']}` · "
            f"**更新**：{_fmt(current_state.get('updated_at'))}"
        )
        if current_state.get("revision"):
            lines.append(f"- **修订**：`{current_state['revision']}`")
        lines.append("")

    events = snapshot.get("events", [])
    labels = {e["id"]: _event_heading(e) for e in events}
    lines.append("# 时间线\n")
    if not events:
        lines.append("_（尚无事件）_\n")
    # Newest first (user decision 2026-09-14): the most recent event must be
    # the first thing visible when the note is opened. The Chronicle keeps its
    # canonical ascending order; only this projection reverses it.
    for event in reversed(events):
        lines.append(f"## {labels[event['id']]}")
        summary = str(event.get("summary") or "").strip()
        if summary:
            lines.append(_escape_tags(summary))
            lines.append("")
        lines.append("---")
        lines.append("")
        occurred = event.get("occurred_at")
        occurred_text = (
            f"未知（精度：{event.get('occurred_at_precision', 'unknown')}）"
            if occurred in (None, "")
            else str(occurred)
        )
        lines.append(
            f"- 发生时间：{occurred_text} ｜ "
            f"报道时间：{_fmt(event.get('reported_at'))} ｜ "
            f"首次观察：{_fmt(event.get('observed_at'))}"
        )
        lines.append(
            f"- 置信度 {float(event.get('confidence', 0.5)):.2f} · "
            f"状态 {event.get('status', 'active')}"
        )
        claims = event.get("claims", [])
        if claims:
            lines.append("- 来源主张：")
            for claim in claims:
                superseded = (
                    f"（被 `{claim['superseded_by']}` 取代）"
                    if claim.get("superseded_by") else ""
                )
                source = _one_line(claim.get("source_title")) or "佚名来源"
                publisher = _one_line(claim.get("source_publisher"))
                kind = claim.get("source_kind") or "unknown"
                origin = f"{source}（{publisher}，{kind}）" if publisher \
                    else f"{source}（{kind}）"
                lines.append(
                    f"  - 「{_escape_tags(_one_line(claim['statement']))}」—— {origin} · "
                    f"置信度 {float(claim.get('confidence', 0.5)):.2f} · "
                    f"{claim.get('status', 'active')}{superseded}"
                )
        event_entities = event.get("entities", [])
        if event_entities:
            names = "、".join(
                f"{_one_line(e.get('name'))}（{e.get('kind', 'unknown')}）"
                for e in event_entities
            )
            lines.append(f"- 涉及实体：{names}")
        quotes = event.get("quotes", [])
        for quote in quotes:
            speaker = _one_line(quote.get("speaker"))
            title = _one_line(quote.get("title"))
            url = quote.get("url")
            slug = _one_line(quote.get("slug")) or None
            header_parts = [p for p in (speaker, f"《{title}》" if title else None) if p]
            header = "　".join(header_parts) if header_parts else "原文"
            if slug:
                # Verbatim material lives in 原文素材/; link, don't inline.
                origin = f"[[原文素材/{slug}|📄 {header}（原文素材）]]"
                if url:
                    origin += f" · [网页存档]({url})"
                lines.append(f"> [!quote] {header}")
                lines.append(f"> 来源：{origin}")
                summary = str(quote.get("summary") or "").strip()
                if summary:
                    lines.append(f"> **摘要**：{_escape_tags(_one_line(summary))}")
                else:
                    # Legacy standalone materials predate quote summaries.
                    # Preserve their compact preview until they are explicitly
                    # backfilled; new slugged quotes are required to carry a
                    # summary by store_bundle.
                    preview = [
                        ln for ln in str(quote.get("quote_text", "")).splitlines()
                        if ln.strip()
                    ]
                    if preview:
                        lines.append(f"> {_one_line(preview[0])[:160]}…")
            else:
                source = _one_line(quote.get("source_title")) or "佚名来源"
                origin = f"{header} —— {source}"
                if url:
                    origin += f"（[原文链接]({url})）"
                lines.append(f"> [!quote] {header}")
                lines.append(f"> 来源：{origin}")
                lines.append(">")
                for raw_line in str(quote.get("quote_text", "")).splitlines() or [""]:
                    lines.append(f"> {raw_line}" if raw_line.strip() else ">")
        lines.append("")

    questions = snapshot.get("questions", [])
    lines.append("# 开放问题\n")
    if not questions:
        lines.append("_（无）_\n")
    for question in questions:
        status = question.get("status", "open")
        if status == "open":
            lines.append(f"- [ ] {_escape_tags(_one_line(question['question']))}")
        else:
            marker = "x" if status == "answered" else " "
            answer = (
                f" → event `{question['answer_event_id']}`"
                if question.get("answer_event_id") else ""
            )
            lines.append(
                f"- [{marker}] {_escape_tags(_one_line(question['question']))}{answer}"
                f"（{status}）"
            )
    lines.append("")

    queries = [q for q in snapshot.get("watch_queries", []) if q.get("active")]
    lines.append("# 监视查询\n")
    if not queries:
        lines.append("_（无）_\n")
    for query in queries:
        lines.append(f"- `{_one_line(query['query'])}`（{query.get('query_kind', 'exact')}）")
    lines.append("")

    relations = snapshot.get("relations", [])
    lines.append("# 关联\n")
    if not relations:
        lines.append("_（无）_\n")
    for relation in relations:
        src = _endpoint_label(relation.get("src_type", "event"),
                              relation["src_id"], snapshot)
        dst = _endpoint_label(relation.get("dst_type", "event"),
                              relation["dst_id"], snapshot)
        evidence = _load_evidence(relation.get("evidence_json"))
        evidence_note = f" · 证据 {len(evidence)} 条" if evidence else ""
        lines.append(
            f"- {src} —**{relation['relation_type']}**→ {dst} · "
            f"置信度 {float(relation.get('confidence', 0.5)):.2f} · "
            f"{relation.get('status', 'active')}{evidence_note}"
        )
    lines.append("")

    interpretations = snapshot.get("interpretations", [])
    lines.append("# 后见解释（Interpretation）\n")
    if not interpretations:
        lines.append("_（无）_\n")
    for item in interpretations:
        earlier = _endpoint_label("event", item["earlier_event_id"], snapshot)
        later = _endpoint_label("event", item["later_event_id"], snapshot)
        lines.append(
            f"- 「{_escape_tags(_one_line(item['statement']))}」"
            f"（{earlier} → {later}）· 置信度 {float(item.get('confidence', 0.5)):.2f} · "
            f"{item.get('status', 'active')}"
        )
    lines.append("")

    lines.append(f"# {MANUAL_SECTION}\n")
    lines.append((manual_notes or "（无）").rstrip())
    lines.append("")
    return "\n".join(lines)


def extract_manual_notes(text: str) -> str | None:
    """Return the reader's「手工批注」body, or ``None`` when absent.

    Old projections used a level-2 section heading while current ones use
    level 1.  A reader can also use deeper headings inside the annotation, so
    the section ends only at a heading at the same or a higher level.
    """
    match = re.search(
        rf"^(?P<level>#{{1,6}})[ \t]+{re.escape(MANUAL_SECTION)}[ \t]*$",
        text,
        flags=re.M,
    )
    if match is None:
        return None
    rest = text[match.end():]
    level = len(match.group("level"))
    following = next(
        (heading for heading in re.finditer(r"^(#{1,6})(?:[ \t]+|$)", rest, re.M)
         if len(heading.group(1)) <= level),
        None,
    )
    body = rest[:following.start()] if following is not None else rest
    body = body.strip()
    return None if body in {"", "（无）", "_（无）_"} else body


def _git_committed_manual_notes(path: Path, marker: str) -> str | None:
    """Last committed「手工批注」body for ``path``, or None.

    Looks through recent commits of the file and returns the first (most
    recent) version whose manual-notes section has real content. Used as a
    recovery fallback when the working-tree copy has lost its annotations.
    """
    vault_root = path.parents[2]  # vault/<area-dir>/file -> vault root
    try:
        relative_path = path.relative_to(vault_root)
    except ValueError:
        return None
    try:
        log = subprocess.run(
            ["git", "-C", str(vault_root), "log", "--all",
             "--format=%h", "--", str(relative_path)],
            capture_output=True, text=True, timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if log.returncode != 0:
        return None
    for commit in log.stdout.split():
        try:
            show = subprocess.run(
                ["git", "-C", str(vault_root), "show",
                 f"{commit}:{relative_path}"],
                capture_output=True, text=True, timeout=10,
            )
        except (OSError, subprocess.SubprocessError):
            continue
        if show.returncode != 0 or marker not in show.stdout:
            continue
        notes = extract_manual_notes(show.stdout)
        if notes and notes != "（无）":
            return notes
    return None


def _atomic_write(path: Path, text: str) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


_UPDATED_LINE = re.compile(r"^updated: .*$", re.MULTILINE)
_UPDATED_PLACEHOLDER = "updated: <ignored>"


def _normalize_updated(text: str) -> str:
    """Blank the frontmatter ``updated:`` value so two renders can be compared.

    Exactly the first ``updated:`` line is replaced (``count=1``); every other
    byte, including body text that merely mentions the word, is kept verbatim.
    """
    return _UPDATED_LINE.sub(_UPDATED_PLACEHOLDER, text, count=1)


def _write_if_changed(path: Path, text: str) -> bool:
    """Write ``text`` unless the file already holds it, ignoring ``updated:``.

    Returns ``True`` when the file was (re)written. An unchanged file is left
    untouched so a re-render that only moves the ``updated:`` timestamp does
    not bump the mtime or create a git diff.
    """
    if path.exists():
        try:
            existing = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            existing = None
        if existing is not None and \
                _normalize_updated(existing) == _normalize_updated(text):
            return False
    _atomic_write(path, text)
    return True


def _load_index(index_path: Path) -> dict[str, Any]:
    if not index_path.exists():
        return {"version": _INDEX_VERSION, "threads": {}}
    try:
        loaded = json.loads(index_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"version": _INDEX_VERSION, "threads": {}}
    if not isinstance(loaded, dict) or not isinstance(loaded.get("threads"), dict):
        return {"version": _INDEX_VERSION, "threads": {}}
    loaded.setdefault("version", _INDEX_VERSION)
    return loaded


def _thread_id_marker(thread_id: str) -> str:
    return f"thread_id: {_yaml_str(thread_id)}"


def sync_threads(
    snapshots: list[dict[str, Any]],
    vault: Path,
    index_path: Path,
    *,
    synced_at: str | None = None,
) -> dict[str, list[str]]:
    """Write/refresh one Obsidian file per snapshot. Never raises."""
    synced_at = synced_at or _now()
    outcome: dict[str, list[str]] = {
        "written": [], "removed": [], "errors": [], "unchanged": []}
    if not snapshots:
        return outcome
    index = _load_index(index_path)
    threads = index["threads"]
    # Index values are vault-relative paths ("name.md" or
    # "closed_threads/name.md"); track used names per directory.
    taken: dict[str, set[str]] = {}
    for rel in threads.values():
        rel_dir, rel_name = _split_rel(rel)
        taken.setdefault(rel_dir, set()).add(rel_name)

    try:
        vault.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        outcome["errors"].append(f"vault unavailable: {exc}")
        return outcome

    dirty = False
    for snapshot in snapshots:
        tid = str(snapshot["id"])
        try:
            materials_dir = vault / "原文素材"
            for snapshot_quote in [
                q for event in snapshot.get("events", [])
                for q in event.get("quotes", [])
            ]:
                slug = str(snapshot_quote.get("slug") or "").strip()
                if not slug:
                    continue
                materials_dir.mkdir(parents=True, exist_ok=True)
                mat_path = materials_dir / f"{slug}.md"
                mat_lines = [
                    "---",
                    "type: source-material",
                    "area: world-historian",
                    f"thread_id: {_yaml_str(tid)}",
                    f"event_id: {_yaml_str(snapshot_quote.get('event_id'))}",
                    f"speaker: {_yaml_str(snapshot_quote.get('speaker'))}",
                    f"title: {_yaml_str(snapshot_quote.get('title'))}",
                    f"source_title: {_yaml_str(snapshot_quote.get('source_title'))}",
                    f"url: {_yaml_str(snapshot_quote.get('url'))}",
                    f"fetched_at: {_yaml_str(snapshot_quote.get('fetched_at'))}",
                    f"updated: {_yaml_str(synced_at)}",
                    "---",
                    "",
                    f"# {snapshot_quote.get('speaker') or ''}"
                    f"《{snapshot_quote.get('title') or ''}》".replace("《》", ""),
                    "",
                    str(snapshot_quote.get("quote_text") or "").rstrip(),
                    "",
                ]
                if not _write_if_changed(mat_path, "\n".join(mat_lines)):
                    outcome["unchanged"].append(str(mat_path))
            previous = str(threads.get(tid) or "")
            prev_dir, prev_name = _split_rel(previous) if previous else ("", "")
            dir_key = (CLOSED_DIR
                       if str(snapshot.get("status") or "active") == "closed" else "")
            names = taken.setdefault(dir_key, set())
            # A thread's own previous filename is not a collision.
            others = names - ({prev_name}
                              if prev_name and prev_dir == dir_key else set())
            name = thread_filename(str(snapshot.get("title") or "untitled"),
                                   tid, others)
            names.add(name)
            if prev_name and prev_dir != dir_key:
                taken.get(prev_dir, set()).discard(prev_name)
            elif prev_name:
                names.discard(prev_name)
            rel = _thread_relpath(snapshot, name)
            target = vault / rel
            marker = _thread_id_marker(tid)
            previous_path = (vault / previous) if previous else None
            source_path = target if target.exists() else (
                previous_path
                if previous_path is not None and previous_path.exists() else target)
            existing = (source_path.read_text(encoding="utf-8")
                        if source_path.exists() else None)
            notes = None
            if existing is not None and marker in existing:
                notes = extract_manual_notes(existing)
            if (notes is None or notes == "（无）") and existing is not None:
                # The on-disk file lost its annotations (typical cause: a
                # remotely-save conflict resolution pulled an older remote
                # version over the local one). Fall back to the last git
                # commit of this file before rendering, so reader notes are
                # never silently dropped by a sync race.
                git_notes = _git_committed_manual_notes(source_path, marker)
                if git_notes:
                    notes = git_notes
                    outcome["errors"].append(
                        f"{tid}: manual notes missing on disk; recovered from git "
                        f"(possible remotely-save revert) — please verify"
                    )
            target.parent.mkdir(parents=True, exist_ok=True)
            if _write_if_changed(target, render_snapshot(snapshot, synced_at, notes)):
                outcome["written"].append(str(target))
            else:
                outcome["unchanged"].append(str(target))

            if previous and previous != rel:
                old_path = vault / previous
                if old_path.exists():
                    old_text = old_path.read_text(encoding="utf-8")
                    if marker in old_text:  # never delete a foreign file
                        old_path.unlink()
                        outcome["removed"].append(str(old_path))
            if previous != rel:
                threads[tid] = rel
                dirty = True
        except OSError as exc:
            outcome["errors"].append(f"{tid}: {exc}")

    if dirty:
        try:
            _atomic_write(index_path,
                          json.dumps(index, ensure_ascii=False, indent=2, sort_keys=True))
        except OSError as exc:
            outcome["errors"].append(f"index write: {exc}")
    return outcome
