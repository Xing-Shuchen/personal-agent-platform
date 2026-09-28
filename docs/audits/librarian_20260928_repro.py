"""Audit probes for d111ace; synthetic temporary data only, no external calls.

Run from repo root: .venv/bin/python docs/audits/librarian_20260928_repro.py
These assertions document defects at the audited commit, not desired behavior.
"""
import json
import runpy
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from agents.librarian.runtime import pipeline, worker
from agents.librarian.runtime.knowledge import create_candidate, decide_candidate, promote_candidate
from agents.librarian.runtime.ocr import EpubGroundTruth
from agents.librarian.runtime.store import Library, LibrarianError

fixtures = runpy.run_path(str(ROOT / "tests/test_librarian_pipeline.py"))
photo, output = fixtures["_photo"], fixtures["_output"]
results = {}


def ingest(lib, key="first"):
    return lib.ingest("audit_owner", transport="feishu", account_id="librarian",
                      conversation_id="audit_chat", source_event_id=key,
                      attachments=[{"source_item_id": key, "mime_type": "image/png",
                                    "data": photo()}], idempotency_key=key)


with tempfile.TemporaryDirectory(prefix="librarian-audit-") as temporary:
    root = Path(temporary)
    epub = root / "9787208171411.epub"
    with ZipFile(epub, "w") as archive:
        archive.writestr("content.opf", '<package xmlns:dc="http://purl.org/dc/elements/1.1/">'
                         '<metadata><dc:title>Audit fixture</dc:title></metadata></package>')
        archive.writestr("text.xhtml", "<p>照片之外的前半句，照片里面恰好拍到了中间这一部分文字，照片之外的后半句。</p>")
    expanded = EpubGroundTruth(epub).sentence("照片里面恰好拍到了中间这一部分文字")
    assert "照片之外" in expanded
    results["F03_epub_expansion"] = expanded

    state = root / "unmatched"
    with Library(state) as lib:
        receipt = ingest(lib)
    with patch.object(worker, "_book_for_cover", return_value=None), \
            patch.object(worker, "process_capture") as processing:
        worker.run(state, root / "vault", "audit_owner")
        assert processing.call_count == 0
    with Library(state) as lib:
        results["F01_unmatched_batch"] = {
            "status": lib.get("audit_owner", "CaptureBatch", receipt["batch_id"])["status"],
            "processing_runs": len(worker._current(lib, "audit_owner", "ProcessingRun"))}
        assert results["F01_unmatched_batch"] == {"status": "received", "processing_runs": 0}

    with Library(root / "affinity") as lib:
        receipt = ingest(lib)
        batch = lib.get("audit_owner", "CaptureBatch", receipt["batch_id"])
        worker._catalog(lib, "audit_owner", epub.stem, epub, batch)
        lib.db.execute("UPDATE session_scope SET last_assigned_at='2000-01-01T00:00:00+00:00'")
        lib.db.commit()
        selected, basis = lib._choose_session(("audit_owner", "feishu", "librarian", "audit_chat"), None)
        assert selected and basis == "active_session"
        results["F04_automatic_session_after_timeout"] = {"selected": bool(selected), "basis": basis}

    state = root / "batch-fault"
    with Library(state) as lib:
        ingest(lib, "bad-batch")
        ingest(lib, "good-batch")
    with patch.object(worker, "_book_for_cover", return_value=(epub.stem, epub)) as cover, \
            patch.object(worker, "_catalog", side_effect=LibrarianError("CONTEXT_CONFLICT", "synthetic conflict")):
        try:
            worker.run(state, root / "vault", "audit_owner")
        except LibrarianError as error:
            assert error.code == "CONTEXT_CONFLICT"
        else:
            raise AssertionError("batch conflict did not occur")
        assert cover.call_count == 1
        results["F06_batch_fault"] = {"accepted_batches": 2, "visited_batches": cover.call_count}

    with Library(root / "index-fault") as lib:
        receipt = ingest(lib)
        capture_id = receipt["capture_ids"][0]
        calls = []
        def extractor(_):
            calls.append(1)
            return output()
        with patch.object(pipeline, "_index_trace", side_effect=RuntimeError("synthetic index failure")):
            try:
                pipeline.process_capture(lib, "audit_owner", capture_id, extractor)
            except RuntimeError:
                pass
            else:
                raise AssertionError("injected fault did not occur")
        counts = {model: len(worker._current(lib, "audit_owner", model))
                  for model in ("ReadingTrace", "PageObservation", "ProcessingRun")}
        assert counts == {"ReadingTrace": 0, "PageObservation": 0, "ProcessingRun": 0}
        pipeline.process_capture(lib, "audit_owner", capture_id, extractor)
        assert len(calls) == 2
        results["F08_index_failure"] = {"persisted_after_failure": counts, "extractor_calls_after_retry": len(calls)}

    with Library(root / "knowledge") as lib:
        receipt = ingest(lib)
        capture_id = receipt["capture_ids"][0]
        traces = pipeline.process_capture(lib, "audit_owner", capture_id, lambda _: output(), extractor_version="v1")
        trace = traces[0]
        candidate = create_candidate(lib, "audit_owner", [{"trace_id": trace["id"], "revision": 1}],
                                     candidate_type="concept", correlation_id="audit",
                                     content={"text": None, "confidence": None, "basis": "unknown"})
        decide_candidate(lib, "audit_owner", candidate["id"], 1, approve=True)
        promote_candidate(lib, "audit_owner", candidate["id"], 2, lambda *_: "knowledge_audit")
        try:
            pipeline.process_capture(lib, "audit_owner", capture_id, lambda _: output(), extractor_version="v2")
        except LibrarianError as error:
            assert error.code == "RECONCILIATION_REQUIRED"
        pipeline.reconcile_extraction(lib, "audit_owner", capture_id, "v2")
        states = {"trace": lib.get("audit_owner", "ReadingTrace", trace["id"])["status"],
                  "candidate": lib.get("audit_owner", "KnowledgeCandidate", candidate["id"])["status"]}
        assert states == {"trace": "superseded", "candidate": "promoted"}
        results["F07_promoted_dependency_replaced"] = states

print(json.dumps(results, ensure_ascii=False, indent=2))
