from __future__ import annotations

import json
import io
from pathlib import Path

import pytest
from PIL import Image

from agents.librarian.runtime.pipeline import correct_trace, process_capture, rebuild_index, resolve_capture, search
from agents.librarian.runtime.store import Library, LibrarianError, validate


def _detection(identifier: str, kind: str, text: str | None,
               linked: list[str] | None = None) -> dict:
    return {"id": identifier, "page_region_id": "page_left",
            "bbox": [.1, .1, .5, .2] if kind == "printed" else [.1, .18, .5, .21],
            "kind": kind,
            "text": {"text": text, "confidence": .85, "basis": "vision"} if text else None,
            "confidence": .9, "linked_text_region_ids": linked or [],
            "link_confidence": .95 if linked else None}


def _output() -> bytes:
    return json.dumps({
        "image_space": {"width": 1000, "height": 1400,
                        "basis": "exif_oriented_original"},
        "pages": [{"id": "page_left", "bbox": [0, 0, 1, 1], "side": "unknown",
                   "page": {"value": {"label": "171", "number": 171,
                                      "scheme": "arabic"}, "confidence": .9,
                            "basis": "vision", "status": "resolved"}}],
        "printed_regions": [_detection("printed_1", "printed", "Weber and Parsons")],
        "marks": [_detection("mark_1", "underline", None, ["printed_1"])],
        "annotations": [_detection("note_1", "margin_note", "Parsons?")],
        "symbols": [], "links": [], "warnings": []
    }).encode()


def _photo() -> bytes:
    stream = io.BytesIO()
    Image.new("RGB", (1000, 1400), "white").save(stream, format="PNG")
    return stream.getvalue()


def _rotated_photo() -> bytes:
    stream = io.BytesIO()
    exif = Image.Exif()
    exif[274] = 6  # EXIF rotation swaps the display dimensions.
    Image.new("RGB", (1000, 1400), "white").save(stream, format="JPEG", exif=exif)
    return stream.getvalue()


def test_synthetic_observation_to_provenance_search_and_rebuild(tmp_path: Path):
    with Library(tmp_path) as lib:
        receipt = lib.ingest("owner_a", transport="gateway", account_id="account",
                             conversation_id="chat", source_event_id="message-1",
                             attachments=[{"source_item_id": "image-1",
                                           "mime_type": "image/png", "data": _photo()}],
                             idempotency_key="command-1")
        capture_id = receipt["capture_ids"][0]
        calls = []
        def extractor(raw: bytes) -> bytes:
            calls.append(raw)
            return _output()
        traces = process_capture(lib, "owner_a", capture_id, extractor)
        assert len(traces) == 2
        assert traces[0]["content"]["printed_text"]["text"] == "Weber and Parsons"
        assert traces[1]["content"]["annotation"]["text"] == "Parsons?"
        assert traces[0]["location"]["page"]["number"] == 171
        assert traces[0]["attribution"]["mark_author"] == "unknown"
        assert lib.read_trace_evidence("owner_a", traces[0]["id"])[0] == _photo()
        assert all(t["source"]["capture_id"] == capture_id for t in traces)
        assert search(lib, "owner_a", "Parsons") == []  # unresolved stays out of default results
        hits = search(lib, "owner_a", "Parsons", include_unresolved=True)
        assert {h["id"] for h in hits} == {t["id"] for t in traces}
        assert search(lib, "owner_b", "Parsons", include_unresolved=True) == []
        assert process_capture(lib, "owner_a", capture_id, extractor) == traces
        assert len(calls) == 1
        lib.db.execute("DELETE FROM trace_index")
        lib.db.commit()
        assert rebuild_index(lib, "owner_a") == 2
        assert len(search(lib, "owner_a", "Parsons", include_unresolved=True)) == 2
        assert [e["event"] for e in lib.pending_events("owner_a")].count("reading.trace.created") == 2


def test_invalid_extraction_keeps_raw_output_without_trace(tmp_path: Path):
    with Library(tmp_path) as lib:
        receipt = lib.ingest("owner_a", transport="gateway", account_id="a",
                             conversation_id="c", source_event_id="m",
                             attachments=[{"source_item_id": "i", "mime_type": "image/png",
                                           "data": _photo()}], idempotency_key="k")
        with pytest.raises(LibrarianError) as err:
            process_capture(lib, "owner_a", receipt["capture_ids"][0], lambda _: b"{broken")
        assert err.value.code == "EXTRACTION_SCHEMA_INVALID"
        row = lib.db.execute("SELECT raw_asset,error_code FROM extractor_attempts").fetchone()
        assert row["error_code"] == "EXTRACTION_SCHEMA_INVALID"
        ref = json.loads(row["raw_asset"])
        assert (tmp_path / ref["object_key"]).read_bytes() == b"{broken"
        failed = lib.db.execute("SELECT body FROM records WHERE model='ProcessingRun'").fetchone()[0]
        assert json.loads(failed)["outcome"] == "failed"
        assert lib.db.execute("SELECT COUNT(*) FROM records WHERE model='ReadingTrace'").fetchone()[0] == 0


