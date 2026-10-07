#!/usr/bin/env python3
"""Privacy-bounded local lookup for World Historian personal links.

This module is deliberately separate from the agent prompt boundary. It may
read explicitly configured observation exports locally, but its JSON output never
contains their statements, facts, names, or other raw personal material.
"""

from __future__ import annotations

import argparse
import os
import json
import re
import sqlite3
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(os.environ.get("PAP_ROOT", str(Path(__file__).resolve().parents[3])))
DEFAULT_DB = ROOT / "var/world-historian/chronicle.sqlite"
PERSONAL_INPUTS = tuple(Path(part).expanduser() for part in os.environ.get("PAP_PERSONAL_INPUTS", "").split(os.pathsep) if part)

_ASCII = re.compile(r"[A-Za-z][A-Za-z0-9._+-]{2,}")
_CJK = re.compile(r"[\u4e00-\u9fff]{4,}")
_STOP = {
    "the", "and", "with", "from", "that", "this", "for", "into", "record", "records",
    "recorded", "complete", "completed", "unknown", "source", "primary", "entry",
    "page", "view", "history", "account", "reported", "public", "private",
}


def _tokens(value: object) -> set[str]:
    """Return only substantial topic tokens; never return private text itself."""
    text = str(value).casefold()
    ascii_tokens = {item for item in _ASCII.findall(text) if item not in _STOP}
    # Long CJK spans are useful as exact topic markers; short common phrases are not.
    cjk_tokens = set(_CJK.findall(text))
    return ascii_tokens | cjk_tokens


def _flatten(value: object) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from _flatten(child)
    elif isinstance(value, list):
        for child in value:
            yield from _flatten(child)


def _time_bucket(observation: dict[str, Any]) -> str:
    raw = observation.get("time", {}).get("at")
    if not isinstance(raw, str):
        return "unknown"
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).strftime("%Y-%m")
    except ValueError:
        return "unknown"


def _relation(kind: str) -> str:
    if "view" in kind or "read" in kind or "browse" in kind or "visit" in kind:
        return "read_about"
    if "git_commit" in kind or "work" in kind or "project" in kind:
        return "worked_on"
    return "experienced"


def _observations(paths: Iterable[Path]) -> Iterable[dict[str, Any]]:
    for path in paths:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            raise ValueError(f"approved personal input is not a list: {path}")
        for item in data:
            if isinstance(item, dict) and isinstance(item.get("observation_id"), str):
                yield item


def _date(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


def lookup(*, db_path: Path = DEFAULT_DB, personal_paths: Iterable[Path] = PERSONAL_INPUTS,
           limit: int = 10) -> dict[str, list[dict[str, object]]]:
    """Find conservative, locally evidenced candidates without exposing private text.

    A match requires two substantial shared tokens. The output echoes only shared terms that
    already occur in the public event, so it cannot disclose a private topic.
    """
    if not 1 <= limit <= 10:
        raise ValueError("limit must be between 1 and 10")
    with sqlite3.connect(f"file:{db_path}?mode=ro", uri=True) as conn:
        events = conn.execute(
            """SELECT id, summary, occurred_at, observed_at, confidence
                 FROM events WHERE status IN ('active', 'confirmed')
                 ORDER BY COALESCE(occurred_at, observed_at) DESC LIMIT 30"""
        ).fetchall()
        existing = {
            (row[0], row[1], row[2])
            for row in conn.execute(
                "SELECT world_event_id, personal_event_id, relation_type FROM personal_links"
            )
        }

    result: list[dict[str, object]] = []
    for event_id, summary, occurred_at, observed_at, confidence in events:
        public_tokens = _tokens(summary)
        if not public_tokens:
            continue
        for observation in _observations(personal_paths):
            # Only the personal observation's local content participates in
            # matching.  Provenance/normalization metadata is not a topic.
            private_tokens = _tokens(" ".join(_flatten({
                "statement": observation.get("statement", ""),
                "facts": observation.get("facts", {}),
            })))
            shared = sorted(public_tokens & private_tokens)
            if len(shared) < 2:
                continue
            event_time = _date(occurred_at) or _date(observed_at)
            personal_time = _date(observation.get("time", {}).get("at"))
            if event_time and personal_time and abs((event_time - personal_time).days) > 30:
                continue
            kind = str(observation.get("kind", "unknown"))
            relation = _relation(kind)
            personal_id = str(observation["observation_id"])
            if (event_id, personal_id, relation) in existing:
                continue
            # These terms are selected from the public event, not copied from
            # the personal observation.  Keep the model context privacy-safe.
            public_terms = [term for term in shared if term in public_tokens][:3]
            score = min(0.85, 0.55 + 0.08 * len(shared) + 0.05 * float(confidence))
            result.append({
                "world_event_id": event_id,
                "personal_event_id": personal_id,
                "relation_type": relation,
                "confidence": round(score, 2),
                "personal_kind": kind,
                "personal_domain": str(observation.get("domain", "unknown")),
                "personal_time_bucket": _time_bucket(observation),
                "public_topic_terms": public_terms,
                "descriptor": "本地记录与该公开事件存在受控主题匹配；需按公开事件语境复核。",
                "evidence": [personal_id],
            })
            if len(result) >= limit:
                return {"candidates": result}
    return {"candidates": result}


def main() -> int:
    parser = argparse.ArgumentParser(description="privacy-bounded personal lookup")
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()
    print(json.dumps(lookup(limit=args.limit), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
