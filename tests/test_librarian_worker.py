"""Catalog binding must never confuse a physical copy or conversation."""
from pathlib import Path
from zipfile import ZipFile
from io import BytesIO
import json
from multiprocessing import get_all_start_methods, get_context

import pytest
from PIL import Image

from agents.librarian.runtime.store import Library, LibrarianError, _now, _unknown_time
from agents.librarian.runtime.worker import (_catalog, _current, _hide_vault_markers,
                                             _isbn_metadata,
                                             _latest_pending_review_ids,
                                             _notified_batch_is_current,
                                             _remove_vault_images, _sync_digital,
                                             _render_batch_note, _render_batch_note_legacy,
                                             _refresh_generated_note, _review_digest,
                                             _notify_correction,
                                             _repair_legacy_auto_affinity)


def test_only_latest_pending_run_reopens_a_capture() -> None:
    runs = [
        {"capture_id": "resolved", "outcome": "pending",
         "issues": ["RECONCILIATION_REQUIRED"]},
        {"capture_id": "still_pending", "outcome": "pending",
         "issues": ["RECONCILIATION_REQUIRED"]},
        {"capture_id": "resolved", "outcome": "success", "issues": []},
    ]
    assert _latest_pending_review_ids(runs) == {"still_pending"}


def test_notified_batch_does_not_hide_a_newer_pending_or_failed_run() -> None:
    batch = {"capture_ids": ["capture_one"]}
    matching = [{"capture_id": "capture_one", "outcome": "success"}]
    args = {"notified": True, "revised_notice": True, "unbound": False,
            "matching_runs": matching, "latest_runs": {"capture_one": matching[0]},
            "pending_review_ids": set()}
    assert _notified_batch_is_current(batch, **args)
    assert not _notified_batch_is_current(batch, **{**args,
        "latest_runs": {"capture_one": {"outcome": "pending"}},
        "pending_review_ids": {"capture_one"}})
    assert not _notified_batch_is_current(batch, **{**args,
        "latest_runs": {"capture_one": {"outcome": "failed"}}})


def test_worker_refreshes_stale_partial_status_after_unchanged_batch(tmp_path: Path,
                                                                       monkeypatch) -> None:
    from agents.librarian.runtime import worker
    from datetime import datetime, timedelta, timezone

    state = tmp_path / "state"
    stream = BytesIO()
    Image.new("RGB", (10, 10), "white").save(stream, "PNG")
    with Library(state) as lib:
        receipt = lib.ingest("owner", transport="feishu", account_id="librarian",
                             conversation_id="chat", source_event_id="status-fixture",
                             attachments=[{"source_item_id": "image", "mime_type": "image/png",
                                           "data": stream.getvalue()}],
                             idempotency_key="status-command")
    future = (datetime.now(timezone.utc) + timedelta(minutes=2)).isoformat()
    monkeypatch.setattr(worker, "_now", lambda: future)
    monkeypatch.setattr(worker, "_process_batch", lambda *_args: {
        "batch_id": receipt["batch_id"], "status": "unchanged"})
    status = state / "batch-status" / f"{receipt['batch_id']}.json"
    status.parent.mkdir()
    status.write_text(json.dumps({"batch_id": receipt["batch_id"], "status": "partial",
                                  "unresolved_pages": 3, "traces": 0}))
    assert worker.run(state, None, "owner", physical_only=True) == []
    updated = json.loads(status.read_text())
    assert updated["status"] == "processed" and updated["unresolved_pages"] == 0
    assert updated["traces"] == 0 and updated["retry_attempts"] == 0


def _epub(path: Path) -> None:
    with ZipFile(path, "w") as archive:
        archive.writestr("content.opf", """<package xmlns:dc="http://purl.org/dc/elements/1.1/">
          <metadata><dc:title>测试图书</dc:title><dc:creator>作者</dc:creator>
          <dc:publisher>出版社</dc:publisher><dc:date>2021</dc:date></metadata></package>""")


def _batch(chat: str, capture: str) -> dict:
    return {"origin": {"transport": "feishu", "account_id": "librarian",
                       "conversation_id": chat}, "capture_ids": [capture],
            "received_at": _now()}


