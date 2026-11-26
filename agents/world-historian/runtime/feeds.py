"""Deterministic RSS/Atom ingestion for World Historian.

Fetches configured ``kind: rss`` sources from ``profile/config.yaml`` and
stores every entry as a row in the ``sources`` table with a stable ID
consistent with ``store_bundle`` (same URL + published time + content hash
collapses to the same ID, so re-fetching is idempotent; a revised article
with a different hash becomes a new source row rather than overwriting).

Standard library only: ``urllib`` + ``xml.etree``. A feed failure never
aborts the other feeds.
"""

from __future__ import annotations

import email.utils
import hashlib
import json
import os
import sqlite3
import sys
import urllib.request
import urllib.parse
from contextlib import nullcontext
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from xml.etree import ElementTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
from db import ChronicleError, _now, repo_root, stable_id

try:
    from paplog import observe as paplog
except ImportError:  # Standalone maintenance use remains dependency-free.
    class _NoopPaplog:
        @staticmethod
        def http(*_args: Any, **_kwargs: Any): return nullcontext()
        @staticmethod
        def database(*_args: Any, **_kwargs: Any): return nullcontext()
    paplog = _NoopPaplog()


def _observed() -> bool:
    """Avoid creating a default ledger for standalone/library use."""
    return bool(os.environ.get("PAP_RUN_ID") or os.environ.get("PAP_OBSERVABILITY_DIR"))

DEFAULT_USER_AGENT = "world-historian-feed-fetcher/0.1 (+pap personal-agent-platform)"
DEFAULT_TIMEOUT = 20

_ATOM_NS = "{http://www.w3.org/2005/Atom}"


def _local(tag: str) -> str:
    """Strip any XML namespace from a tag name."""
    return tag.rsplit("}", 1)[-1]


def _text(element: ElementTree.Element | None) -> str:
    if element is None or element.text is None:
        return ""
    return element.text.strip()


def _parse_time(value: str) -> str | None:
    """Parse RFC-822 / ISO-8601 timestamps; return ISO text or ``None``."""
    value = (value or "").strip()
    if not value:
        return None
    try:
        parsed = email.utils.parsedate_to_datetime(value)
    except (TypeError, ValueError):
        pass
    else:
        if parsed is not None:
            return parsed.astimezone().isoformat(timespec="seconds")
    for candidate in (value, value.replace("Z", "+00:00")):
        try:
            parsed = datetime.fromisoformat(candidate)
        except ValueError:
            continue
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone().isoformat(timespec="seconds")
    return None


def _content_hash(title: str, url: str, published: str | None) -> str:
    material = "\x1f".join((title.strip(), url.strip(), (published or "").strip()))
    return hashlib.sha256(material.encode("utf-8")).hexdigest()[:20]


def parse_feed(xml_text: str) -> list[dict[str, Any]]:
    """Parse RSS 2.0 or Atom XML into entry dicts: title/link/published/summary."""
    root = ElementTree.fromstring(xml_text)
    tag = _local(root.tag)
    entries: list[dict[str, Any]] = []

    if tag == "rss":
        channel = root.find("channel")
        if channel is None:
            return entries
        for item in channel.findall("item"):
            link = _text(item.find("link"))
            if not link:
                continue
            entries.append({
                "title": _text(item.find("title")),
                "link": link,
                "published": _parse_time(_text(item.find("pubDate"))),
                "summary": _text(item.find("description")),
            })

    elif tag == "feed":
        for entry in root.findall(f"{_ATOM_NS}entry"):
            link = ""
            raw_link = entry.find(f"{_ATOM_NS}link")
            if raw_link is not None:
                link = raw_link.get("href", "")
            if not link:
                continue
            entries.append({
                "title": _text(entry.find(f"{_ATOM_NS}title")),
                "link": link,
                "published": _parse_time(
                    _text(entry.find(f"{_ATOM_NS}published"))
                    or _text(entry.find(f"{_ATOM_NS}updated"))
                ),
                "summary": _text(entry.find(f"{_ATOM_NS}summary"))
                or _text(entry.find(f"{_ATOM_NS}content")),
            })

    return entries


def fetch_feed(url: str, *, timeout: int = DEFAULT_TIMEOUT) -> str:
    """Fetch a feed URL as UTF-8 text. Raises on network/HTTP errors."""
    request = urllib.request.Request(url, headers={"User-Agent": DEFAULT_USER_AGENT})
    # A configured feed is a real network boundary.  Deliberately omit query
    # parameters from the resource identity so a feed URL cannot leak a token.
    parsed = urllib.parse.urlsplit(url)
    safe_endpoint = urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))
    with (paplog.http(safe_endpoint, effect="execute", attributes={"http.method": "GET", "feed.fetch": True})
          if _observed() else nullcontext()):
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read()
    return raw.decode("utf-8", errors="replace")