def test_invalid_cross_page_link_is_rejected(tmp_path: Path):
    output = json.loads(_output())
    output["marks"][0]["linked_text_region_ids"] = ["missing"]
    with Library(tmp_path) as lib:
        receipt = lib.ingest("owner_a", transport="gateway", account_id="a",
                             conversation_id="c", source_event_id="m",
                             attachments=[{"source_item_id": "i", "mime_type": "image/png",
                                           "data": _photo()}], idempotency_key="k")
        with pytest.raises(LibrarianError) as err:
            process_capture(lib, "owner_a", receipt["capture_ids"][0],
                            lambda _: json.dumps(output).encode())
        assert err.value.code == "EXTRACTION_SCHEMA_INVALID"


def test_conflicting_explicit_session_keeps_original_and_observation(tmp_path: Path):
    now = "2026-09-28T00:00:00+00:00"
    with Library(tmp_path) as lib:
        for name in ("one", "other"):
            lib.register("owner_a", {"object_type": "Work", "schema_version": "0.1.0",
                         "id": f"work_{name}", "owner_id": "owner_a", "created_at": now,
                         "title": f"Synthetic {name}", "original_title": None,
                         "authors": [], "identifiers": [], "revision": 1,
                         "supersedes_revision": None})
        session = lib.start_session("owner_a")
        # The session is explicitly attached to one work; a submitted different
        # work is retained on the immutable capture rather than reassigned.
        current = lib.get("owner_a", "ReadingSession", session["id"])
        current["work_id"] = "work_one"
        current["revision"] = 2
        current["supersedes_revision"] = 1
        with lib.transaction():
            lib._put(current)
        receipt = lib.ingest("owner_a", transport="gateway", account_id="a",
                             conversation_id="c", source_event_id="m",
                             attachments=[{"source_item_id": "i", "mime_type": "image/png",
                                           "data": _photo()}], idempotency_key="k",
                             submitted_context={"session_id": session["id"],
                                                "work_id": "work_other"})
        capture_id = receipt["capture_ids"][0]
        with pytest.raises(LibrarianError) as error:
            process_capture(lib, "owner_a", capture_id, lambda _: _output())
        assert error.value.code == "CONTEXT_CONFLICT"
        assert lib.read_original("owner_a", capture_id) == _photo()
        run = json.loads(lib.db.execute("SELECT body FROM records WHERE model='ProcessingRun'").fetchone()[0])
        assert run["outcome"] == "failed" and "CONTEXT_CONFLICT" in run["issues"]
        observation = json.loads(lib.db.execute("SELECT body FROM records WHERE model='PageObservation'").fetchone()[0])
        assert observation["capture_id"] == capture_id
        attempt = lib.db.execute("SELECT raw_asset,error_code FROM extractor_attempts").fetchone()
        assert attempt["error_code"] == "CONTEXT_CONFLICT"
        assert (tmp_path / json.loads(attempt["raw_asset"])["object_key"]).read_bytes() == _output()
        assert lib.db.execute("SELECT COUNT(*) FROM records WHERE model='ReadingTrace'").fetchone()[0] == 0
        resolved = resolve_capture(lib, "owner_a", capture_id, None,
                                   session_id=session["id"], work_id="work_one")
        assert resolved["revision"] == 1
        traces = process_capture(lib, "owner_a", capture_id, lambda _: _output())
        assert len(traces) == 2
        assert all(trace["work_id"] == "work_one" for trace in traces)
        assert lib.get("owner_a", "PageObservation", observation["id"]) == observation

        second = lib.ingest("owner_a", transport="gateway", account_id="a",
                            conversation_id="c", source_event_id="m2",
                            attachments=[{"source_item_id": "i2", "mime_type": "image/png",
                                          "data": _photo()}], idempotency_key="k2",
                            submitted_context={"session_id": session["id"]})
        title_output = json.loads(_output())
        title_output["visible_title"] = {"text": "Synthetic other", "confidence": .95,
                                         "basis": "vision"}
        second_id = second["capture_ids"][0]
        with pytest.raises(LibrarianError) as title_error:
            process_capture(lib, "owner_a", second_id,
                            lambda _: json.dumps(title_output).encode())
        assert title_error.value.code == "CONTEXT_CONFLICT"
        assert lib.read_original("owner_a", second_id) == _photo()
        resolve_capture(lib, "owner_a", second_id, None,
                        session_id=session["id"], work_id="work_one")
        confirmed = process_capture(lib, "owner_a", second_id,
                                    lambda _: json.dumps(title_output).encode())
        assert len(confirmed) == 2
        title_output["visible_title"]["confidence"] = .7
        third = lib.ingest("owner_a", transport="gateway", account_id="a",
                           conversation_id="c", source_event_id="m3",
                           attachments=[{"source_item_id": "i3", "mime_type": "image/png",
                                         "data": _photo()}], idempotency_key="k3",
                           submitted_context={"session_id": session["id"]})
        low_confidence = process_capture(lib, "owner_a", third["capture_ids"][0],
                                         lambda _: json.dumps(title_output).encode())
        assert len(low_confidence) == 2