def test_catalog_uses_conversation_session_and_rejects_ambiguous_copies(tmp_path: Path) -> None:
    epub = tmp_path / "9787208171411.epub"
    _epub(epub)
    with Library(tmp_path / "state") as lib:
        assert _catalog(lib, "owner", epub.stem, epub, _batch("chat-a", "capture-a")) == "测试图书"
        first = _current(lib, "owner", "ReadingSession")[0]
        edition = _current(lib, "owner", "Edition")[0]
        assert edition["isbn"]["isbn13"] == epub.stem
        assert edition["id"].startswith("edition_") and epub.stem not in edition["id"]
        assert edition["work_id"].startswith("work_") and epub.stem not in edition["work_id"]
        assert first["book_instance_id"].startswith("copy_") and epub.stem not in first["book_instance_id"]
        scope = lib.db.execute("SELECT selected,last_assigned_at FROM session_scope "
                               "WHERE owner_id='owner' AND conversation_id='chat-a'").fetchone()
        assert scope["selected"] == 0 and scope["last_assigned_at"] is not None

        # OCR-derived affinity expires; it is not a user-selected session.
        lib.db.execute("UPDATE session_scope SET last_assigned_at='2000-01-01T00:00:00+00:00' "
                       "WHERE owner_id='owner' AND conversation_id='chat-a'")
        assert lib._choose_session(("owner", "feishu", "librarian", "chat-a"), None) == (None, "unknown")

        # A different conversation must not silently inherit the first session.
        _catalog(lib, "owner", epub.stem, epub, _batch("chat-b", "capture-b"))
        sessions = _current(lib, "owner", "ReadingSession")
        assert len(sessions) == 2
        assert len({session["id"] for session in sessions}) == 2
        assert len(_current(lib, "owner", "Work")) == 1
        assert len(_current(lib, "owner", "Edition")) == 1

        lib.register("owner", {"object_type": "BookInstance", "schema_version": "0.1.0",
                               "id": "copy_second", "owner_id": "owner", "created_at": _now(),
                               "edition_id": edition["id"], "medium": "physical",
                               "acquired_at": _unknown_time(), "ownership_status": "unknown",
                               "physical": {"qr_id": None, "shelf": None},
                               "reading_status": {"state": "unknown", "current_page": None,
                                                  "progress_evidence_ref": None},
                               "revision": 1, "supersedes_revision": None})
        with pytest.raises(LibrarianError, match="multiple physical copies") as error:
            _catalog(lib, "owner", epub.stem, epub, _batch("chat-c", "capture-c"))
        assert error.value.code == "CONTEXT_CONFLICT"
        assert len(_current(lib, "owner", "ReadingSession")) == 2

        # An expired automatic session cannot disambiguate two copies.
        with pytest.raises(LibrarianError, match="multiple physical copies"):
            _catalog(lib, "owner", epub.stem, epub, _batch("chat-a", "capture-d"))


def test_catalog_reuses_existing_legacy_isbn_edition(tmp_path: Path) -> None:
    epub = tmp_path / "9787208171411.epub"
    _epub(epub)
    with Library(tmp_path / "state") as lib:
        common = {"schema_version": "0.1.0", "owner_id": "owner",
                  "created_at": _now(), "revision": 1, "supersedes_revision": None}
        lib.register("owner", {**common, "object_type": "Work", "id": "work_9787208171411",
                               "title": "测试图书", "original_title": None, "authors": [],
                               "identifiers": []})
        lib.register("owner", {**common, "object_type": "Edition", "id": "edition_9787208171411",
                               "work_id": "work_9787208171411", "edition_label": None,
                               "publisher": None, "publication_year": None,
                               "isbn": {"isbn13": epub.stem, "isbn10": None},
                               "language": None, "page_count": None, "volume_label": None})
        lib.register("owner", {**common, "object_type": "BookInstance", "id": "copy_9787208171411",
                               "edition_id": "edition_9787208171411", "medium": "physical",
                               "acquired_at": _unknown_time(), "ownership_status": "unknown",
                               "physical": {"qr_id": None, "shelf": None},
                               "reading_status": {"state": "unknown", "current_page": None,
                                                  "progress_evidence_ref": None}})
        assert _catalog(lib, "owner", epub.stem, epub, _batch("chat", "capture")) == "测试图书"
        assert len(_current(lib, "owner", "Work")) == 1
        assert len(_current(lib, "owner", "Edition")) == 1
        assert _current(lib, "owner", "ReadingSession")[0]["book_instance_id"] == "copy_9787208171411"


def test_old_vault_page_images_are_removed_without_rewriting_review_text(tmp_path: Path) -> None:
    folder = tmp_path / "2Area" / "40 学习与阅读" / "阅读笔记"
    attachment = folder / "Attachments" / "Librarian" / "batch_abc" / "capture_xyz.jpg"
    attachment.parent.mkdir(parents=True)
    attachment.write_bytes(b"old derived image")
    note = folder / "一本书.md"
    note.write_text("我的批注\n![[Attachments/Librarian/batch_abc/capture_xyz.jpg]]\n"
                    "<!-- librarian-batch: batch_abc -->\n", encoding="utf-8")
    assert _remove_vault_images(tmp_path, {"id": "batch_abc"})
    assert "我的批注" in note.read_text(encoding="utf-8")
    assert "原图证据：`capture_xyz`" in note.read_text(encoding="utf-8")
    assert not attachment.exists()
    assert not _remove_vault_images(tmp_path, {"id": "batch_abc"})