def ingest_feed(
    conn: sqlite3.Connection,
    *,
    feed_name: str,
    feed_url: str,
    fetch: Callable[[str], str] = fetch_feed,
    max_entries: int = 30,
) -> dict[str, Any]:
    """Fetch one feed and insert unseen entries into ``sources``.

    Returns ``{"source", "fetched", "added", "error"}``; network or parse
    problems are reported in ``error`` and never raise.
    """
    try:
        xml_text = fetch(feed_url)
        entries = parse_feed(xml_text)
    except Exception as exc:  # noqa: BLE001 — one bad feed must not kill the run
        return {"source": feed_name, "fetched": 0, "added": 0,
                "error": f"{type(exc).__name__}: {exc}"}

    now = _now()
    added = 0
    try:
        with (paplog.database("world-historian.sources", effect="write",
                              attributes={"feed.name": feed_name, "candidate_count": min(len(entries), max_entries)})
              if _observed() else nullcontext()):
            for entry in entries[:max_entries]:
                url = entry["link"]
                title = entry["title"]
                published = entry["published"]
                content_hash = _content_hash(title, url, published)
                identifier = stable_id("src", url, published, content_hash)
                row = conn.execute(
                    "SELECT 1 FROM sources WHERE id = ?", (identifier,)
                ).fetchone()
                if row is not None:
                    continue
                conn.execute(
                    """INSERT INTO sources
                       (id, canonical_url, title, publisher, source_kind, published_at,
                        updated_at, fetched_at, content_hash, metadata_json, created_at)
                       VALUES (?, ?, ?, ?, 'rss', ?, ?, ?, ?, ?, ?)""",
                    (identifier, url, title, feed_name, published, published, now,
                     content_hash, json.dumps({
                         "feed": feed_name, "feed_url": feed_url,
                         "summary": entry["summary"][:2000],
                     }, ensure_ascii=False), now),
                )
                added += 1
            conn.commit()
    except sqlite3.Error as exc:
        # A database-side failure for one feed (e.g. "database is locked" from
        # a concurrent store-bundle writer) is this feed's error; it must not
        # abort the other feeds or the whole run. Nothing was committed.
        try:
            conn.rollback()
        except sqlite3.Error:
            pass
        return {"source": feed_name, "fetched": len(entries), "added": 0,
                "error": f"{type(exc).__name__}: {exc}"}
    return {"source": feed_name, "fetched": len(entries), "added": added,
            "error": None}


def configured_rss_sources(config_path: Path | None = None) -> list[dict[str, str]]:
    """Read ``kind: rss`` sources from ``profile/config.yaml``."""
    try:
        import yaml
    except ImportError as exc:
        # Returning [] here made the hourly feeds job "succeed" forever while
        # ingesting nothing on interpreters without PyYAML. Fail loudly instead.
        raise ChronicleError(
            "PyYAML is required for feeds ingestion; run this command with the "
            "repository .venv interpreter (make setup)"
        ) from exc
    path = Path(config_path or repo_root() / "agents/world-historian/profile/config.yaml")
    try:
        loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except OSError as exc:
        raise ChronicleError(f"feed config is unreadable: {path}: {exc}") from exc
    except yaml.YAMLError as exc:
        raise ChronicleError(f"feed config is not valid YAML: {path}: {exc}") from exc
    sources = list(loaded.get("sources", []) or [])
    # Machine-local watchlist (gitignored): personal/regional feeds live outside
    # the reusable repo config. Merged by URL, profile config wins on conflicts.
    local_path = repo_root() / "var" / "config" / "world-historian-sources.yaml"
    if local_path.is_file():
        try:
            local = yaml.safe_load(local_path.read_text(encoding="utf-8")) or {}
        except OSError as exc:
            raise ChronicleError(f"local feed config is unreadable: {local_path}: {exc}") from exc
        except yaml.YAMLError as exc:
            raise ChronicleError(f"local feed config is not valid YAML: {local_path}: {exc}") from exc
        sources.extend(local.get("sources", []) or [])
    seen: set[str] = set()
    merged: list[dict[str, str]] = []
    for source in sources:
        if not (isinstance(source, dict) and source.get("kind") == "rss"
                and source.get("url")):
            continue
        url = str(source["url"])
        if url in seen:
            continue
        seen.add(url)
        merged.append(source)
    return merged


def ingest_all(conn: sqlite3.Connection, *, max_entries: int = 30,
               config_path: Path | None = None) -> dict[str, Any]:
    """Fetch every configured RSS source; failures are collected, not fatal."""
    results = [ingest_feed(conn, feed_name=s["name"], feed_url=s["url"],
                           max_entries=max_entries)
               for s in configured_rss_sources(config_path)]
    added = sum(r["added"] for r in results)
    errors = [r for r in results if r.get("error")]
    return {"sources_checked": len(results), "entries_added": added,
            "results": results, "errors": errors}


def recent_sources(conn: sqlite3.Connection, *, hours: int = 24,
                   limit: int = 50) -> list[dict[str, Any]]:
    """RSS-ingested sources fetched within the last ``hours``, newest first."""
    rows = conn.execute(
        """SELECT * FROM sources WHERE source_kind = 'rss'
           ORDER BY fetched_at DESC, published_at DESC LIMIT 400"""
    ).fetchall()
    now = datetime.now(timezone.utc).astimezone()
    cutoff = now.timestamp() - hours * 3600
    out: list[dict[str, Any]] = []
    for row in rows:
        try:
            fetched = datetime.fromisoformat(str(row["fetched_at"]))
        except ValueError:
            continue
        if fetched.timestamp() < cutoff:
            continue
        out.append(dict(row))
        if len(out) >= limit:
            break
    return out