def test_explicit_annotation_link_groups_trace_without_inventing_authorship(tmp_path: Path):
    output = json.loads(_output())
    output["links"] = [{"from_id": "mark_1", "to_id": "note_1",
                        "kind": "annotates", "confidence": .95}]
    with Library(tmp_path) as lib:
        receipt = lib.ingest("owner_a", transport="gateway", account_id="a",
                             conversation_id="c", source_event_id="m",
                             attachments=[{"source_item_id": "i", "mime_type": "image/png",
                                           "data": _photo()}], idempotency_key="k")
        traces = process_capture(lib, "owner_a", receipt["capture_ids"][0],
                                 lambda _: json.dumps(output).encode())
        assert len(traces) == 1
        assert traces[0]["trace_types"] == ["underline", "margin_note"]
        assert traces[0]["content"]["annotation"]["text"] == "Parsons?"
        assert traces[0]["attribution"]["mark_author"] == "unknown"


def test_correction_adds_revision_and_keeps_evidence(tmp_path: Path):
    with Library(tmp_path) as lib:
        receipt = lib.ingest("owner_a", transport="gateway", account_id="a",
                             conversation_id="c", source_event_id="m",
                             attachments=[{"source_item_id": "i", "mime_type": "image/png",
                                           "data": _photo()}], idempotency_key="k")
        trace = process_capture(lib, "owner_a", receipt["capture_ids"][0],
                                lambda _: _output())[1]
        old_observation = trace["source"]["observation_id"]
        changed = correct_trace(lib, "owner_a", trace["id"], 1,
                                annotation="Parsons!", reason="user correction")
        assert changed["revision"] == 2
        assert changed["source"]["observation_id"] == old_observation
        assert changed["provenance"] == trace["provenance"]
        assert changed["content"]["annotation"]["basis"] == "user_statement"
        history = lib.db.execute("SELECT body FROM records WHERE model='ReadingTrace' AND id=? ORDER BY revision",
                                 (trace["id"],)).fetchall()
        assert json.loads(history[0]["body"])["content"]["annotation"]["text"] == "Parsons?"
        assert search(lib, "owner_a", "Parsons!", include_unresolved=True)[0]["revision"] == 2
        assert not search(lib, "owner_a", "Parsons?", include_unresolved=True)
        with pytest.raises(LibrarianError) as err:
            correct_trace(lib, "owner_a", trace["id"], 1,
                          annotation="stale", reason="stale request")
        assert err.value.code == "REVISION_CONFLICT"
        assert [e["event"] for e in lib.pending_events("owner_a")].count("reading.trace.corrected") == 1