def test_correction_notice_dedupes_each_distinct_trace_state(tmp_path: Path,
                                                              monkeypatch) -> None:
    from agents.librarian.runtime import worker

    sent = []
    def send(command, **_kwargs):
        sent.append(command)
        return type("Result", (), {"returncode": 0})()
    monkeypatch.setattr(worker.subprocess, "run", send)
    batch = {"id": "batch_one", "origin": {"conversation_id": "owner-chat"}}
    note = tmp_path / "book.md"
    trace = {"id": "rt_one", "revision": 1,
             "location": {"page": {"number": 23, "label": "23"}},
             "content": {"printed_text": {"text": "first"},
                         "annotation": {"text": None}}}
    first_key = _review_digest([trace])
    _notify_correction(tmp_path, batch, note, 1, revision_key=first_key)
    _notify_correction(tmp_path, batch, note, 1, revision_key=first_key)
    changed = {**trace, "revision": 2,
               "location": {"page": {"number": 24, "label": "24"}}}
    _notify_correction(tmp_path, batch, note, 1, revision_key=_review_digest([changed]))
    assert len(sent) == 2


def test_vault_trace_metadata_is_hidden_without_changing_review_text(tmp_path: Path) -> None:
    folder = tmp_path / "2Area" / "40 学习与阅读" / "阅读笔记"
    folder.mkdir(parents=True)
    note = folder / "一本书.md"
    note.write_text("我的批注\n<!-- librarian-trace: rt_abc revision: 2 -->\n"
                    "<!-- librarian-batch: batch_abc -->\n", encoding="utf-8")
    assert _hide_vault_markers(tmp_path, {"id": "batch_abc"})
    content = note.read_text(encoding="utf-8")
    assert "我的批注" in content
    assert '<span hidden data-librarian-trace="rt_abc" data-revision="2"></span>' in content
    assert '<span hidden data-librarian-batch="batch_abc"></span>' in content
    assert not _hide_vault_markers(tmp_path, {"id": "batch_abc"})


def test_failed_digital_source_does_not_stop_other_sources(tmp_path: Path, monkeypatch) -> None:
    from agents.librarian.runtime import worker

    def unavailable(*_args):
        raise LibrarianError("UPSTREAM_UNAVAILABLE", "private source unavailable")

    monkeypatch.setattr(worker, "sync_koodo_sqlite", unavailable)
    monkeypatch.setattr(worker, "fetch_weread_book",
                        lambda _key, book_id: ({"bookId": book_id}, []))
    monkeypatch.setattr(worker, "sync_weread_book",
                        lambda *_args: {"created": 0, "unchanged": 0})
    config = tmp_path / "plugin-data.json"
    config.write_text('{"wereadApiKey":"private"}', encoding="utf-8")
    with Library(tmp_path / "state") as lib:
        result = _sync_digital(lib, tmp_path / "state", "owner",
                               koodo=("koodo", tmp_path / "books.db", tmp_path / "notes.db"),
                               weread=("weread", config, ["book-1"]))
    assert [(item["source"], item["status"]) for item in result] == [
        ("koodo", "error"), ("weread", "success")]
    assert result[0]["code"] == "UPSTREAM_UNAVAILABLE"
    assert "private" not in (tmp_path / "state" / "digital-sync-status.json").read_text()


def test_bad_batch_does_not_starve_later_batch(tmp_path: Path, monkeypatch) -> None:
    from agents.librarian.runtime import worker

    stream = BytesIO()
    Image.new("RGB", (10, 10), "white").save(stream, "PNG")
    with Library(tmp_path / "state") as lib:
        ids = []
        for index in (1, 2):
            receipt = lib.ingest("owner", transport="feishu", account_id="librarian",
                                 conversation_id=f"chat-{index}", source_event_id=f"message-{index}",
                                 attachments=[{"source_item_id": f"image-{index}",
                                               "mime_type": "image/png", "data": stream.getvalue()}],
                                 idempotency_key=f"command-{index}")
            ids.append(receipt["batch_id"])

    seen = []
    def process(_lib, _root, _vault, _owner, batch, _model):
        seen.append(batch["id"])
        if batch["id"] == ids[0]:
            raise LibrarianError("CONTEXT_CONFLICT", "first batch failed")
        return {"batch_id": batch["id"], "status": "processed", "traces": 1}

    monkeypatch.setattr(worker, "_process_batch", process)
    monkeypatch.setattr(worker, "_now", lambda: "2099-01-01T00:00:00+00:00")
    result = worker.run(tmp_path / "state", tmp_path / "vault", "owner")
    assert seen == ids
    assert [(item["batch_id"], item["status"]) for item in result] == [
        (ids[0], "error"), (ids[1], "processed")]
    assert (tmp_path / "state" / "batch-status" / f"{ids[0]}.json").exists()


