"""Five public-source collectors and deterministic pre-parsers (Section 5.2)."""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from typing import Any, Callable

try:
    from .db import make_claim_id, make_source_id, utc_now_iso
except ImportError:
    from db import make_claim_id, make_source_id, utc_now_iso  # type: ignore[no-redef]

Fetcher = Callable[[str], str]

CCDI_NOTICE_RE = re.compile(
    r"^(?P<prefix>.+?)(?P<name>[\u4e00-\u9fa5·]{2,5})涉嫌严重违纪违法"
)
DEFAULT_MEDIA_KEYWORDS = (
    "履新", "落马", "被查", "双开", "免职", "投案", "常委", "副省长", "副部长", "审查调查"
)


def default_http_fetch(url: str, timeout: float = 12.0) -> str:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; PAP-CadreTracker/1.0)",
            "Accept": "text/html,application/xhtml+xml,application/xml,application/json;q=0.9,*/*;q=0.8",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
        charset = resp.headers.get_content_charset() or "utf-8"
        return raw.decode(charset, errors="replace")


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _record_raw_source(
    conn: sqlite3.Connection,
    *,
    source_type: str,
    source_name: str,
    credibility_tier: int,
    url: str,
    title: str,
    published_at: str,
    raw_content: str,
) -> tuple[str, bool]:
    """Idempotently store a raw source by (url, content_hash). Returns (source_id, inserted)."""
    content_hash = _sha256(raw_content)
    existing = conn.execute(
        "SELECT source_id FROM raw_sources WHERE url = ? AND content_hash = ?",
        (url, content_hash),
    ).fetchone()
    if existing is not None:
        return existing["source_id"], False

    source_id = make_source_id(url, content_hash)
    cur = conn.execute(
        """INSERT OR IGNORE INTO raw_sources
           (source_id, source_type, source_name, credibility_tier, url, title, published_at, content_hash, raw_content, ingest_status)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending')""",
        (source_id, source_type, source_name, credibility_tier, url, title, published_at, content_hash, raw_content),
    )
    conn.commit()
    return source_id, cur.rowcount > 0


class _LinkExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._in_a = False
        self._href = ""
        self._buf: list[str] = []
        self.links: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "a":
            self._in_a = True
            self._href = dict(attrs).get("href") or ""
            self._buf = []

    def handle_data(self, data: str) -> None:
        if self._in_a:
            self._buf.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self._in_a:
            text = re.sub(r"\s+", " ", "".join(self._buf)).strip()
            if text:
                self.links.append((self._href, text))
            self._in_a = False


