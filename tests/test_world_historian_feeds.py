"""Tests for deterministic RSS/Atom ingestion."""

import json
from pathlib import Path

from conftest import load_runtime_module

db = load_runtime_module("db")
feeds = load_runtime_module("feeds")

RSS_SAMPLE = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel>
<title>Example Feed</title>
<item><title>First story</title><link>https://example.test/1</link>
  <pubDate>Mon, 31 Aug 2026 08:00:00 +0800</pubDate>
  <description>Alpha</description></item>
<item><title>Second story</title><link>https://example.test/2</link>
  <pubDate>Mon, 31 Aug 2026 09:00:00 +0800</pubDate>
  <description>Beta</description></item>
</channel></rss>"""

ATOM_SAMPLE = """<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
<title>Atom Feed</title>
<entry><title>Atom story</title>
  <link href="https://example.test/atom-1"/>
  <published>2026-08-31T09:30:00+08:00</published>
  <summary>Gamma</summary></entry>
</feed>"""


def fresh(tmp_path: Path):
    conn = db.connect(tmp_path / "chronicle.sqlite")
    db.migrate(conn)
    return conn


def test_parse_rss_and_atom_entries():
    rss = feeds.parse_feed(RSS_SAMPLE)
    assert [e["link"] for e in rss] == ["https://example.test/1",
                                        "https://example.test/2"]
    assert rss[0]["title"] == "First story"
    assert rss[0]["published"] is not None
    atom = feeds.parse_feed(ATOM_SAMPLE)
    assert atom[0]["link"] == "https://example.test/atom-1"
    assert atom[0]["title"] == "Atom story"


def test_ingest_is_idempotent_and_revisions_get_new_rows(tmp_path):
    conn = fresh(tmp_path)
    first = feeds.ingest_feed(conn, feed_name="Example",
                              feed_url="https://example.test/feed",
                              fetch=lambda url: RSS_SAMPLE)
    assert first["added"] == 2 and first["error"] is None
    second = feeds.ingest_feed(conn, feed_name="Example",
                               feed_url="https://example.test/feed",
                               fetch=lambda url: RSS_SAMPLE)
    assert second["added"] == 0  # same content → idempotent
    assert db.stats(conn)["sources"] == 2

    # Same URL, revised title → different hash → new row, no overwrite.
    revised = RSS_SAMPLE.replace("First story", "First story (updated)")
    third = feeds.ingest_feed(conn, feed_name="Example",
                              feed_url="https://example.test/feed",
                              fetch=lambda url: revised)
    assert third["added"] == 1
    titles = [r["title"] for r in conn.execute("SELECT title FROM sources")]
    assert "First story" in titles and "First story (updated)" in titles


def test_feed_failure_is_isolated(tmp_path):
    conn = fresh(tmp_path)

    def boom(url):
        raise OSError("network down")

    result = feeds.ingest_feed(conn, feed_name="Broken",
                               feed_url="https://broken.test/rss", fetch=boom)
    assert result["added"] == 0 and "network down" in result["error"]
    assert db.stats(conn)["sources"] == 0  # nothing half-written


def test_recent_sources_window(tmp_path):
    conn = fresh(tmp_path)
    feeds.ingest_feed(conn, feed_name="Example",
                      feed_url="https://example.test/feed",
                      fetch=lambda url: RSS_SAMPLE)
    recent = feeds.recent_sources(conn, hours=24)
    assert len(recent) == 2
    assert all(r["source_kind"] == "rss" for r in recent)
    assert feeds.recent_sources(conn, hours=0) == []


def test_ingest_all_uses_configured_sources(tmp_path):
    conn = fresh(tmp_path)
    config = tmp_path / "config.yaml"
    config.write_text(
        "sources:\n"
        "  - {name: A, kind: rss, url: 'https://a.test/feed'}\n"
        "  - {name: B, kind: wechat, note: no url use}\n"
        "  - {name: C, kind: site, url: 'https://c.test/'}\n",
        encoding="utf-8")
    assert feeds.configured_rss_sources(config) == [
        {"name": "A", "kind": "rss", "url": "https://a.test/feed"}]
    calls = []

    def fake_fetch(url):
        calls.append(url)
        return RSS_SAMPLE

    original = feeds.ingest_feed
    def spy_ingest(conn_arg, *, feed_name, feed_url, fetch=None, max_entries=30):
        return original(conn_arg, feed_name=feed_name, feed_url=feed_url,
                        fetch=fake_fetch, max_entries=max_entries)
    feeds.ingest_feed = spy_ingest
    try:
        result = feeds.ingest_all(conn, config_path=config)
    finally:
        feeds.ingest_feed = original
    assert calls == ["https://a.test/feed"]  # wechat/site filtered out
    assert result["sources_checked"] == 1
    assert result["entries_added"] == 2
    publishers = {r["publisher"] for r in conn.execute(
        "SELECT publisher FROM sources")}
    assert publishers == {"A"}


def test_ingested_source_ids_match_store_bundle_scheme(tmp_path):
    conn = fresh(tmp_path)
    feeds.ingest_feed(conn, feed_name="Example",
                      feed_url="https://example.test/feed",
                      fetch=lambda url: RSS_SAMPLE)
    row = conn.execute(
        "SELECT id, canonical_url, title, published_at, content_hash "
        "FROM sources LIMIT 1").fetchone()
    assert row["id"].startswith("src_")
    # Pin the real cross-path invariant: the row id must be exactly the stable id
    # store_bundle derives from (url, published_at, content_hash), so a bundle
    # describing the same article collapses onto the RSS-ingested row whenever
    # it carries the identical published_at and content_hash.
    assert row["content_hash"] == feeds._content_hash(
        row["title"], row["canonical_url"], row["published_at"])
    assert row["id"] == db.stable_id(
        "src", row["canonical_url"], row["published_at"], row["content_hash"])


def test_metadata_json_carries_summary(tmp_path):
    conn = fresh(tmp_path)
    feeds.ingest_feed(conn, feed_name="Example",
                      feed_url="https://example.test/feed",
                      fetch=lambda url: RSS_SAMPLE)
    meta = json.loads(conn.execute(
        "SELECT metadata_json FROM sources LIMIT 1").fetchone()[0])
    assert meta["feed"] == "Example"
    assert meta["summary"] in ("Alpha", "Beta")