def test_failed_batch_retries_with_backoff_then_stops(tmp_path: Path, monkeypatch) -> None:
    from agents.librarian.runtime import worker

    stream = BytesIO()
    Image.new("RGB", (10, 10), "white").save(stream, "PNG")
    state = tmp_path / "state"
    with Library(state) as lib:
        receipt = lib.ingest("owner", transport="feishu", account_id="librarian",
                             conversation_id="chat", source_event_id="message",
                             attachments=[{"source_item_id": "image", "mime_type": "image/png",
                                           "data": stream.getvalue()}],
                             idempotency_key="command")
    clock = ["2099-01-01T00:00:00+00:00"]
    monkeypatch.setattr(worker, "_now", lambda: clock[0])
    calls = []
    def fail(*_args):
        calls.append(clock[0])
        raise LibrarianError("EXTRACTOR_UNAVAILABLE", "model unavailable")
    monkeypatch.setattr(worker, "_process_batch", fail)
    status_file = state / "batch-status" / f"{receipt['batch_id']}.json"

    assert worker.run(state, None, "owner")[0]["code"] == "EXTRACTOR_UNAVAILABLE"
    assert json.loads(status_file.read_text())["next_retry_at"] == "2099-01-01T00:05:00+00:00"
    clock[0] = "2099-01-01T00:04:59+00:00"
    assert worker.run(state, None, "owner") == []
    clock[0] = "2099-01-01T00:05:00+00:00"
    assert len(worker.run(state, None, "owner")) == 1
    clock[0] = "2099-01-01T00:35:00+00:00"
    assert len(worker.run(state, None, "owner")) == 1
    assert json.loads(status_file.read_text())["retry_exhausted"] is True
    clock[0] = "2099-01-02T00:00:00+00:00"
    assert worker.run(state, None, "owner") == []
    assert len(calls) == 3
    assert len(worker.run(state, None, "owner", vision_model="fixture/new-model")) == 1
    assert json.loads(status_file.read_text())["retry_attempts"] == 1
    source_books = state / "source-books"
    source_books.mkdir()
    (source_books / "9787208171411.epub").write_bytes(b"new ground truth")
    assert len(worker.run(state, None, "owner", vision_model="fixture/new-model")) == 1
    assert json.loads(status_file.read_text())["retry_attempts"] == 1
    assert len(calls) == 5


def test_partial_extractor_failure_is_throttled_and_success_resets_retry(tmp_path: Path,
                                                                          monkeypatch) -> None:
    from agents.librarian.runtime import worker

    stream = BytesIO()
    Image.new("RGB", (10, 10), "white").save(stream, "PNG")
    state = tmp_path / "state"
    with Library(state) as lib:
        receipt = lib.ingest("owner", transport="feishu", account_id="librarian",
                             conversation_id="chat", source_event_id="message",
                             attachments=[{"source_item_id": "image", "mime_type": "image/png",
                                           "data": stream.getvalue()}],
                             idempotency_key="command")
    clock = ["2099-01-01T00:00:00+00:00"]
    monkeypatch.setattr(worker, "_now", lambda: clock[0])
    calls = []
    def process(*_args):
        calls.append(clock[0])
        if len(calls) == 1:
            return {"status": "partial", "issues": [{"code": "EXTRACTOR_UNAVAILABLE"}]}
        return {"status": "processed", "traces": 1}
    monkeypatch.setattr(worker, "_process_batch", process)
    status_file = state / "batch-status" / f"{receipt['batch_id']}.json"
    worker.run(state, None, "owner")
    clock[0] = "2099-01-01T00:01:00+00:00"
    assert worker.run(state, None, "owner") == []
    clock[0] = "2099-01-01T00:05:00+00:00"
    assert worker.run(state, None, "owner")[0]["status"] == "processed"
    assert json.loads(status_file.read_text())["retry_attempts"] == 0
    assert len(calls) == 2


