"""Catalog binding must never confuse a physical copy or conversation."""
from pathlib import Path
from zipfile import ZipFile

import pytest

from agents.librarian.runtime.store import Library, LibrarianError, _now, _unknown_time
from agents.librarian.runtime.worker import (_catalog, _current, _hide_vault_markers,
                                             _remove_vault_images)


def _epub(path: Path) -> None:
    with ZipFile(path, "w") as archive:
        archive.writestr("content.opf", """<package xmlns:dc="http://purl.org/dc/elements/1.1/">
          <metadata><dc:title>测试图书</dc:title><dc:creator>作者</dc:creator>
          <dc:publisher>出版社</dc:publisher><dc:date>2021</dc:date></metadata></package>""")


def _batch(chat: str, capture: str) -> dict:
    return {"origin": {"transport": "feishu", "account_id": "librarian",
                       "conversation_id": chat}, "capture_ids": [capture]}


def test_catalog_uses_conversation_session_and_rejects_ambiguous_copies(tmp_path: Path) -> None:
    epub = tmp_path / "9787208171411.epub"
    _epub(epub)
    with Library(tmp_path / "state") as lib:
        assert _catalog(lib, "owner", epub.stem, epub, _batch("chat-a", "capture-a")) == "测试图书"
        first = _current(lib, "owner", "ReadingSession")[0]
        assert first["book_instance_id"] == "copy_9787208171411"

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

        # The previously selected session still disambiguates its own chat.
        _catalog(lib, "owner", epub.stem, epub, _batch("chat-a", "capture-d"))
        assert len(_current(lib, "owner", "ReadingSession")) == 2


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