class CCDICollector:
    """Monitor CCDI central-managed cadre investigation & sanction notices (Tier 1)."""

    def __init__(self, fetcher: Fetcher = default_http_fetch) -> None:
        self.fetcher = fetcher

    @staticmethod
    def parse_notice_headline(headline: str) -> dict[str, Any] | None:
        clean = headline.strip()
        m = CCDI_NOTICE_RE.match(clean)
        if not m:
            return None
        prefix = m.group("prefix").strip()
        name = m.group("name").strip()
        return {
            "prefix": prefix,
            "name": name,
            "is_former": "原" in prefix,
            "voluntary_surrender": "主动投案" in clean,
            "headline": clean,
        }

    def poll(
        self,
        conn: sqlite3.Connection,
        endpoints: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        inserted_items: list[dict[str, Any]] = []
        for ep in endpoints:
            url = ep["url"]
            source_type = ep.get("source_type", "ccdi_investigation")
            source_name = ep.get("name", "中央纪委国家监委网站")
            html = self.fetcher(url)
            parser = _LinkExtractor()
            parser.feed(html)
            for href, text in parser.links:
                parsed = self.parse_notice_headline(text)
                if parsed is None and ("开除党籍" not in text and "双开" not in text and "严重违纪违法" not in text):
                    continue
                item_url = urllib.parse.urljoin(url, href) if href else f"{url}#{_sha256(text)[:12]}"
                payload = json.dumps({"headline": text, "parsed": parsed}, ensure_ascii=False)
                sid, is_new = _record_raw_source(
                    conn,
                    source_type=source_type,
                    source_name=source_name,
                    credibility_tier=1,
                    url=item_url,
                    title=text,
                    published_at=utc_now_iso(),
                    raw_content=payload,
                )
                if is_new:
                    inserted_items.append(
                        {"source_id": sid, "source_type": source_type, "title": text, "parsed": parsed}
                    )
        return inserted_items


class AppointCollector:
    """Monitor HRSS State Council & Xinhua appointment/removal notices (Tier 1)."""

    def __init__(self, fetcher: Fetcher = default_http_fetch) -> None:
        self.fetcher = fetcher

    @staticmethod
    def split_atomic_clauses(text: str) -> list[str]:
        parts = re.split(r"[。；;]+", text)
        return [p.strip() for p in parts if p.strip() and any(k in p for k in ("任命", "免去", "任", "职务", "批准"))]

    def poll(
        self,
        conn: sqlite3.Connection,
        endpoints: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        inserted_items: list[dict[str, Any]] = []
        for ep in endpoints:
            url = ep["url"]
            source_type = ep.get("source_type", "hrss_appoint")
            source_name = ep.get("name", "人社部/新华社任免")
            html = self.fetcher(url)
            parser = _LinkExtractor()
            parser.feed(html)
            for href, text in parser.links:
                if not any(k in text for k in ("国务院任免", "任免", "履新", "书记", "省长", "市长", "部长", "常委")):
                    continue
                item_url = urllib.parse.urljoin(url, href) if href else f"{url}#{_sha256(text)[:12]}"
                clauses = self.split_atomic_clauses(text)
                payload = json.dumps({"title": text, "clauses": clauses}, ensure_ascii=False)
                sid, is_new = _record_raw_source(
                    conn,
                    source_type=source_type,
                    source_name=source_name,
                    credibility_tier=1,
                    url=item_url,
                    title=text,
                    published_at=utc_now_iso(),
                    raw_content=payload,
                )
                if is_new:
                    inserted_items.append(
                        {"source_id": sid, "source_type": source_type, "title": text, "clauses": clauses}
                    )
        return inserted_items


class WikiCollector:
    """Wikipedia Wikitext & Wikidata SPARQL collector (Tier 3)."""

    def __init__(self, fetcher: Fetcher = default_http_fetch) -> None:
        self.fetcher = fetcher

    @staticmethod
    def parse_wikitext_infobox(wikitext: str) -> dict[str, Any]:
        """Stdlib Wikitext parser for {{Infobox officeholder}} and {{Succession box}}."""
        info: dict[str, str] = {}
        successions: list[dict[str, str]] = []

        # Extract Infobox officeholder key=value pairs
        infobox_m = re.search(r"\{\{\s*Infobox\s+officeholder(.*?)\n\}\}", wikitext, flags=re.IGNORECASE | re.DOTALL)
        if infobox_m:
            body = infobox_m.group(1)
            for line in body.splitlines():
                kv = re.match(r"^\s*\|\s*([^=]+?)\s*=\s*(.+?)\s*$", line)
                if kv:
                    info[kv.group(1).strip()] = kv.group(2).strip()

        # Extract {{Succession box|...}}
        for sm in re.finditer(r"\{\{\s*Succession\s+box(.*?)\}\}", wikitext, flags=re.IGNORECASE | re.DOTALL):
            box: dict[str, str] = {}
            for part in sm.group(1).split("|"):
                if "=" in part:
                    k, v = part.split("=", 1)
                    box[k.strip()] = v.strip()
            if box:
                successions.append(box)

        return {"infobox": info, "succession_boxes": successions}

    def poll_recent_changes(
        self,
        conn: sqlite3.Connection,
        api_url: str,
        watched_titles: set[str] | None = None,
    ) -> list[dict[str, Any]]:
        query_url = f"{api_url}?action=query&list=recentchanges&rcnamespace=0&rclimit=50&format=json"
        raw = self.fetcher(query_url)
        data = json.loads(raw)
        changes = data.get("query", {}).get("recentchanges", [])
        inserted: list[dict[str, Any]] = []
        for ch in changes:
            title = str(ch.get("title", "")).strip()
            if watched_titles is not None and title not in watched_titles:
                continue
            revid = ch.get("revid")
            item_url = f"{api_url}?title={urllib.parse.quote(title)}&oldid={revid}"
            sid, is_new = _record_raw_source(
                conn,
                source_type="wikipedia_wikitext",
                source_name="中文维基百科",
                credibility_tier=3,
                url=item_url,
                title=title,
                published_at=str(ch.get("timestamp") or utc_now_iso()),
                raw_content=json.dumps(ch, ensure_ascii=False),
            )
            if is_new:
                inserted.append({"source_id": sid, "source_type": "wikipedia_wikitext", "title": title})
        return inserted


class DeepMediaCollector:
    """RSS/Atom collector for Caixin / ThePaper / etc. with known-cadre & keyword filtering (Tier 2)."""

    def __init__(self, fetcher: Fetcher = default_http_fetch) -> None:
        self.fetcher = fetcher

    def poll(
        self,
        conn: sqlite3.Connection,
        feeds: list[dict[str, Any]],
        *,
        keywords: tuple[str, ...] = DEFAULT_MEDIA_KEYWORDS,
    ) -> list[dict[str, Any]]:
        known_names = {
            r["name"] for r in conn.execute("SELECT name FROM persons WHERE length(name) >= 2").fetchall()
        }
        inserted: list[dict[str, Any]] = []
        for feed in feeds:
            feed_url = feed["url"]
            source_name = feed.get("name", "政经深度媒体")
            tier = int(feed.get("credibility_tier", 2))
            xml_text = self.fetcher(feed_url)
            root = ET.fromstring(xml_text)
            items = root.findall(".//item") or root.findall(".//{http://www.w3.org/2005/Atom}entry")
            for item in items:
                title = (item.findtext("title") or item.findtext("{http://www.w3.org/2005/Atom}title") or "").strip()
                link = (item.findtext("link") or "").strip()
                if not link:
                    link_el = item.find("{http://www.w3.org/2005/Atom}link")
                    if link_el is not None:
                        link = (link_el.attrib.get("href") or "").strip()
                desc = (
                    item.findtext("description")
                    or item.findtext("{http://www.w3.org/2005/Atom}summary")
                    or ""
                ).strip()
                pub = (
                    item.findtext("pubDate")
                    or item.findtext("{http://www.w3.org/2005/Atom}updated")
                    or utc_now_iso()
                ).strip()
                haystack = f"{title} {desc}"
                hit_name = any(n in haystack for n in known_names)
                hit_kw = any(kw in haystack for kw in keywords)
                if not (hit_name or hit_kw):
                    continue
                sid, is_new = _record_raw_source(
                    conn,
                    source_type="deep_media",
                    source_name=source_name,
                    credibility_tier=tier,
                    url=link or f"{feed_url}#{_sha256(title)[:12]}",
                    title=title,
                    published_at=pub,
                    raw_content=json.dumps({"title": title, "description": desc, "link": link}, ensure_ascii=False),
                )
                if is_new:
                    inserted.append({"source_id": sid, "source_type": "deep_media", "title": title})
        return inserted


class _RosterHTMLParser(HTMLParser):
    """Lightweight stdlib HTML extractor matching simple tag/class/id selectors."""

    def __init__(self, target_tag: str | None, target_class: str | None, target_id: str | None) -> None:
        super().__init__()
        self.target_tag = target_tag
        self.target_class = target_class
        self.target_id = target_id
        self._depth = 0
        self._capturing = False
        self._buf: list[str] = []
        self.items: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = dict(attrs)
        if not self._capturing:
            tag_ok = self.target_tag is None or tag.lower() == self.target_tag
            classes = (attr_map.get("class") or "").split()
            cls_ok = self.target_class is None or self.target_class in classes
            id_ok = self.target_id is None or attr_map.get("id") == self.target_id
            if tag_ok and cls_ok and id_ok:
                self._capturing = True
                self._depth = 1
                self._buf = []
        else:
            self._depth += 1

    def handle_data(self, data: str) -> None:
        if self._capturing:
            self._buf.append(data)

    def handle_endtag(self, tag: str) -> None:
        if self._capturing:
            self._depth -= 1
            if self._depth <= 0:
                text = re.sub(r"\s+", " ", "".join(self._buf)).strip()
                if text:
                    self.items.append(text)
                self._capturing = False


def extract_roster_from_html(html: str, css_selector: str) -> list[dict[str, Any]]:
    """Extract [(rank_order, name, title)] from a leadership roster HTML page."""
    # Parse the leaf selector part (e.g. 'ul.leaders li.leader-item' -> tag='li', class='leader-item')
    leaf = css_selector.strip().split()[-1]
    target_tag: str | None = None
    target_class: str | None = None
    target_id: str | None = None
    if "#" in leaf:
        t, target_id = leaf.split("#", 1)
        target_tag = t.lower() or None
    elif "." in leaf:
        t, target_class = leaf.split(".", 1)
        target_tag = t.lower() or None
    else:
        target_tag = leaf.lower() or None

    parser = _RosterHTMLParser(target_tag, target_class, target_id)
    parser.feed(html)

    roster: list[dict[str, Any]] = []
    for idx, raw_item in enumerate(parser.items, start=1):
        # Support formats like "殷勇 市长", "副省长：张三", "张三（副省长）"
        m_colon = re.match(r"^(?P<title>[^：:]+)[：:]\s*(?P<name>[\u4e00-\u9fa5·]{2,5})$", raw_item)
        m_paren = re.match(r"^(?P<name>[\u4e00-\u9fa5·]{2,5})\s*[（(](?P<title>[^）)]+)[）)]$", raw_item)
        m_space = re.match(r"^(?P<name>[\u4e00-\u9fa5·]{2,5})\s+(?P<title>.+)$", raw_item)
        if m_colon:
            name, title = m_colon.group("name").strip(), m_colon.group("title").strip()
        elif m_paren:
            name, title = m_paren.group("name").strip(), m_paren.group("title").strip()
        elif m_space:
            name, title = m_space.group("name").strip(), m_space.group("title").strip()
        else:
            name, title = raw_item.strip(), ""
        roster.append({"rank_order": idx, "name": name, "title": title})
    return roster


def _age_in_years(birth_ym: str | None, ref_date: datetime) -> float | None:
    if not birth_ym or not re.fullmatch(r"\d{4}-\d{2}", birth_ym):
        return None
    by, bm = (int(x) for x in birth_ym.split("-"))
    return (ref_date.year - by) + (ref_date.month - bm) / 12.0


def _retirement_threshold(rank: str | None) -> int:
    if rank in ("正国级", "副国级"):
        return 68
    if rank == "正省部级":
        return 65
    return 60


class GovDomSentinel:
    """31-province & ministry leadership roster DOM diff sentinel (Section 5.2)."""

    def __init__(self, fetcher: Fetcher = default_http_fetch) -> None:
        self.fetcher = fetcher

    def poll(
        self,
        conn: sqlite3.Connection,
        *,
        captured_date: str | None = None,
        now: datetime | None = None,
    ) -> list[dict[str, Any]]:
        ref_dt = now or datetime.now(timezone.utc)
        cap_date = captured_date or ref_dt.strftime("%Y-%m-%d")
        targets = conn.execute(
            """SELECT t.*, o.canonical_name AS org_name
               FROM gov_roster_targets t
               JOIN organizations o ON o.org_id = t.org_id
               WHERE t.enabled = 1"""
        ).fetchall()

        events: list[dict[str, Any]] = []
        for target in targets:
            html = self.fetcher(target["page_url"])
            roster = extract_roster_from_html(html, target["css_selector"])
            roster_json = json.dumps(roster, ensure_ascii=False, sort_keys=True)
            roster_hash = _sha256(roster_json)

            prev = conn.execute(
                """SELECT snapshot_id, captured_date, roster_json, roster_hash
                   FROM gov_roster_snapshots
                   WHERE target_id = ?
                   ORDER BY captured_date DESC, snapshot_id DESC
                   LIMIT 1""",
                (target["target_id"],),
            ).fetchone()

            conn.execute(
                "UPDATE gov_roster_targets SET last_checked_at = ? WHERE target_id = ?",
                (utc_now_iso(), target["target_id"]),
            )

            if prev is not None and prev["roster_hash"] == roster_hash:
                conn.commit()
                continue

            target_id_val = target["target_id"]
            snap_id = f"snap_{_sha256(f'{target_id_val}|{cap_date}|{roster_hash}')[:14]}"
            conn.execute(
                """INSERT INTO gov_roster_snapshots (snapshot_id, target_id, captured_date, roster_json, roster_hash)
                   VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(target_id, captured_date) DO UPDATE SET
                     snapshot_id = excluded.snapshot_id,
                     roster_json = excluded.roster_json,
                     roster_hash = excluded.roster_hash""",
                (snap_id, target["target_id"], cap_date, roster_json, roster_hash),
            )

            if prev is None:
                # Baseline snapshot established
                conn.commit()
                continue

            prev_roster = json.loads(prev["roster_json"])
            prev_names = {item["name"]: item for item in prev_roster}
            curr_names = {item["name"]: item for item in roster}

            removed = [name for name in prev_names if name not in curr_names]
            added = [name for name in curr_names if name not in prev_names]

            for name in removed:
                person = conn.execute(
                    "SELECT person_id, birth_ym, current_rank, status FROM persons WHERE name = ? LIMIT 1",
                    (name,),
                ).fetchone()
                age = _age_in_years(person["birth_ym"], ref_dt) if person else None
                retire_age = _retirement_threshold(person["current_rank"] if person else None)
                cutoff_date = (ref_dt - timedelta(days=14)).strftime("%Y-%m-%d")
                has_recent_transfer = False
                if person is not None:
                    tr = conn.execute(
                        """SELECT 1 FROM claims_and_clues
                           WHERE subject_person_id = ? AND claim_type = 'appointment'
                             AND event_date >= ? LIMIT 1""",
                        (person["person_id"], cutoff_date),
                    ).fetchone()
                    has_recent_transfer = tr is not None

                is_anomaly = (age is None or age < retire_age) and not has_recent_transfer
                diff_payload = {
                    "target_id": target["target_id"],
                    "org_name": target["org_name"],
                    "change": "removed",
                    "name": name,
                    "previous_title": prev_names[name].get("title"),
                    "age": round(age, 1) if age is not None else None,
                    "retirement_threshold": retire_age,
                    "has_recent_transfer": has_recent_transfer,
                    "is_anomaly": is_anomaly,
                }
                title = f"[{target['org_name']}] 领导列表移除 '{name}'"
                sid, is_new = _record_raw_source(
                    conn,
                    source_type="gov_dom_diff",
                    source_name=f"官网领导之窗哨兵({target['org_name']})",
                    credibility_tier=2,
                    url=f"{target['page_url']}#diff-{cap_date}-{name}",
                    title=title,
                    published_at=utc_now_iso(),
                    raw_content=json.dumps(diff_payload, ensure_ascii=False),
                )
                if is_anomaly:
                    cid = make_claim_id(sid, "dom_removal_anomaly", name, title)
                    conn.execute(
                        """INSERT OR IGNORE INTO claims_and_clues
                           (claim_id, source_id, claim_type, event_date, subject_person_id, subject_raw_name,
                            certainty, payload_json, evidence_quote, confidence, review_status)
                           VALUES (?, ?, 'dom_removal_anomaly', ?, ?, ?, 'FACT', ?, ?, 0.95, 'auto_merged')""",
                        (
                            cid,
                            sid,
                            cap_date,
                            person["person_id"] if person else None,
                            name,
                            json.dumps(diff_payload, ensure_ascii=False),
                            title,
                        ),
                    )
                if is_new:
                    events.append(
                        {
                            "source_id": sid,
                            "source_type": "gov_dom_diff",
                            "title": title,
                            "is_anomaly": is_anomaly,
                            "name": name,
                        }
                    )

            for name in added:
                title = f"[{target['org_name']}] 领导列表新增 '{name}'"
                sid, is_new = _record_raw_source(
                    conn,
                    source_type="gov_dom_diff",
                    source_name=f"官网领导之窗哨兵({target['org_name']})",
                    credibility_tier=2,
                    url=f"{target['page_url']}#add-{cap_date}-{name}",
                    title=title,
                    published_at=utc_now_iso(),
                    raw_content=json.dumps(
                        {"target_id": target["target_id"], "org_name": target["org_name"], "change": "added", "entry": curr_names[name]},
                        ensure_ascii=False,
                    ),
                )
                if is_new:
                    events.append(
                        {"source_id": sid, "source_type": "gov_dom_diff", "title": title, "is_anomaly": False, "name": name}
                    )

            conn.commit()
        return events