def test_interior_photo_without_epub_or_vault_persists_partial_trace(tmp_path: Path,
                                                                       monkeypatch) -> None:
    from agents.librarian.runtime import worker

    stream = BytesIO()
    Image.new("RGB", (100, 100), "white").save(stream, "PNG")
    state = tmp_path / "state"
    with Library(state) as lib:
        receipt = lib.ingest("owner", transport="feishu", account_id="librarian",
                             conversation_id="chat", source_event_id="interior-1",
                             attachments=[{"source_item_id": "image-1", "mime_type": "image/png",
                                           "data": stream.getvalue()}],
                             idempotency_key="interior-command")
    calls = []
    def extractor(epub, **_kwargs):
        assert epub is None
        def infer(_):
            calls.append("bookscan")
            return json.dumps({
            "image_space": {"width": 100, "height": 100,
                            "basis": "exif_oriented_original"},
            "pages": [{"id": "page_1", "bbox": [0, 0, 1, 1], "side": "unknown",
                       "page": {"value": None, "confidence": None,
                                "basis": "unknown", "status": "unresolved"}}],
            "printed_regions": [{"id": "text_1", "page_region_id": "page_1",
                                 "bbox": [.1, .1, .8, .2], "kind": "printed",
                                 "text": {"text": "照片上可见的一整句。", "confidence": .8,
                                          "basis": "vision"}, "confidence": .8,
                                 "linked_text_region_ids": [], "link_confidence": None}],
            "marks": [{"id": "mark_1", "page_region_id": "page_1",
                       "bbox": [.1, .18, .8, .21], "kind": "underline", "text": None,
                       "confidence": .8, "linked_text_region_ids": ["text_1"],
                       "link_confidence": .9}],
            "annotations": [], "symbols": [], "links": [], "warnings": []
            }).encode()
        return infer
    monkeypatch.setattr(worker, "bookscan_extractor", extractor)
    monkeypatch.setattr(worker, "_now", lambda: "2099-01-01T00:00:00+00:00")

    result = worker.run(state, None, "owner", vision_model="fixture/vision")
    assert result[0]["status"] == "partial"
    assert result[0]["unresolved_pages"] == 1
    assert result[0]["vault_status"] == "unconfigured"
    with Library(state) as lib:
        assert len(_current(lib, "owner", "PageObservation")) == 1
        traces = _current(lib, "owner", "ReadingTrace")
        assert len(traces) == 1 and traces[0]["location"]["page"] is None
        assert traces[0]["work_id"] is None
    worker.run(state, None, "owner", vision_model="fixture/vision")
    assert calls == ["bookscan"]


def test_generic_photo_uses_bookscan_without_full_page_model(tmp_path: Path, monkeypatch) -> None:
    from agents.librarian.runtime import worker
    from agents.librarian.runtime.pipeline import ExtractionOutput

    image = BytesIO()
    Image.new("RGB", (100, 100), "white").save(image, "PNG")
    original = image.getvalue()
    state = tmp_path / "state"
    with Library(state) as lib:
        receipt = lib.ingest("owner", transport="feishu", account_id="librarian",
                             conversation_id="chat", source_event_id="interior-ocr",
                             attachments=[{"source_item_id": "image", "mime_type": "image/png",
                                           "data": original}], idempotency_key="interior-ocr")
    observation = {"image_space": {"width": 100, "height": 100,
                                    "basis": "exif_oriented_original"},
                   "pages": [{"id": "page_0", "bbox": [0, 0, 1, 1], "side": "unknown",
                              "page": {"value": None, "confidence": None,
                                       "basis": "unknown", "status": "unresolved"}}],
                   "printed_regions": [{"id": "print_0", "page_region_id": "page_0",
                                        "bbox": [.1, .2, .8, .3], "kind": "printed",
                                        "text": {"text": "照片上可见的完整句子。", "confidence": .9,
                                                 "basis": "vision"},
                                        "confidence": .9, "linked_text_region_ids": [],
                                        "link_confidence": None}],
                   "marks": [{"id": "mark_0", "page_region_id": "page_0",
                              "bbox": [.1, .29, .8, .31], "kind": "underline", "text": None,
                              "confidence": .8, "linked_text_region_ids": ["print_0"],
                              "link_confidence": .9}],
                   "annotations": [], "symbols": [], "links": [], "warnings": []}
    monkeypatch.setattr(worker, "bookscan_extractor", lambda _epub, **_kwargs: lambda _raw: ExtractionOutput(
        raw=b'{}', observation=json.dumps(observation).encode(), derivative=original,
        derivative_width=100, derivative_height=100, operations=("exif_transpose",)))
    monkeypatch.setattr(worker, "_now", lambda: "2099-01-01T00:00:00+00:00")
    result = worker.run(state, None, "owner")
    assert result[0]["status"] == "partial"
    assert result[0]["traces"] == 1
    with Library(state) as lib:
        traces = _current(lib, "owner", "ReadingTrace")
        assert traces[0]["source"]["capture_id"] == receipt["capture_ids"][0]


