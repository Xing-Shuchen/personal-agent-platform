"""Disposable, atomically published dashboard read model from Chronicle.

The canonical database is opened read-only. A generation is immutable; CURRENT
is replaced only after every file has passed validation. The Obsidian plugin
can continue using the preceding generation during a rebuild.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sqlite3
import tempfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA = "world-historian-dashboard.v1"
GENERATOR = "0.7.0"


def _rows(conn: sqlite3.Connection, sql: str, args: tuple = ()) -> list[dict]:
    return [dict(row) for row in conn.execute(sql, args)]


def _json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def _fsync_directory(path: Path) -> None:
    try:
        descriptor = os.open(path, os.O_RDONLY)
    except OSError:
        return
    try:
        try:
            os.fsync(descriptor)
        except OSError:
            pass
    finally:
        os.close(descriptor)


class _GenerationWriter:
    """Reuse byte-identical files from the preceding immutable generation."""

    def __init__(self, root: Path, previous: Path | None = None):
        self.root = root
        self.previous = previous
        self.reused = 0
        self.written = 0

    def write(self, relative: str, value: Any) -> None:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
        old = self.previous / relative if self.previous else None
        if old and old.is_file() and old.read_bytes() == payload:
            os.link(old, path)
            self.reused += 1
        else:
            with path.open("wb") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            self.written += 1


def _canonical(kind: str, identifier: str, path: str | None = None) -> dict:
    result = {"kind": "chronicle", "table": kind, "id": identifier}
    if path:
        result["obsidian_path"] = path
    return result


def _meaningful(*values: str | None) -> str | None:
    return max((value for value in values if value), key=_time_key, default=None)


def _time_key(value: str) -> float:
    try:
        raw = value.split("/", 1)[0].replace("Z", "+00:00")
        if len(raw) == 4:
            raw += "-01-01"
        elif len(raw) == 7:
            raw += "-01"
        parsed = datetime.fromisoformat(raw)
        return (parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)).timestamp()
    except (ValueError, OverflowError):
        return float("-inf")


def _normalized_status(value: str) -> str:
    return {"closed": "resolved", "candidate": "watching"}.get(value, value)


def _claim_state(value: str) -> str:
    return {"active": "uncertain", "confirmed": "supported", "disputed": "contested"}.get(value, value)


def _thread_note_paths(index_path: Path | None, vault_dir: Path | None) -> dict[str, str]:
    paths = {}
    if index_path and index_path.exists():
        data = json.loads(index_path.read_text(encoding="utf-8"))
        candidates = data.get("threads", data) if isinstance(data, dict) else {}
        paths.update({key: "2Area/41 新闻及事件/" + value for key, value in candidates.items()
                      if isinstance(key, str) and isinstance(value, str)})
    if vault_dir:
        note_dir = vault_dir / "2Area" / "41 新闻及事件"
        for note in sorted((*note_dir.glob("*.md"), *(note_dir / "closed_threads").glob("*.md"))):
            head = note.read_text(encoding="utf-8")[:2000]
            match = re.search(r'^thread_id:\s*["\']?([A-Za-z0-9_-]+)', head, re.MULTILINE)
            if match:
                paths[match.group(1)] = str(note.relative_to(vault_dir))
    return paths


def _manual_annotations(vault_dir: Path | None, note_paths: dict[str, str]) -> dict[str, dict]:
    if not vault_dir:
        return {}
    annotations = {}
    for thread_id, relative in note_paths.items():
        path = vault_dir / relative
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        match = re.search(r"^#{1,6}\s+手工批注\s*\n(?P<body>[\s\S]*)\Z", text, re.MULTILINE)
        if match:
            body = match.group("body").strip()
            if body and body != "（无）":
                annotations[thread_id] = {"text": body, "provenance": "manual", "canonical_ref": {"kind": "obsidian_file", "path": relative}}
    return annotations


def build(conn: sqlite3.Connection, directory: Path, *, note_paths: dict[str, str] | None = None,
          locations: list[dict] | None = None, annotations: dict[str, dict] | None = None,
          previous: Path | None = None) -> dict:
    """Build and validate one generation in a private directory."""
    note_paths = note_paths or {}
    locations = locations or []
    annotations = annotations or {}
    writer = _GenerationWriter(directory, previous)
    threads = _rows(conn, "SELECT * FROM threads ORDER BY id")
    events = _rows(conn, "SELECT * FROM events ORDER BY id")
    entities = _rows(conn, "SELECT * FROM entities ORDER BY id")
    claims = _rows(conn, "SELECT * FROM claims ORDER BY id")
    sources = {row["id"]: row for row in _rows(conn, "SELECT id, canonical_url, title, publisher, source_kind, published_at, updated_at, fetched_at FROM sources ORDER BY id")}
    memberships = _rows(conn, "SELECT * FROM thread_events ORDER BY thread_id, event_id")
    event_entities = _rows(conn, "SELECT * FROM event_entities ORDER BY event_id, entity_id, role")
    thread_entities = _rows(conn, "SELECT * FROM thread_entities ORDER BY thread_id, entity_id")
    questions = _rows(conn, "SELECT * FROM open_questions ORDER BY id")
    relations = _rows(conn, "SELECT * FROM relations WHERE status != 'rejected' ORDER BY id")
    relations_by_thread: dict[str, list[dict]] = defaultdict(list)
    relations_by_entity: dict[str, list[dict]] = defaultdict(list)
    for relation in relations:
        if relation["src_type"] == relation["dst_type"] == "thread":
            relations_by_thread[relation["src_id"]].append(relation)
            relations_by_thread[relation["dst_id"]].append(relation)
        elif relation["src_type"] == relation["dst_type"] == "entity":
            relations_by_entity[relation["src_id"]].append(relation)
            relations_by_entity[relation["dst_id"]].append(relation)
    watches = _rows(conn, "SELECT * FROM watch_queries WHERE active = 1 ORDER BY id")
    has_states = conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='thread_current_states'").fetchone()
    states = {row["thread_id"]: row for row in _rows(conn, "SELECT * FROM thread_current_states ORDER BY thread_id")} if has_states else {}
    by_id = {row["id"]: row for row in events}
    entity_by_id = {row["id"]: row for row in entities}
    member_events: dict[str, list[str]] = defaultdict(list)
    event_threads: dict[str, list[str]] = defaultdict(list)
    for row in memberships:
        member_events[row["thread_id"]].append(row["event_id"])
        event_threads[row["event_id"]].append(row["thread_id"])
    event_entity_ids: dict[str, set[str]] = defaultdict(set)
    entity_event_ids: dict[str, set[str]] = defaultdict(set)
    for row in event_entities:
        event_entity_ids[row["event_id"]].add(row["entity_id"])
        entity_event_ids[row["entity_id"]].add(row["event_id"])
    thread_entity_ids: dict[str, set[str]] = defaultdict(set)
    entity_thread_ids: dict[str, set[str]] = defaultdict(set)
    for row in thread_entities:
        thread_entity_ids[row["thread_id"]].add(row["entity_id"])
    for tid, eids in member_events.items():
        for eid in eids:
            thread_entity_ids[tid].update(event_entity_ids[eid])
    for tid, ids in thread_entity_ids.items():
        for eid in ids:
            entity_thread_ids[eid].add(tid)
    claims_by_event: dict[str, list[dict]] = defaultdict(list)
    for row in claims:
        source = sources.get(row["source_id"])
        claims_by_event[row["event_id"]].append({
            "claim_id": row["id"], "statement": row["statement"],
            "state": _claim_state(row["status"]), "canonical_state": row["status"],
            "confidence": row["confidence"], "asserted_at": row["asserted_at"],
            "updated_at": row["updated_at"], "superseded_by": row["superseded_by"],
            "source": ({"source_id": source["id"], "title": source["title"],
                        "publisher": source["publisher"], "source_kind": source["source_kind"],
                        "published_at": source["published_at"], "url": source["canonical_url"],
                        "relationship": "claim_origin",
                        "canonical_ref": _canonical("sources", source["id"])} if source else None),
            "canonical_ref": _canonical("claims", row["id"]),
        })
    questions_by_thread: dict[str, list[dict]] = defaultdict(list)
    for row in questions:
        questions_by_thread[row["thread_id"]].append({
            "question_id": row["id"], "question": row["question"], "state": row["status"],
            "answer_event_id": row["answer_event_id"], "opened_at": row["created_at"],
            "last_updated_at": row["updated_at"], "canonical_ref": _canonical("open_questions", row["id"]),
        })
    watches_by_thread: dict[str, list[dict]] = defaultdict(list)
    for row in watches:
        watches_by_thread[row["thread_id"]].append({"query": row["query"], "kind": row["query_kind"]})

    # Geographic evidence is admitted only from explicit event→location links.
    # Chronicle currently has no coordinate table; optional registry entries
    # preserve their own provenance and precision.
    location_by_id = {}
    for location in locations:
        if not all(key in location for key in ("location_id", "name", "lat", "lon", "geo_precision", "canonical_source_ref")):
            raise ValueError("location registry entries require id, name, coordinates, precision and provenance")
        if location["geo_precision"] not in {"exact", "city", "region", "country", "approximate"} or not isinstance(location["canonical_source_ref"], dict):
            raise ValueError("location registry requires known precision and structured provenance")
        if any(isinstance(location[key], bool) or not isinstance(location[key], (int, float)) for key in ("lat", "lon")) or not (-90 <= location["lat"] <= 90 and -180 <= location["lon"] <= 180):
            raise ValueError("invalid location coordinates")
        if location["location_id"] in location_by_id:
            raise ValueError("duplicate location ID")
        location_by_id[location["location_id"]] = {**location, "event_ids": [], "thread_ids": []}
    event_locations: dict[str, set[str]] = defaultdict(set)
    for row in relations:
        if row["src_type"] == "event" and row["dst_type"] == "location" and row["dst_id"] in location_by_id and row["relation_type"] in {"occurs_at", "event_occurs_at_location"}:
            event_locations[row["src_id"]].add(row["dst_id"])
    for eid, lids in event_locations.items():
        for lid in lids:
            location_by_id[lid]["event_ids"].append(eid)
            location_by_id[lid]["thread_ids"].extend(event_threads[eid])
    for location in location_by_id.values():
        location["event_ids"] = sorted(set(location["event_ids"]))
        location["thread_ids"] = sorted(set(location["thread_ids"]))

    timeline = []
    for row in events:
        eid = row["id"]
        item = {
            "event_id": eid, "thread_ids": sorted(event_threads[eid]),
            "title": row["title"] or ((row["occurred_at"] or row["reported_at"] or row["observed_at"] or "")[:10] + " · 事件记录"),
            "summary": row["summary"], "occurred_at": row["occurred_at"],
            "reported_at": row["reported_at"], "first_observed_at": row["observed_at"],
            "time_precision": row["occurred_at_precision"], "confidence": row["confidence"],
            "state": row["status"], "entity_ids": sorted(event_entity_ids[eid]),
            "location_ids": sorted(event_locations[eid]), "claim_count": len(claims_by_event[eid]),
            "source_count": len({claim["source"]["source_id"] for claim in claims_by_event[eid] if claim["source"]}),
            "claim_states": sorted({claim["state"] for claim in claims_by_event[eid]}),
            "canonical_ref": _canonical("events", eid, next((note_paths[tid] for tid in event_threads[eid] if tid in note_paths), None)),
        }
        timeline.append(item)
        detail = {**item, "claims": claims_by_event[eid]}
        writer.write(f"events/{eid}.json", detail)
    timeline.sort(key=lambda e: (_time_key(e["occurred_at"] or e["reported_at"] or e["first_observed_at"] or ""), e["event_id"]), reverse=True)
    timeline_by_id = {event["event_id"]: event for event in timeline}
    timeline_rank = {event["event_id"]: index for index, event in enumerate(timeline)}

    thread_list = []
    for row in threads:
        tid = row["id"]
        eids = member_events[tid]
        sorted_eids = sorted(eids, key=timeline_rank.__getitem__)
        linked_events = [by_id[eid] for eid in eids]
        latest_event = max(linked_events, key=lambda e: (_time_key(e["occurred_at"] or e["reported_at"] or e["observed_at"] or ""), e["id"])) if linked_events else None
        event_changes = [event["updated_at"] for event in linked_events]
        last_event_change = _meaningful(row["last_event_ingested_at"], *event_changes)
        claim_changes = [claim["updated_at"] for eid in eids for claim in claims_by_event[eid]]
        q_changes = [question["last_updated_at"] for question in questions_by_thread[tid]]
        source_changes = [claim["source"]["source_id"] for eid in eids for claim in claims_by_event[eid] if claim["source"]]
        source_ingestions = [sources[sid]["fetched_at"] for sid in set(source_changes) if sid in sources]
        state = states.get(tid)
        last_meaningful = _meaningful(row["created_at"], last_event_change, state["updated_at"] if state else None, *claim_changes, *q_changes, *source_ingestions)
        open_questions = [q for q in questions_by_thread[tid] if q["state"] == "open"]
        attention = []
        if any(c["state"] in {"contested", "superseded"} for eid in eids for c in claims_by_event[eid]):
            attention.append("contested_or_corrected_claim")
        if row["priority"] == "high" and open_questions:
            attention.append("high_priority_open_questions")
        if row["priority"] == "high" and row["quiet_count"] >= 3:
            attention.append("high_priority_stale")
        note = note_paths.get(tid)
        item = {
            "thread_id": tid, "title": row["title"], "status": _normalized_status(row["status"]),
            "canonical_status": row["status"], "priority": row["priority"],
            "tracking_since": row["created_at"], "last_meaningful_change_at": last_meaningful,
            "last_event_ingested_at": row["last_event_ingested_at"],
            "last_event_change_at": last_event_change,
            "last_claim_change_at": _meaningful(*claim_changes),
            "last_question_change_at": _meaningful(*q_changes),
            "last_source_ingested_at": _meaningful(*source_ingestions),
            "last_event_at": latest_event["occurred_at"] or latest_event["reported_at"] if latest_event else None,
            "latest_event_id": latest_event["id"] if latest_event else None,
            "latest_event_summary": latest_event["summary"] if latest_event else None,
            "current_state_excerpt": state["body"][:240] if state else None, "open_question_count": len(open_questions),
            "event_count": len(eids),
            "source_count": len({c["source"]["source_id"] for eid in eids for c in claims_by_event[eid] if c["source"]}),
            "stale": row["quiet_count"] >= 3,
            "top_entity_ids": sorted(thread_entity_ids[tid], key=lambda ent: (-len(entity_event_ids[ent].intersection(eids)), ent))[:8],
            "location_ids": sorted({lid for eid in eids for lid in event_locations[eid]}),
            "attention": {"required": bool(attention), "reasons": attention},
            "canonical_ref": _canonical("threads", tid, note),
        }
        thread_list.append(item)
        detail = {**item,
                  "current_state": {"text": state["body"] if state else None,
                                    "provenance": state["provenance"] if state else "unavailable",
                                    "updated_at": state["updated_at"] if state else None,
                                    "revision": state["revision"] if state else None,
                                    "source_refs": json.loads(state["source_refs_json"] or "[]") if state else [],
                                    "canonical_ref": _canonical("thread_current_states", tid) if state else None,
                                    "stale": bool(state and last_event_change and _time_key(last_event_change) > _time_key(state["updated_at"]))},
                  "open_questions": questions_by_thread[tid], "watch_queries": watches_by_thread[tid],
                  "annotations": [annotations[tid]] if tid in annotations else [],
                  "event_ids": sorted_eids,
                  "event_summaries": [timeline_by_id[eid] for eid in sorted_eids],
                  "entity_ids": sorted(thread_entity_ids[tid]),
                  "related_threads": [dict(relation_id=r["id"], thread_id=r["dst_id"] if r["src_id"] == tid else r["src_id"], type=r["relation_type"], confidence=r["confidence"])
                                      for r in relations_by_thread[tid]],
                  }
        writer.write(f"threads/{tid}.json", detail)
    thread_list.sort(key=lambda t: (_time_key(t["last_meaningful_change_at"] or ""), t["thread_id"]), reverse=True)

    entity_list = []
    thread_by_id = {thread["id"]: thread for thread in threads}
    thread_summary_by_id = {thread["thread_id"]: thread for thread in thread_list}
    for row in entities:
        eid = row["id"]
        ev_ids = entity_event_ids[eid]
        tids = {tid for event_id in ev_ids for tid in event_threads[event_id]}
        tids.update(entity_thread_ids[eid])
        last_seen = _meaningful(*(by_id[event_id]["occurred_at"] or by_id[event_id]["reported_at"] or by_id[event_id]["observed_at"] for event_id in ev_ids))
        related = sorted({r["dst_id"] if r["src_id"] == eid else r["src_id"] for r in relations_by_entity[eid]})
        item = {"entity_id": eid, "name": row["name"], "kind": row["kind"],
                "aliases": json.loads(row["aliases_json"] or "[]"),
                "thread_ids": sorted(tids, key=lambda tid: (_time_key(thread_summary_by_id[tid]["last_meaningful_change_at"] or ""), tid), reverse=True),
                "event_count": len(ev_ids), "thread_count": len(tids), "last_seen_at": last_seen,
                "canonical_ref": _canonical("entities", eid)}
        entity_list.append(item)
        contextual_questions = [{**question, "owner_thread_id": tid} for tid in sorted(tids) for question in questions_by_thread[tid]]
        writer.write(f"entities/{eid}.json", {**item, "event_ids": sorted(ev_ids),
              "related_entity_ids": related, "location_ids": sorted({lid for event_id in ev_ids for lid in event_locations[event_id]}),
              "current_thread_ids": sorted(tid for tid in tids if _normalized_status(thread_by_id[tid]["status"]) in {"active", "watching"}),
              "contextual_questions": contextual_questions})
    entity_list.sort(key=lambda e: (-e["thread_count"], -e["event_count"], e["name"], e["entity_id"]))

    nodes = {"thread:" + t["thread_id"]: {"type": "thread", "label": t["title"], "canonical_ref": t["canonical_ref"]} for t in thread_list}
    nodes.update({"event:" + e["event_id"]: {"type": "event", "label": e["title"], "canonical_ref": e["canonical_ref"]} for e in timeline})
    nodes.update({"entity:" + e["entity_id"]: {"type": "entity", "label": e["name"], "canonical_ref": e["canonical_ref"]} for e in entity_list})
    nodes.update({"location:" + l["location_id"]: {"type": "location", "label": l["name"], "canonical_ref": l["canonical_source_ref"]} for l in location_by_id.values()})
    nodes.update({"question:" + q["id"]: {"type": "question", "label": q["question"], "state": q["status"], "owner_thread_id": q["thread_id"], "canonical_ref": _canonical("open_questions", q["id"])} for q in questions})
    nodes.update({"claim:" + c["id"]: {"type": "claim", "label": c["statement"][:120], "state": _claim_state(c["status"]), "confidence": c["confidence"], "owner_event_id": c["event_id"], "canonical_ref": _canonical("claims", c["id"])} for c in claims})
    linked_source_ids = {c["source_id"] for c in claims}
    nodes.update({"source:" + sid: {"type": "source", "label": sources[sid]["title"], "publisher": sources[sid]["publisher"], "url": sources[sid]["canonical_url"], "canonical_ref": _canonical("sources", sid)} for sid in sorted(linked_source_ids) if sid in sources})
    edges = []
    for row in memberships:
        edges.append({"id": "member:" + row["thread_id"] + ":" + row["event_id"], "source": "thread:" + row["thread_id"], "target": "event:" + row["event_id"], "type": "thread_contains_event", "confidence": row["membership_confidence"]})
    for row in thread_entities:
        edges.append({"id": "thread_entity:" + row["thread_id"] + ":" + row["entity_id"], "source": "thread:" + row["thread_id"], "target": "entity:" + row["entity_id"], "type": "thread_involves_entity"})
    for row in event_entities:
        edges.append({"id": "event_entity:" + row["event_id"] + ":" + row["entity_id"] + ":" + row["role"], "source": "event:" + row["event_id"], "target": "entity:" + row["entity_id"], "type": "event_involves_entity", "role": row["role"]})
    for row in claims:
        edges.append({"id": "event_claim:" + row["id"], "source": "event:" + row["event_id"], "target": "claim:" + row["id"], "type": "event_contains_claim"})
        if "source:" + row["source_id"] in nodes:
            edges.append({"id": "claim_source:" + row["id"], "source": "claim:" + row["id"], "target": "source:" + row["source_id"], "type": "claim_supported_by_source"})
    for row in questions:
        edges.append({"id": "question_thread:" + row["id"], "source": "question:" + row["id"], "target": "thread:" + row["thread_id"], "type": "question_about_thread"})
    for eid, lids in event_locations.items():
        for lid in lids:
            edges.append({"id": "event_location:" + eid + ":" + lid, "source": "event:" + eid, "target": "location:" + lid, "type": "event_occurs_at_location"})
    for row in relations:
        src, dst = row["src_type"] + ":" + row["src_id"], row["dst_type"] + ":" + row["dst_id"]
        if src in nodes and dst in nodes:
            edges.append({"id": row["id"], "source": src, "target": dst, "type": row["relation_type"],
                          "confidence": row["confidence"], "evidence_refs": json.loads(row["evidence_json"] or "[]"),
                          "canonical_ref": _canonical("relations", row["id"])})
    edges.sort(key=lambda edge: edge["id"])
    writer.write("threads.json", thread_list)
    partitions: dict[str, list[dict]] = defaultdict(list)
    for event in timeline:
        date = event["occurred_at"] or event["reported_at"] or event["first_observed_at"] or ""
        key = date[:7] if re.fullmatch(r"\d{4}-\d{2}", date[:7]) else "undated"
        partitions[key].append(event)
    for key, records in partitions.items():
        writer.write(f"timeline/{key}.json", records)
    ordered_partitions = sorted((key for key in partitions if key != "undated"), reverse=True)
    if "undated" in partitions:
        ordered_partitions.append("undated")
    writer.write("timeline-partitions.json", [{"key": key, "count": len(partitions[key])} for key in ordered_partitions])
    writer.write("entities.json", entity_list)
    writer.write("locations.json", sorted(location_by_id.values(), key=lambda l: l["location_id"]))
    buckets: dict[str, dict] = defaultdict(lambda: {"nodes": {}, "adjacency": defaultdict(list)})
    def bucket_for(node_id: str) -> str:
        return hashlib.sha256(node_id.encode()).hexdigest()[:2]
    for node_id, node in nodes.items():
        buckets[bucket_for(node_id)]["nodes"][node_id] = node
    for edge in edges:
        buckets[bucket_for(edge["source"])]["adjacency"][edge["source"]].append(edge)
        if edge["target"] != edge["source"]:
            buckets[bucket_for(edge["target"])]["adjacency"][edge["target"]].append(edge)
    for prefix, bucket in buckets.items():
        writer.write(f"graph/{prefix}.json", bucket)
    writer.write("graph-manifest.json", {"format": "sharded-adjacency.v1", "node_count": len(nodes),
           "edge_count": len(edges), "edge_types": sorted({edge["type"] for edge in edges}),
           "buckets": sorted(buckets)})
    manifest = {"schema_version": SCHEMA, "generator_version": GENERATOR,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "thread_count": len(threads), "event_count": len(events),
                "entity_count": len(entities), "location_count": len(location_by_id),
                "claim_count": len(claims), "relation_count": len(edges),
                "reused_file_count": writer.reused, "written_file_count": writer.written}
    _json(directory / "manifest.json", manifest)
    validate(directory)
    return manifest


def validate(directory: Path) -> None:
    def read(name: str) -> Any:
        return json.loads((directory / name).read_text(encoding="utf-8"))
    manifest = read("manifest.json")
    if manifest.get("schema_version") != SCHEMA:
        raise ValueError("unsupported dashboard schema")
    ids_by_kind = {}
    details_by_kind = {}
    partitions = read("timeline-partitions.json")
    if not isinstance(partitions, list) or any(not isinstance(p, dict) or not re.fullmatch(r"(?:\d{4}-\d{2}|undated)", str(p.get("key", ""))) or not isinstance(p.get("count"), int) or p["count"] < 0 for p in partitions):
        raise ValueError("invalid timeline partitions")
    if len({p["key"] for p in partitions}) != len(partitions) or sum(p["count"] for p in partitions) != manifest["event_count"]:
        raise ValueError("timeline partition count mismatch")
    timeline = []
    for partition in partitions:
        records = read(f"timeline/{partition['key']}.json")
        if not isinstance(records, list) or len(records) != partition["count"]:
            raise ValueError("invalid timeline partition")
        timeline.extend(records)
    for name, count_key, key, folder in (("threads.json", "thread_count", "thread_id", "threads"),
                                         ("timeline-partitions.json", "event_count", "event_id", "events"),
                                         ("entities.json", "entity_count", "entity_id", "entities")):
        records = timeline if folder == "events" else read(name)
        if not isinstance(records, list) or len(records) != manifest[count_key]:
            raise ValueError(f"invalid {name} count")
        identifiers = set()
        for item in records:
            identifier = item.get(key)
            if not isinstance(identifier, str) or identifier in identifiers or not item.get("canonical_ref"):
                raise ValueError(f"invalid {name} record")
            identifiers.add(identifier)
            detail_file = directory / folder / f"{identifier}.json"
            if not detail_file.is_file():
                raise ValueError(f"missing detail for {identifier}")
            detail = json.loads(detail_file.read_text(encoding="utf-8"))
            if detail.get(key) != identifier or detail.get("canonical_ref") != item["canonical_ref"]:
                raise ValueError(f"invalid {folder} detail {identifier}")
            details_by_kind[identifier] = detail
        ids_by_kind[folder] = identifiers
    for thread in (details_by_kind[tid] for tid in ids_by_kind["threads"]):
        if not set(thread["event_ids"]) <= ids_by_kind["events"] or not set(thread["entity_ids"]) <= ids_by_kind["entities"]:
            raise ValueError("thread has missing event or entity")
        if not isinstance(thread.get("current_state"), dict) or not isinstance(thread.get("open_questions"), list):
            raise ValueError("thread lacks state or questions")
    for event in (details_by_kind[eid] for eid in ids_by_kind["events"]):
        if not set(event["thread_ids"]) <= ids_by_kind["threads"] or not set(event["entity_ids"]) <= ids_by_kind["entities"]:
            raise ValueError("event has missing thread or entity")
        if event["time_precision"] not in {"instant", "day", "month", "year", "range", "unknown"}:
            raise ValueError("event has invalid time precision")
        if event["claim_count"] != len(event["claims"]):
            raise ValueError("event claim count mismatch")
        for claim in event["claims"]:
            if not claim.get("canonical_ref") or claim.get("state") not in {"supported", "uncertain", "analytical", "contested", "corrected", "superseded", "retracted"}:
                raise ValueError("invalid claim")
            if claim.get("source") and not claim["source"].get("canonical_ref"):
                raise ValueError("invalid source reference")
    graph_manifest = read("graph-manifest.json")
    if graph_manifest.get("format") != "sharded-adjacency.v1":
        raise ValueError("invalid graph format")
    graph_nodes = set()
    edge_counts: dict[str, int] = defaultdict(int)
    graph_edges: dict[str, dict] = {}
    for prefix in graph_manifest["buckets"]:
        if not re.fullmatch(r"[a-f0-9]{2}", prefix):
            raise ValueError("invalid graph bucket name")
        bucket = read(f"graph/{prefix}.json")
        for node_id, node in bucket["nodes"].items():
            if hashlib.sha256(node_id.encode()).hexdigest()[:2] != prefix or not node.get("canonical_ref"):
                raise ValueError("invalid graph node")
            graph_nodes.add(node_id)
        for node_id, adjacency in bucket["adjacency"].items():
            if node_id not in bucket["nodes"]:
                raise ValueError("adjacency has missing node")
            for edge in adjacency:
                if node_id not in (edge["source"], edge["target"]) or not edge.get("type"):
                    raise ValueError("invalid graph edge")
                edge_counts[edge["id"]] += 1
                graph_edges[edge["id"]] = edge
    if len(graph_nodes) != graph_manifest["node_count"] or len(graph_edges) != graph_manifest["edge_count"]:
        raise ValueError("graph count mismatch")
    if any(edge["source"] not in graph_nodes or edge["target"] not in graph_nodes or
           edge_counts[edge_id] != (1 if edge["source"] == edge["target"] else 2)
           for edge_id, edge in graph_edges.items()):
        raise ValueError("graph edge has missing endpoint")
    locations = read("locations.json")
    if len(locations) != manifest["location_count"]:
        raise ValueError("invalid location count")
    location_ids = {location["location_id"] for location in locations}
    for location in locations:
        if not set(location["event_ids"]) <= ids_by_kind["events"] or not set(location["thread_ids"]) <= ids_by_kind["threads"]:
            raise ValueError("location references missing object")
        if not location.get("geo_precision") or not location.get("canonical_source_ref"):
            raise ValueError("location lacks precision or provenance")
    for event in (details_by_kind[eid] for eid in ids_by_kind["events"]):
        if not set(event["location_ids"]) <= location_ids:
            raise ValueError("event references missing location")


def publish(db_path: Path, output: Path, *, note_index: Path | None = None,
            location_registry: Path | None = None, vault_dir: Path | None = None) -> dict:
    output.mkdir(parents=True, exist_ok=True, mode=0o700)
    output.chmod(0o700)
    generations = output / "generations"
    generations.mkdir(exist_ok=True, mode=0o700)
    generations.chmod(0o700)
    with tempfile.TemporaryDirectory(prefix="dashboard-snapshot-") as scratch:
        snapshot = Path(scratch) / "source.sqlite"
        source = sqlite3.connect(f"{db_path.resolve().as_uri()}?mode=ro", uri=True)
        target = sqlite3.connect(snapshot)
        try:
            source.backup(target)
        finally:
            source.close()
            target.close()
        digest = hashlib.sha256(snapshot.read_bytes())
        for optional in (note_index, location_registry):
            if optional and optional.exists():
                digest.update(optional.read_bytes())
        if vault_dir:
            note_paths = _thread_note_paths(note_index, vault_dir)
            annotations = _manual_annotations(vault_dir, note_paths)
            digest.update(json.dumps((note_paths, annotations), sort_keys=True).encode())
        else:
            note_paths = _thread_note_paths(note_index, None)
            annotations = {}
        revision = digest.hexdigest()[:20]
        generation_digest = digest.copy()
        generation_digest.update(Path(__file__).read_bytes())
        generation = f"{SCHEMA}-{GENERATOR}-{generation_digest.hexdigest()[:20]}"
        final = generations / generation
        if final.is_dir():
            validate(final)
            manifest = json.loads((final / "manifest.json").read_text(encoding="utf-8"))
        else:
            stage = Path(tempfile.mkdtemp(prefix=".building-", dir=generations))
            try:
                previous = None
                pointer = output / "CURRENT"
                if pointer.is_file():
                    candidate = generations / pointer.read_text(encoding="utf-8").strip()
                    if candidate.is_dir():
                        try:
                            validate(candidate)
                            previous = candidate
                        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
                            pass
                conn = sqlite3.connect(f"{snapshot.resolve().as_uri()}?mode=ro", uri=True)
                conn.row_factory = sqlite3.Row
                try:
                    registry = json.loads(location_registry.read_text(encoding="utf-8")) if location_registry else []
                    manifest = build(conn, stage, note_paths=note_paths, locations=registry, annotations=annotations, previous=previous)
                finally:
                    conn.close()
                manifest["source_revision"] = revision
                _json(stage / "manifest.json", manifest)
                validate(stage)
                stage.rename(final)
                _fsync_directory(generations)
            except Exception:
                shutil.rmtree(stage, ignore_errors=True)
                raise
        pointer = output / ".CURRENT.tmp"
        pointer.write_text(generation + "\n", encoding="utf-8")
        with pointer.open("r+") as stream:
            os.fsync(stream.fileno())
        pointer.replace(output / "CURRENT")
        _fsync_directory(output)
        return manifest


def inspect_canonical(db_path: Path, table: str, identifier: str) -> dict:
    columns = {"threads": "id", "events": "id", "claims": "id", "sources": "id",
               "entities": "id", "open_questions": "id", "relations": "id",
               "thread_current_states": "thread_id"}
    if table not in columns or not identifier or len(identifier) > 200:
        raise ValueError("unsupported canonical reference")
    conn = sqlite3.connect(f"{db_path.resolve().as_uri()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(f"SELECT * FROM {table} WHERE {columns[table]} = ?", (identifier,)).fetchone()
        if row is None:
            raise ValueError("canonical record not found")
        return {"table": table, "id": identifier, "record": dict(row)}
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=Path("var/world-historian/chronicle.sqlite"))
    parser.add_argument("--output", type=Path, default=Path("var/world-historian/dashboard"))
    parser.add_argument("--note-index", type=Path)
    parser.add_argument("--location-registry", type=Path)
    parser.add_argument("--vault", type=Path)
    parser.add_argument("--inspect-table")
    parser.add_argument("--inspect-id")
    args = parser.parse_args()
    if args.inspect_table or args.inspect_id:
        if not args.inspect_table or not args.inspect_id:
            parser.error("--inspect-table and --inspect-id are required together")
        result = inspect_canonical(args.db, args.inspect_table, args.inspect_id)
    else:
        result = publish(args.db, args.output, note_index=args.note_index, location_registry=args.location_registry, vault_dir=args.vault)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
