"""Evidence-preserving synthetic extraction seam and current-trace retrieval.

An extractor passed to ``process_capture`` must return raw JSON bytes. This
module does not supply a vision model; a real extractor must be validated with
annotated photographs before M1 can be claimed.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Callable

from .store import Library, LibrarianError, _json, _new, _now, _unknown_time, validate


TRACE_KINDS = {"highlight", "underline", "circle", "bracket", "margin_note",
               "inline_note", "symbol", "arrow", "page_mark", "unknown_mark"}


def _identity(value: str | None, basis: str) -> dict[str, Any]:
    return {"value": value, "confidence": None, "basis": basis if value else "unknown",
            "status": "resolved" if value else "unresolved"}


def _inside(inner: list[float], outer: list[float]) -> bool:
    return outer[0] <= inner[0] < inner[2] <= outer[2] and outer[1] <= inner[1] < inner[3] <= outer[3]


def _bbox(boxes: list[list[float]]) -> list[float]:
    return [min(box[0] for box in boxes), min(box[1] for box in boxes),
            max(box[2] for box in boxes), max(box[3] for box in boxes)]


def _check_observation(observation: dict[str, Any]) -> None:
    """Cross-element constraints not expressible in the single-object schema."""
    regions = {page["id"]: page for page in observation["pages"]}
    if len(regions) != len(observation["pages"]):
        raise LibrarianError("EXTRACTION_SCHEMA_INVALID", "duplicate page region ID")
    elements = observation["printed_regions"] + observation["marks"] + observation["annotations"] + observation["symbols"]
    by_id = {item["id"]: item for item in elements}
    if len(by_id) != len(elements):
        raise LibrarianError("EXTRACTION_SCHEMA_INVALID", "duplicate detection ID")
    for page in observation["pages"]:
        box = page["bbox"]
        if not (box[0] < box[2] and box[1] < box[3]):
            raise LibrarianError("EXTRACTION_SCHEMA_INVALID", "zero-area page region")
    printed = {item["id"] for item in observation["printed_regions"]}
    for item in elements:
        box = item["bbox"]
        if item["page_region_id"] not in regions or not (box[0] < box[2] and box[1] < box[3]):
            raise LibrarianError("EXTRACTION_SCHEMA_INVALID", "detection has invalid page or bbox")
        if not _inside(box, regions[item["page_region_id"]]["bbox"]):
            raise LibrarianError("EXTRACTION_SCHEMA_INVALID", "detection outside its page region")
        if any(link not in printed for link in item["linked_text_region_ids"]):
            raise LibrarianError("EXTRACTION_SCHEMA_INVALID", "text link target missing")
    for link in observation["links"]:
        if link["from_id"] not in by_id or link["to_id"] not in by_id:
            raise LibrarianError("EXTRACTION_SCHEMA_INVALID", "observation link target missing")


def _spatial(page_box: list[float], trace_box: list[float]) -> tuple[str, str]:
    cx = (trace_box[0] + trace_box[2]) / 2
    cy = (trace_box[1] + trace_box[3]) / 2
    x = (cx - page_box[0]) / (page_box[2] - page_box[0])
    y = (cy - page_box[1]) / (page_box[3] - page_box[1])
    return (["upper", "upper_middle", "middle", "lower_middle", "lower"][min(4, int(y * 5))],
            ["left", "center", "right"][min(2, int(x * 3))])


def process_capture(lib: Library, owner_id: str, capture_id: str,
                    extractor: Callable[[bytes], bytes], *, extractor_version: str = "synthetic-v1",
                    normalizer_version: str = "physical-v1") -> list[dict[str, Any]]:
    """Run one captured original through a replaceable extractor and normalize.

    A persisted successful run is reused on retry. Deliberate reprocessing
    with another version currently stops at reconciliation rather than
    overwriting any user correction.
    """
    capture = lib.get(owner_id, "PageCapture", capture_id)
    old = lib.db.execute("SELECT body FROM records WHERE owner_id=? AND model='ProcessingRun' AND current=1",
                         (owner_id,)).fetchall()
    for row in old:
        run = json.loads(row["body"])
        if run["capture_id"] == capture_id and run["outcome"] in {"success", "partial"}:
            if run["extractor_version"] != extractor_version or run["normalizer_version"] != normalizer_version:
                raise LibrarianError("RECONCILIATION_REQUIRED", "reprocessing needs trace reconciliation")
            return _traces_for_capture(lib, owner_id, capture_id)

    original = lib.read_original(owner_id, capture_id)
    raw = extractor(original)
    if not isinstance(raw, bytes):
        raise LibrarianError("EXTRACTION_SCHEMA_INVALID", "extractor must return raw JSON bytes")
    raw_asset = lib._save_object(raw, "application/json")
    run_id = _new("run")
    try:
        output = json.loads(raw)
        if not isinstance(output, dict):
            raise ValueError("root must be an object")
        observation = {"object_type": "PageObservation", "schema_version": "0.1.0",
                       "id": _new("observation"), "owner_id": owner_id,
                       "created_at": _now(), "capture_id": capture_id,
                       "processing_run_id": run_id, "extractor": extractor_version,
                       "raw_output_asset": raw_asset, **output}
        validate("PageObservation", observation)
        _check_observation(observation)
    except (json.JSONDecodeError, ValueError, KeyError, TypeError, LibrarianError) as error:
        with lib.db:
            lib.db.execute("INSERT INTO extractor_attempts VALUES(?,?,?,?,?,?)",
                           (owner_id, capture_id, run_id, _json(raw_asset), "failed", "EXTRACTION_SCHEMA_INVALID"))
        raise LibrarianError("EXTRACTION_SCHEMA_INVALID", f"extractor output invalid: {error}") from error

    context = capture["submitted_context"]
    session_id = context["session_id"]
    basis = "explicit_session" if session_id else "unknown"
    if not session_id:
        inferred = lib.db.execute("SELECT session_id,basis FROM capture_context WHERE owner_id=? AND capture_id=?",
                                  (owner_id, capture_id)).fetchone()
        if inferred:
            session_id, basis = inferred["session_id"], inferred["basis"]
    work_id = context["work_id"]
    edition_id = context["edition_id"]
    book_instance_id = context["book_instance_id"]
    if session_id:
        session = lib.get(owner_id, "ReadingSession", session_id)
        if session["status"] == "closed":
            raise LibrarianError("CONTEXT_CONFLICT", "closed session cannot silently receive captures")
        for key, value in (("work_id", work_id), ("edition_id", edition_id),
                           ("book_instance_id", book_instance_id)):
            if value and session[key] and value != session[key]:
                raise LibrarianError("CONTEXT_CONFLICT", "explicit session conflicts with submitted context")
        work_id = work_id or session["work_id"]
        edition_id = edition_id or session["edition_id"]
        book_instance_id = book_instance_id or session["book_instance_id"]
    if book_instance_id:
        instance = lib.get(owner_id, "BookInstance", book_instance_id)
        if edition_id and edition_id != instance["edition_id"]:
            raise LibrarianError("CONTEXT_CONFLICT", "instance and edition conflict")
        edition_id = instance["edition_id"]
    if edition_id:
        edition = lib.get(owner_id, "Edition", edition_id)
        if work_id and work_id != edition["work_id"]:
            raise LibrarianError("CONTEXT_CONFLICT", "edition and work conflict")
        work_id = edition["work_id"]
    state = "resolved" if all((session_id, work_id, edition_id, book_instance_id)) else "unresolved"
    resolution = {"object_type": "CaptureResolution", "schema_version": "0.1.0",
                  "id": _new("resolution"), "owner_id": owner_id, "created_at": _now(),
                  "capture_id": capture_id, "session": _identity(session_id, basis),
                  "work": _identity(work_id, basis),
                  "edition": _identity(edition_id, basis),
                  "book_instance": _identity(book_instance_id, basis),
                  "pages": observation["pages"], "revision": 1,
                  "supersedes_revision": None}
    validate("CaptureResolution", resolution)
    traces = normalize(capture, observation, resolution, state, normalizer_version)
    run = {"object_type": "ProcessingRun", "schema_version": "0.1.0",
           "id": run_id, "owner_id": owner_id, "created_at": _now(),
           "capture_id": capture_id, "checkpoint": "NORMALIZED",
           "outcome": "success" if state == "resolved" and all(p["page"]["status"] == "resolved" for p in observation["pages"]) else "partial",
           "issues": ([] if state == "resolved" else ["NEEDS_BOOK_RESOLUTION"]) +
                     (["NEEDS_PAGE_RESOLUTION"] if any(p["page"]["status"] != "resolved" for p in observation["pages"]) else []),
           "extractor_version": extractor_version,
           "normalizer_version": normalizer_version,
           "revision": 1, "supersedes_revision": None}
    with lib.db:
        lib._put(run)
        lib._put(observation)
        lib._put(resolution)
        lib.db.execute("INSERT INTO extractor_attempts VALUES(?,?,?,?,?,?)",
                       (owner_id, capture_id, run_id, _json(raw_asset), "success", None))
        for trace in traces:
            lib._put(trace)
            _index_trace(lib, trace)
            lib._event(owner_id, "reading.trace.created", "reading_trace", trace["id"], 1,
                       {"trace_id": trace["id"], "revision": 1, "medium": "physical",
                        "book_instance_id": trace["book_instance_id"]}, run_id)
        lib._event(owner_id, "reading.capture.processed", "processing_run", run_id, 1,
                   {"capture_id": capture_id, "processing_run_id": run_id,
                    "outcome": run["outcome"], "trace_refs":
                    [{"trace_id": t["id"], "revision": 1} for t in traces],
                    "issues": run["issues"]}, run_id)
    return traces


def normalize(capture: dict[str, Any], observation: dict[str, Any],
              resolution: dict[str, Any], context_state: str,
              normalizer_version: str) -> list[dict[str, Any]]:
    """Pure deterministic observation-to-trace projection for one capture."""
    pages = {p["id"]: p for p in observation["pages"]}
    printed = {p["id"]: p for p in observation["printed_regions"]}
    marks = observation["marks"] + observation["annotations"] + observation["symbols"]
    by_id = {item["id"]: item for item in marks}
    parent = {item["id"]: item["id"] for item in marks}

    def root(identifier: str) -> str:
        while parent[identifier] != identifier:
            identifier = parent[identifier]
        return identifier

    for link in observation["links"]:
        left, right = link["from_id"], link["to_id"]
        if (link["kind"] in {"annotates", "continues"}
                and link["confidence"] is not None and link["confidence"] >= .90
                and left in by_id and right in by_id
                and by_id[left]["page_region_id"] == by_id[right]["page_region_id"]):
            parent[root(right)] = root(left)
    groups: dict[str, list[dict[str, Any]]] = {}
    for mark in marks:
        groups.setdefault(root(mark["id"]), []).append(mark)
    result = []
    for group in groups.values():
        page = pages[group[0]["page_region_id"]]
        linked_ids = {identifier for mark in group
                      if mark["link_confidence"] is not None and mark["link_confidence"] >= .90
                      for identifier in mark["linked_text_region_ids"]
                      if identifier in printed and printed[identifier]["page_region_id"] == page["id"]}
        linked = [item for item in observation["printed_regions"] if item["id"] in linked_ids]
        boxes = [mark["bbox"] for mark in group] + [item["bbox"] for item in linked]
        box = _bbox(boxes)
        vertical, horizontal = _spatial(page["bbox"], box)
        printed_text = "\n".join(item["text"]["text"] for item in linked
                                  if item["text"] and item["text"]["text"]) or None
        scores = [item["text"]["confidence"] for item in linked if item["text"]]
        text_confidence = min(scores) if scores and len(scores) == len(linked) and all(s is not None for s in scores) else None
        notes = [mark["text"] for mark in group if mark in observation["annotations"] and mark["text"] and mark["text"]["text"]]
        annotation = ({"text": "\n".join(note["text"] for note in notes),
                       "confidence": min(note["confidence"] for note in notes)
                       if all(note["confidence"] is not None for note in notes) else None,
                       "basis": "vision"} if notes else None)
        source_ids = sorted([mark["id"] for mark in group] + [item["id"] for item in linked])
        key = _json([capture["owner_id"], capture["origin"], observation["id"], source_ids])
        trace_id = "rt_" + hashlib.sha256(key.encode()).hexdigest()[:32]
        kinds = list(dict.fromkeys(mark["kind"] if mark["kind"] in TRACE_KINDS else "unknown_mark"
                                   for mark in group))
        symbols = [mark["text"]["text"] for mark in group if mark in observation["symbols"]
                   and mark["text"] and mark["text"]["text"]]
        trace = {"object_type": "ReadingTrace", "schema_version": "0.1.0",
                 "id": trace_id, "owner_id": capture["owner_id"],
                 "created_at": observation["created_at"], "revision": 1,
                 "supersedes_revision": None, "status": "active",
                 "context_state": context_state, "work_id": resolution["work"]["value"],
                 "edition_id": resolution["edition"]["value"],
                 "book_instance_id": resolution["book_instance"]["value"],
                 "session_id": resolution["session"]["value"], "medium": "physical",
                 "location": {"kind": "physical", "page_region_id": page["id"],
                              "page": page["page"]["value"], "page_bbox": page["bbox"],
                              "bbox": box, "side": page["side"],
                              "vertical": vertical, "horizontal": horizontal},
                 "trace_types": kinds,
                 "content": {"printed_text": {"text": printed_text,
                                                "confidence": text_confidence,
                                                "basis": "vision" if printed_text else "unknown"},
                             "annotation": annotation or {"text": None, "confidence": None,
                                                          "basis": "unknown"},
                             "symbols": symbols},
                 "source": {"kind": "physical", "capture_id": capture["id"],
                            "observation_id": observation["id"],
                            "resolution_id": resolution["id"],
                            "resolution_revision": 1, "detection_ids": source_ids},
                 "provenance": [capture["asset"], observation["raw_output_asset"]],
                 "confidence": {"book_resolution": None,
                                "page_number": page["page"]["confidence"]},
                 "marked_at": _unknown_time(),
                 "attribution": {"mark_author": "unknown", "basis": "unknown"},
                 "intent_signals": [],
                 "review": {"required": False, "state": "none", "reason": None}}
        validate("ReadingTrace", trace)
        result.append(trace)
    return result


def _index_trace(lib: Library, trace: dict[str, Any]) -> None:
    lib.db.execute("INSERT OR REPLACE INTO trace_index VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                   (trace["owner_id"], trace["id"], trace["revision"],
                    trace["content"]["printed_text"]["text"] or "",
                    trace["content"]["annotation"]["text"] or "",
                    trace["work_id"], trace["edition_id"], trace["book_instance_id"],
                    trace["session_id"], trace["medium"], trace["context_state"],
                    _json(trace["trace_types"])))


def _traces_for_capture(lib: Library, owner_id: str, capture_id: str) -> list[dict[str, Any]]:
    rows = lib.db.execute("SELECT body FROM records WHERE owner_id=? AND model='ReadingTrace' AND current=1 ORDER BY rowid",
                          (owner_id,)).fetchall()
    return [trace for row in rows if (trace := json.loads(row["body"]))["source"]["capture_id"] == capture_id]


def rebuild_index(lib: Library, owner_id: str) -> int:
    traces = [json.loads(row[0]) for row in lib.db.execute(
        "SELECT body FROM records WHERE owner_id=? AND model='ReadingTrace' AND current=1", (owner_id,))]
    with lib.db:
        lib.db.execute("DELETE FROM trace_index WHERE owner_id=?", (owner_id,))
        for trace in traces:
            if trace["status"] == "active":
                _index_trace(lib, trace)
    return len(traces)


def correct_trace(lib: Library, owner_id: str, trace_id: str, expected_revision: int,
                  *, printed_text: object = ...,
                  annotation: object = ...,
                  reason: str) -> dict[str, Any]:
    """Append a user correction while retaining exact original evidence refs.

    Omitted fields stay as they were; explicit None changes a field to unknown.
    """
    if not reason.strip() or (printed_text is ... and annotation is ...):
        raise LibrarianError("VALIDATION_FAILED", "correction needs a field and reason")
    prior = lib.get(owner_id, "ReadingTrace", trace_id)
    if prior["revision"] != expected_revision:
        raise LibrarianError("REVISION_CONFLICT", "trace revision changed")
    revised = json.loads(_json(prior))
    revised["revision"] += 1
    revised["supersedes_revision"] = expected_revision
    revised["created_at"] = _now()
    for field, value in (("printed_text", printed_text), ("annotation", annotation)):
        if value is ...:
            continue
        if value is not None and (not isinstance(value, str) or not value.strip()):
            raise LibrarianError("VALIDATION_FAILED", "correction text must be nonempty or null")
        revised["content"][field] = {"text": value, "confidence": None,
                                      "basis": "user_statement" if value is not None else "unknown"}
    validate("ReadingTrace", revised)
    with lib.db:
        lib._put(revised)
        _index_trace(lib, revised)
        lib._event(owner_id, "reading.trace.corrected", "reading_trace", trace_id,
                   revised["revision"], {"trace_id": trace_id,
                   "previous_revision": expected_revision,
                   "revision": revised["revision"], "reason": reason}, trace_id)
    return revised


def search(lib: Library, owner_id: str, query: str, *, include_unresolved: bool = False,
           work_id: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
    if not owner_id or not query.strip() or not 1 <= limit <= 100:
        raise LibrarianError("VALIDATION_FAILED", "owner, query and limit required")
    escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    rows = lib.db.execute("SELECT trace_id,revision FROM trace_index WHERE owner_id=? AND (? OR context_state='resolved') AND (? IS NULL OR work_id=?) AND (printed_text LIKE ? ESCAPE '\\' OR annotation LIKE ? ESCAPE '\\') ORDER BY rowid DESC LIMIT ?",
                          (owner_id, include_unresolved, work_id, work_id,
                           f"%{escaped}%", f"%{escaped}%", limit)).fetchall()
    return [lib.get(owner_id, "ReadingTrace", row["trace_id"]) for row in rows]


def search_response(lib: Library, request: dict[str, Any], *, trusted_owner_id: str) -> dict[str, Any]:
    """Return the shared provenance-first SearchResponse contract."""
    validate("SearchRequest", request)
    if request["owner_id"] != trusted_owner_id:
        raise LibrarianError("UNAUTHORIZED", "search owner differs from trusted identity")
    filters = request["filters"]
    cursor = request["cursor"]
    if cursor is not None and (not cursor.isdecimal() or int(cursor) > 1_000_000):
        raise LibrarianError("VALIDATION_FAILED", "invalid search cursor")
    offset = int(cursor or 0)
    terms = ["owner_id=?", "(printed_text LIKE ? ESCAPE '\\' OR annotation LIKE ? ESCAPE '\\')"]
    escaped = request["query"].replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    params: list[Any] = [trusted_owner_id, f"%{escaped}%", f"%{escaped}%"]
    if not filters["include_unresolved"]:
        terms.append("context_state='resolved'")
    for column in ("work_id", "edition_id", "book_instance_id", "session_id", "medium"):
        if filters[column] is not None:
            terms.append(f"{column}=?")
            params.append(filters[column])
    if filters["trace_types"]:
        terms.append("EXISTS (SELECT 1 FROM json_each(trace_types) WHERE value IN (" +
                     ",".join("?" for _ in filters["trace_types"]) + "))")
        params.extend(filters["trace_types"])
    sql = ("SELECT trace_id FROM trace_index WHERE " + " AND ".join(terms) +
           " ORDER BY rowid DESC LIMIT ? OFFSET ?")
    rows = lib.db.execute(sql, (*params, request["limit"] + 1, offset)).fetchall()
    hits = []
    for row in rows[:request["limit"]]:
        trace = lib.get(trusted_owner_id, "ReadingTrace", row["trace_id"])
        title = (lib.get(trusted_owner_id, "Work", trace["work_id"])["title"]
                 if trace["work_id"] else None)
        hit = {"trace_id": trace["id"], "revision": trace["revision"],
               "medium": trace["medium"], "context_state": trace["context_state"],
               "title": title, "location": trace["location"],
               "content": trace["content"], "channels": ["lexical"],
               "rank_score": 1.0, "evidence": trace["provenance"],
               "warnings": (["book unresolved"] if trace["context_state"] != "resolved" else [])}
        validate("SearchHit", hit)
        hits.append(hit)
    stale = lib.db.execute(
        "SELECT COUNT(*) FROM records r LEFT JOIN trace_index i "
        "ON i.owner_id=r.owner_id AND i.trace_id=r.id "
        "WHERE r.owner_id=? AND r.model='ReadingTrace' AND r.current=1 "
        "AND json_extract(r.body,'$.status')='active' "
        "AND (i.trace_id IS NULL OR i.revision<>r.revision)",
        (trusted_owner_id,)).fetchone()[0]
    current = lib.db.execute("SELECT COUNT(*) FROM records WHERE owner_id=? AND model='ReadingTrace' AND current=1 AND json_extract(body,'$.status')='active'",
                             (trusted_owner_id,)).fetchone()[0]
    indexed = lib.db.execute("SELECT COUNT(*) FROM trace_index WHERE owner_id=?",
                             (trusted_owner_id,)).fetchone()[0]
    response = {"hits": hits,
                "next_cursor": str(offset + request["limit"]) if len(rows) > request["limit"] else None,
                "index_state": "ready" if current == indexed and stale == 0 else "lagging"}
    validate("SearchResponse", response)
    return response