def test_physical_processing_is_independent_of_slow_digital_sync(tmp_path: Path,
                                                                  monkeypatch) -> None:
    from agents.librarian.runtime import worker

    state = tmp_path / "state"
    seen = []
    monkeypatch.setattr(worker, "_sync_digital", lambda *_args, **_kwargs:
                        seen.append("digital") or [])
    worker.run(state, None, "owner", koodo=("source", tmp_path, tmp_path),
               physical_only=True)
    assert seen == []
    worker.run(state, None, "owner", koodo=("source", tmp_path, tmp_path),
               digital_only=True)
    assert seen == ["digital"]


@pytest.mark.skipif("fork" not in get_all_start_methods(), reason="requires forked workers")
def test_physical_batch_finishes_while_digital_source_is_blocked(tmp_path: Path,
                                                                 monkeypatch) -> None:
    from agents.librarian.runtime import worker

    state = tmp_path / "state"
    stream = BytesIO()
    Image.new("RGB", (10, 10), "white").save(stream, "PNG")
    with Library(state) as lib:
        batch_id = lib.ingest(
            "owner", transport="feishu", account_id="librarian",
            conversation_id="chat", source_event_id="message",
            attachments=[{"source_item_id": "image", "mime_type": "image/png",
                          "data": stream.getvalue()}],
            idempotency_key="command")["batch_id"]
    context = get_context("fork")
    digital_started = context.Event()
    release_digital = context.Event()
    physical_result = context.Queue()
    digital_result = context.Queue()

    def slow_digital(*_args, **_kwargs):
        digital_started.set()
        assert release_digital.wait(10)
        return []

    monkeypatch.setattr(worker, "_sync_digital", slow_digital)
    monkeypatch.setattr(worker, "_process_batch", lambda _lib, _root, _vault,
                        _owner, batch, _model:
                        {"batch_id": batch["id"], "status": "processed", "traces": 1})
    monkeypatch.setattr(worker, "_now", lambda: "2099-01-01T00:00:00+00:00")

    def run_digital():
        digital_result.put(worker.run(state, None, "owner",
                                      koodo=("source", tmp_path, tmp_path),
                                      digital_only=True))

    def run_physical():
        physical_result.put(worker.run(state, None, "owner", physical_only=True))

    digital = context.Process(target=run_digital)
    physical = context.Process(target=run_physical)
    digital.start()
    try:
        assert digital_started.wait(3)
        physical.start()
        result = physical_result.get(timeout=3)
        assert any(item.get("batch_id") == batch_id and item["status"] == "processed"
                   for item in result)
        assert digital.is_alive()
    finally:
        release_digital.set()
        if physical.pid is not None:
            physical.join(timeout=5)
        digital.join(timeout=5)
        if physical.is_alive():
            physical.terminate()
            physical.join()
        if digital.is_alive():
            digital.terminate()
            digital.join()
    assert physical.exitcode == 0
    assert digital.exitcode == 0
    assert digital_result.get(timeout=1) == []


def test_worker_recovers_lagging_index_without_a_new_photo(tmp_path: Path) -> None:
    from agents.librarian.runtime import worker
    from agents.librarian.runtime.digital import ingest_export

    state = tmp_path / "state"
    export = '''---
bookId: "book-1"
---
> [!abstract] Test book
# 高亮划线
## One
> 📌 Weber and Parsons
> ⏱ 2024-01-01 12:00:00 ^book-1-mark-1
'''.encode()
    with Library(state) as lib:
        trace = ingest_export(lib, "owner", "weread", "export.md", export)[0]
        lib.db.execute("DELETE FROM trace_index WHERE owner_id='owner'")
        lib.db.commit()
    assert worker.run(state, None, "owner", physical_only=True) == []
    with Library(state) as lib:
        row = lib.db.execute("SELECT revision FROM trace_index WHERE owner_id='owner' AND trace_id=?",
                             (trace["id"],)).fetchone()
        assert row["revision"] == trace["revision"]