def test_explicit_session_yields_resolved_trace_and_default_search(tmp_path: Path):
    created = "2026-09-28T00:00:00+00:00"
    with Library(tmp_path) as lib:
        lib.register("owner_a", {"object_type": "Work", "schema_version": "0.1.0",
                   "id": "work_one", "owner_id": "owner_a", "created_at": created,
                   "title": "Synthetic book", "original_title": None, "authors": [],
                   "identifiers": [], "revision": 1, "supersedes_revision": None})
        lib.register("owner_a", {"object_type": "Edition", "schema_version": "0.1.0",
                   "id": "edition_one", "owner_id": "owner_a", "created_at": created,
                   "work_id": "work_one", "edition_label": None, "publisher": None,
                   "publication_year": None, "isbn": {"isbn13": None, "isbn10": None},
                   "language": None, "page_count": None, "volume_label": None,
                   "revision": 1, "supersedes_revision": None})
        lib.register("owner_a", {"object_type": "BookInstance", "schema_version": "0.1.0",
                   "id": "bookinst_one", "owner_id": "owner_a", "created_at": created,
                   "edition_id": "edition_one", "medium": "physical",
                   "acquired_at": {"value": None, "confidence": None, "basis": "unknown"},
                   "ownership_status": "owned", "physical": {"qr_id": None, "shelf": None},
                   "reading_status": {"state": "reading", "current_page": None,
                                      "progress_evidence_ref": None},
                   "revision": 1, "supersedes_revision": None})
        session = lib.start_session("owner_a", "bookinst_one", scope=("gateway", "a", "c"))
        receipt = lib.ingest("owner_a", transport="gateway", account_id="a",
                             conversation_id="c", source_event_id="m",
                             attachments=[{"source_item_id": "i", "mime_type": "image/png",
                                           "data": _photo()}], idempotency_key="k",
                             submitted_context={"session_id": session["id"]})
        traces = process_capture(lib, "owner_a", receipt["capture_ids"][0],
                                 lambda _: _output())
        assert all(t["context_state"] == "resolved" for t in traces)
        assert all(t["work_id"] == "work_one" and t["edition_id"] == "edition_one"
                   and t["book_instance_id"] == "bookinst_one" for t in traces)
        assert len(search(lib, "owner_a", "Parsons")) == 2
        inferred = lib.ingest("owner_a", transport="gateway", account_id="a",
                              conversation_id="c", source_event_id="m2",
                              attachments=[{"source_item_id": "i", "mime_type": "image/png",
                                            "data": _photo()}], idempotency_key="k2")
        inferred_traces = process_capture(lib, "owner_a", inferred["capture_ids"][0],
                                          lambda _: _output())
        assert all(t["session_id"] == session["id"] and t["context_state"] == "resolved"
                   for t in inferred_traces)
        original_capture = lib.get("owner_a", "PageCapture", inferred["capture_ids"][0])
        original_observation = lib.get("owner_a", "PageObservation",
                                       inferred_traces[0]["source"]["observation_id"])
        old_resolution = lib.get("owner_a", "CaptureResolution",
                                 inferred_traces[0]["source"]["resolution_id"])
        pages = json.loads(json.dumps(old_resolution["pages"]))
        pages[0]["page"] = {"value": {"label": "172", "number": 172,
                                       "scheme": "arabic"}, "confidence": None,
                            "basis": "user_statement", "status": "resolved"}
        resolution = resolve_capture(lib, "owner_a", inferred["capture_ids"][0], 1,
                                     pages=pages)
        assert resolution["revision"] == 2
        revised = lib.get("owner_a", "ReadingTrace", inferred_traces[0]["id"])
        assert revised["revision"] == 2 and revised["location"]["page"]["number"] == 172
        assert revised["source"]["resolution_revision"] == 2
        assert lib.get("owner_a", "PageCapture", inferred["capture_ids"][0]) == original_capture
        assert lib.get("owner_a", "PageObservation", original_observation["id"]) == original_observation
        with pytest.raises(LibrarianError) as error:
            resolve_capture(lib, "owner_a", inferred["capture_ids"][0], 1, pages=pages)
        assert error.value.code == "REVISION_CONFLICT"

        unresolved_receipt = lib.ingest("owner_a", transport="gateway", account_id="a",
                                        conversation_id="different-chat", source_event_id="m3",
                                        attachments=[{"source_item_id": "i", "mime_type": "image/png",
                                                      "data": _photo()}], idempotency_key="k3")
        unresolved_id = unresolved_receipt["capture_ids"][0]
        unresolved_trace = process_capture(lib, "owner_a", unresolved_id, lambda _: _output())[0]
        assert unresolved_trace["context_state"] == "unresolved"
        resolve_capture(lib, "owner_a", unresolved_id, 1, session_id=session["id"])
        assert lib.get("owner_a", "ReadingTrace", unresolved_trace["id"])["context_state"] == "resolved"


