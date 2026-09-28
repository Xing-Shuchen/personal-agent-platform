"""Catalog binding must never confuse a physical copy or conversation."""
from pathlib import Path
from zipfile import ZipFile
from io import BytesIO
import json

import pytest
from PIL import Image

from agents.librarian.runtime.store import Library, LibrarianError, _now, _unknown_time
from agents.librarian.runtime.worker import (_catalog, _current, _hide_vault_markers,
                                             _remove_vault_images, _sync_digital,
                                             _render_batch_note, _render_batch_note_legacy,
                                             _refresh_generated_note,
                                             _repair_legacy_auto_affinity)


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
        assert first["book_instance_id"] == "copy_9787208171411"
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

        lib.register("owner", {"object_type": "BookInstance", "schema_version": "0.1.0",
                               "id": "copy_second", "owner_id": "owner", "created_at": _now(),
                               "edition_id": "edition_9787208171411", "medium": "physical",
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
    monkeypatch.setattr(worker, "_book_for_cover", lambda *_: None)
    calls = []
    def extractor(*, model):
        def infer(_):
            calls.append(model)
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
                       "link_confidence": .8}],
            "annotations": [], "symbols": [], "links": [], "warnings": []
            }).encode()
        return infer
    monkeypatch.setattr(worker, "openclaw_extractor", extractor)
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
    assert calls == ["fixture/vision"]


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


def test_physical_note_uses_weread_layout_and_upgrades_unchanged_legacy(tmp_path: Path) -> None:
    batch = {"id": "batch_fixture", "isbn": "9787208171411"}
    trace = {"id": "rt_fixture", "revision": 1,
             "created_at": "2026-09-28T12:00:00+00:00", "trace_types": ["underline"],
             "location": {"page": {"label": "39", "number": 39},
                          "bbox": [.1, .2, .8, .3]},
             "content": {"printed_text": {"text": "正是帕森斯，\n完成整合。"},
                         "annotation": {"text": None}},
             "source": {"capture_id": "capture_fixture"}}
    new = _render_batch_note(batch, "社会理论二十讲", [trace], created="2026-09-28")
    assert "# 元数据" in new and "# 高亮划线" in new
    assert "## 第 39 页" in new
    assert "> 📌 正是帕森斯，完成整合。 ^rt_fixture" in new
    assert "> ⏱ 2026-09-28 20:00:00" in new
    assert "<span hidden data-librarian-trace=" in new
    assert "![[" not in new

    folder = tmp_path / "2Area" / "40 学习与阅读" / "阅读笔记"
    folder.mkdir(parents=True)
    note = folder / "社会理论二十讲.md"
    note.write_text(_render_batch_note_legacy(batch, "社会理论二十讲", [trace],
                                               created="2026-09-28"), encoding="utf-8")
    _refresh_generated_note(tmp_path, batch, "社会理论二十讲", [trace], [trace])
    assert note.read_text(encoding="utf-8") == new
    note.write_text(new + "我的审阅\n", encoding="utf-8")
    with pytest.raises(LibrarianError) as error:
        _refresh_generated_note(tmp_path, batch, "社会理论二十讲", [trace], [trace])
    assert error.value.code == "REVIEW_EDIT_CONFLICT"


def test_second_photo_can_supply_epub_identity(tmp_path: Path, monkeypatch) -> None:
    from agents.librarian.runtime import worker

    state = tmp_path / "state"
    epub = state / "source-books" / "9787208171411.epub"
    epub.parent.mkdir(parents=True)
    _epub(epub)
    stream = BytesIO()
    Image.new("RGB", (100, 100), "white").save(stream, "PNG")
    with Library(state) as lib:
        receipt = lib.ingest("owner", transport="feishu", account_id="librarian",
                             conversation_id="chat", source_event_id="two-photos",
                             attachments=[{"source_item_id": str(index), "mime_type": "image/png",
                                           "data": stream.getvalue()} for index in (1, 2)],
                             idempotency_key="two-photos-command")
        batch = _current(lib, "owner", "CaptureBatch")[0]
        seen = []
        monkeypatch.setattr(worker, "_book_for_cover",
                            lambda *_: seen.append(1) or ((epub.stem, epub) if len(seen) == 2 else None))
        monkeypatch.setattr(worker, "ocr_extractor", lambda **_kwargs: lambda _raw: b"{}")
        monkeypatch.setattr(worker, "process_capture", lambda *_args, **_kwargs: [])
        result = worker._process_batch(lib, state, None, "owner", batch, "fixture/vision")
        assert len(seen) == 2
        assert result["status"] == "partial"
        assert len(_current(lib, "owner", "ReadingSession")) == 1


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