def test_physical_note_uses_weread_layout_and_upgrades_unchanged_legacy(tmp_path: Path) -> None:
    batch = {"id": "batch_fixture", "isbn": "9787208171411"}
    trace = {"id": "rt_fixture", "revision": 1,
             "created_at": "2026-09-28T12:00:00+00:00", "trace_types": ["underline"],
             "location": {"page": {"label": "39", "number": 39},
                          "bbox": [.1, .2, .8, .3]},
             "content": {"printed_text": {"text": "正是帕森斯，\n完成整合。"},
                         "annotation": {"text": None}},
             "source": {"capture_id": "capture_fixture"}}
    received = {"capture_fixture": "2026-09-27T12:00:00+00:00"}
    new = _render_batch_note(batch, "社会理论二十讲", [trace], created="2026-09-28",
                             received_at_by_capture=received)
    assert "# 元数据" in new and "# 高亮划线" in new
    assert "## 第 39 页" in new
    assert "> 📌 正是帕森斯，完成整合。" in new
    assert "^rt_fixture" not in new
    assert "原图" not in new
    assert "capture_fixture" not in new
    assert "> ⏱ 收图：2026-09-27 20:00:00" in new
    assert "2026-09-28 20:00:00" not in new
    assert "<span hidden data-librarian-trace=" in new
    assert "![[" not in new

    note_v6 = _render_batch_note(batch, "社会理论二十讲", [trace], created="2026-09-28",
                                 presentation_version=6,
                                 received_at_by_capture=received)
    assert "> 📌 正是帕森斯，完成整合。 ^rt_fixture" in note_v6
    note_v7 = _render_batch_note(batch, "社会理论二十讲", [trace], created="2026-09-28",
                                 presentation_version=7,
                                 received_at_by_capture=received)
    assert "^rt_fixture" not in note_v7
    assert "> 原图证据：`capture_fixture`" in note_v7
    note_v8 = _render_batch_note(batch, "社会理论二十讲", [trace], created="2026-09-28",
                                 presentation_version=8,
                                 received_at_by_capture=received)
    assert "> 📷 原图：可向图书专员索取" in note_v8

    folder = tmp_path / "2Area" / "40 学习与阅读" / "阅读笔记"
    folder.mkdir(parents=True)
    note = folder / "社会理论二十讲.md"
    note.write_text(_render_batch_note_legacy(batch, "社会理论二十讲", [trace],
                                               created="2026-09-28"), encoding="utf-8")
    _refresh_generated_note(tmp_path, batch, "社会理论二十讲", [trace], [trace], received)
    assert note.read_text(encoding="utf-8") == new
    note.write_text(note_v8, encoding="utf-8")
    _refresh_generated_note(tmp_path, batch, "社会理论二十讲", [trace], [trace], received)
    assert note.read_text(encoding="utf-8") == new
    note.write_text(note_v7, encoding="utf-8")
    _refresh_generated_note(tmp_path, batch, "社会理论二十讲", [trace], [trace], received)
    assert note.read_text(encoding="utf-8") == new
    note.write_text(note_v6, encoding="utf-8")
    _refresh_generated_note(tmp_path, batch, "社会理论二十讲", [trace], [trace], received)
    assert note.read_text(encoding="utf-8") == new
    trace["revision"] = 2
    trace["created_at"] = "2026-09-29T12:00:00+00:00"
    revised = _render_batch_note(batch, "社会理论二十讲", [trace], created="2026-09-28",
                                  received_at_by_capture=received)
    assert "> ⏱ 收图：2026-09-27 20:00:00" in revised
    assert "2026-09-29 20:00:00" not in revised
    trace["revision"] = 1
    trace["created_at"] = "2026-09-28T12:00:00+00:00"
    note.write_text(_render_batch_note(batch, "社会理论二十讲", [trace],
                                       created="2026-09-28", presentation_version=5),
                    encoding="utf-8")
    _refresh_generated_note(tmp_path, batch, "社会理论二十讲", [trace], [trace], received)
    assert note.read_text(encoding="utf-8") == new
    note.write_text(new + "我的审阅\n", encoding="utf-8")
    with pytest.raises(LibrarianError) as error:
        _refresh_generated_note(tmp_path, batch, "社会理论二十讲", [trace], [trace], received)
    assert error.value.code == "REVIEW_EDIT_CONFLICT"