def test_trace_semantics_reject_fake_resolved_context_and_review(tmp_path: Path):
    with Library(tmp_path) as lib:
        receipt = lib.ingest("owner_a", transport="gateway", account_id="a",
                             conversation_id="c", source_event_id="m",
                             attachments=[{"source_item_id": "i", "mime_type": "image/png",
                                           "data": _photo()}], idempotency_key="k")
        trace = process_capture(lib, "owner_a", receipt["capture_ids"][0],
                                lambda _: _output())[0]
        false_resolution = dict(trace, context_state="resolved")
        with pytest.raises(LibrarianError, match="full chain"):
            validate("ReadingTrace", false_resolution)
        false_review = json.loads(json.dumps(trace))
        false_review["review"] = {"required": False, "state": "pending", "reason": "unclear"}
        with pytest.raises(LibrarianError, match="pending review"):
            validate("ReadingTrace", false_review)


def test_observation_dimensions_follow_exif_oriented_original(tmp_path: Path):
    with Library(tmp_path) as lib:
        receipt = lib.ingest("owner_a", transport="gateway", account_id="a",
                             conversation_id="c", source_event_id="m",
                             attachments=[{"source_item_id": "i", "mime_type": "image/jpeg",
                                           "data": _rotated_photo()}], idempotency_key="k")
        capture_id = receipt["capture_ids"][0]
        with pytest.raises(LibrarianError, match="EXIF-oriented original"):
            process_capture(lib, "owner_a", capture_id, lambda _: _output())
        raw_ref = json.loads(lib.db.execute("SELECT raw_asset FROM extractor_attempts").fetchone()[0])
        assert (tmp_path / raw_ref["object_key"]).read_bytes() == _output()
        output = json.loads(_output())
        output["image_space"].update(width=1400, height=1000)
        assert len(process_capture(lib, "owner_a", capture_id,
                                   lambda _: json.dumps(output).encode())) == 2


def test_opt_in_symbol_signal_and_important_content_review(tmp_path: Path):
    output = json.loads(_output())
    output["printed_regions"][0]["text"]["confidence"] = .5
    symbol = _detection("symbol_1", "symbol", "!!")
    symbol["text"]["confidence"] = .95
    symbol["confidence"] = .95
    output["symbols"] = [symbol]
    output["links"] = [{"from_id": "mark_1", "to_id": "symbol_1",
                        "kind": "annotates", "confidence": .95}]
    raw = json.dumps(output).encode()
    vocabulary = {"enabled": True, "version": "personal-v1",
                  "mappings": {"!!": "promote_candidate", "R": "reread_target"}}
    with Library(tmp_path) as lib:
        def capture(source: str) -> str:
            return lib.ingest("owner_a", transport="gateway", account_id="a",
                              conversation_id="c", source_event_id=source,
                              attachments=[{"source_item_id": "i", "mime_type": "image/png",
                                            "data": _photo()}], idempotency_key=source)["capture_ids"][0]
        disabled = process_capture(lib, "owner_a", capture("disabled"), lambda _: raw)
        assert all(not trace["intent_signals"] for trace in disabled)
        enabled = process_capture(lib, "owner_a", capture("enabled"), lambda _: raw,
                                  vocabulary=vocabulary)
        important = next(trace for trace in enabled if "symbol" in trace["trace_types"])
        assert important["intent_signals"] == ["promote_candidate"]
        assert important["vocabulary_version"] == "personal-v1"
        assert important["review"]["required"] is True
        assert important["review"]["state"] == "pending"
        assert important["attribution"]["mark_author"] == "unknown"
        assert all("reread_target" not in trace["intent_signals"] for trace in enabled)


def test_user_resolution_before_extraction_survives_processing(tmp_path: Path):
    with Library(tmp_path) as lib:
        session = lib.start_session("owner_a")
        receipt = lib.ingest("owner_a", transport="gateway", account_id="a",
                             conversation_id="c", source_event_id="m",
                             attachments=[{"source_item_id": "i", "mime_type": "image/png",
                                           "data": _photo()}], idempotency_key="k")
        capture_id = receipt["capture_ids"][0]
        first = resolve_capture(lib, "owner_a", capture_id, None,
                                session_id=session["id"])
        assert first["revision"] == 1
        traces = process_capture(lib, "owner_a", capture_id, lambda _: _output())
        resolution = lib.get("owner_a", "CaptureResolution", first["id"])
        assert resolution["revision"] == 2
        assert resolution["session"]["value"] == session["id"]
        assert resolution["session"]["basis"] == "user_confirmation"
        assert all(trace["source"]["resolution_id"] == first["id"] and
                   trace["source"]["resolution_revision"] == 2 for trace in traces)
        assert lib.get("owner_a", "PageCapture", capture_id)["submitted_context"]["session_id"] is None