def test_isbn_metadata_fills_note_and_upgrades_unchanged_v9(tmp_path: Path) -> None:
    isbn = "9787208171411"
    source = tmp_path / "source-books"
    source.mkdir()
    (source / f"{isbn}.metadata.json").write_text(json.dumps({
        "isbn13": isbn, "authors": ["汉斯·约阿斯", "沃尔夫冈·克诺伯"],
        "translator": "郑作彧", "publisher": "上海人民出版社",
        "publication_date": "2021-09-01",
        "original_title": "Sozialtheorie. Zwanzig einführende Vorlesungen",
        "source_url": "https://book.douban.com/subject/35596074/",
    }, ensure_ascii=False), encoding="utf-8")
    batch = {"id": "batch_fixture", "isbn": isbn,
             "bibliography": _isbn_metadata(tmp_path, isbn)}
    trace = {"id": "rt_fixture", "revision": 1,
             "created_at": "2026-09-28T12:00:00+00:00", "trace_types": ["underline"],
             "location": {"page": {"label": "39", "number": 39},
                          "bbox": [.1, .2, .8, .3]},
             "content": {"printed_text": {"text": "正是帕森斯，完成整合。"},
                         "annotation": {"text": None}},
             "source": {"capture_id": "capture_fixture"}}
    folder = tmp_path / "2Area" / "40 学习与阅读" / "阅读笔记"
    folder.mkdir(parents=True)
    note = folder / "社会理论二十讲.md"
    note.write_text(_render_batch_note(batch, "社会理论二十讲", [trace],
                                       created="2026-09-28", presentation_version=9),
                    encoding="utf-8")
    _refresh_generated_note(tmp_path, batch, "社会理论二十讲", [trace], [trace])
    rendered = note.read_text(encoding="utf-8")
    assert 'authors: ["汉斯·约阿斯", "沃尔夫冈·克诺伯"]' in rendered
    assert "> - 译者： 郑作彧" in rendered
    assert "> - 出版日期： 2021-09-01" in rendered
    assert "> - 书目来源： [ISBN 书目](https://book.douban.com/subject/35596074/)" in rendered
    assert rendered.count('data-librarian-trace="rt_fixture"') == 1


def test_legacy_worker_selected_session_becomes_expiring_affinity(tmp_path: Path) -> None:
    epub = tmp_path / "9787208171411.epub"
    _epub(epub)
    state = tmp_path / "state"
    stream = BytesIO()
    Image.new("RGB", (100, 100), "white").save(stream, "PNG")
    with Library(state) as lib:
        receipt = lib.ingest("owner", transport="feishu", account_id="librarian",
                             conversation_id="chat", source_event_id="message",
                             attachments=[{"source_item_id": "image", "mime_type": "image/png",
                                           "data": stream.getvalue()}], idempotency_key="command")
        capture_id = receipt["capture_ids"][0]
        _catalog(lib, "owner", epub.stem, epub, _batch("chat", capture_id))
        lib.db.execute("UPDATE session_scope SET selected=1,last_assigned_at=NULL "
                       "WHERE owner_id='owner' AND conversation_id='chat'")
        assert _repair_legacy_auto_affinity(lib, "owner") == 1
        assert _repair_legacy_auto_affinity(lib, "owner") == 0
        scope = lib.db.execute("SELECT selected,last_assigned_at FROM session_scope "
                               "WHERE owner_id='owner' AND conversation_id='chat'").fetchone()
        assert scope["selected"] == 0 and scope["last_assigned_at"] is not None
        lib.db.execute("UPDATE session_scope SET last_assigned_at='2000-01-01T00:00:00+00:00'")
        assert lib._choose_session(("owner", "feishu", "librarian", "chat"), None) == (None, "unknown")


def test_chapter_note_layout_uses_epub_order_without_page_grouping() -> None:
    batch = {"id": "batch_fixture", "isbn": "9787208171411"}
    def trace(identifier, page, printed, annotation=None):
        return {"id": identifier, "revision": 1,
                "created_at": "2026-09-28T12:00:00+00:00",
                "location": {"page": {"label": str(page), "number": page},
                             "bbox": [0, 10, 100, 20]},
                "content": {"printed_text": {"text": printed},
                            "annotation": {"text": annotation}},
                "review": {"state": "none"},
                "source": {"capture_id": identifier}}
    later = trace("rt_later", 23, "下一章的句子。")
    second = trace("rt_second", 39, "第二段的句子。")
    first = trace("rt_first", 40, "第一段的句子。")
    note = trace("rt_note", 39, None, "手写内容")
    layout = ({8: "第一讲 什么是理论？", 9: "第二讲 帕森斯"},
              {"rt_later": (8, 10), "rt_first": (9, 20),
               "rt_note": (9, 20.5), "rt_second": (9, 30)})
    rendered = _render_batch_note(batch, "社会理论二十讲",
                                  [second, later, note, first], created="2026-09-28",
                                  presentation_version=11, chapter_layout=layout)
    assert rendered.index("## 第一讲") < rendered.index("## 第二讲")
    assert rendered.index("第一段的句子") < rendered.index("手写内容") < rendered.index("第二段的句子")
    assert "## 第 39 页" not in rendered
    assert "> 📖 第 39 页" in rendered
    assert rendered.count('data-librarian-trace=') == 4
