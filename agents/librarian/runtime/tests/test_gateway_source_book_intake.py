"""Trusted EPUB attachment is bound to the selected physical session."""
from zipfile import ZipFile

import pytest

from agents.librarian.runtime.gateway_session import session_inbound
from agents.librarian.runtime.gateway_source_book_intake import store_inbound_epub
from agents.librarian.runtime.store import Library, LibrarianError


def _source(event):
    return {"transport": "feishu", "account_id": "librarian",
            "conversation_id": "chat", "source_event_id": event}


def test_epub_attachment_requires_selected_session_and_retries(tmp_path):
    staged = tmp_path / "staged.epub"
    with ZipFile(staged, "w") as archive:
        archive.writestr("mimetype", "application/epub+zip")
        archive.writestr("OEBPS/content.opf", "<package/>")
    request = {"owner_id": "owner", "actor_id": "person",
               "source": _source("file-1"), "data_path": str(staged)}
    with Library(tmp_path / "state") as lib:
        with pytest.raises(LibrarianError, match="select one"):
            store_inbound_epub(lib, request)
        session_inbound(lib, {"owner_id": "owner", "actor_id": "person",
                              "source": _source("read-1"), "action": "start",
                              "book": "社会理论二十讲", "isbn": "9787208171411"})
        stored = store_inbound_epub(lib, request)
        assert stored["status"] == "stored"
        assert (lib.root / "source-books" / "9787208171411.epub").read_bytes() == staged.read_bytes()
        assert store_inbound_epub(lib, request)["status"] == "unchanged"
        with pytest.raises(LibrarianError, match="select one"):
            store_inbound_epub(lib, {**request, "source": {**request["source"],
                                                            "conversation_id": "other"}})


def test_local_epub_inbox_is_selected_by_current_book(tmp_path):
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    epub = inbox / "社会理论二十讲 -- 作者.epub"
    with ZipFile(epub, "w") as archive:
        archive.writestr("mimetype", "application/epub+zip")
        archive.writestr("OEBPS/content.opf",
                         "<package><metadata><title>社会理论二十讲</title></metadata></package>")
    with Library(tmp_path / "state") as lib:
        session_inbound(lib, {"owner_id": "owner", "actor_id": "person",
                              "source": _source("read-1"), "action": "start",
                              "book": "社会理论二十讲", "isbn": "9787208171411"})
        result = store_inbound_epub(lib, {"owner_id": "owner", "actor_id": "person",
                                          "source": _source("file-1"),
                                          "inbox_root": str(inbox)})
        assert result["status"] == "stored"
        assert (lib.root / "source-books" / "9787208171411.epub").read_bytes() == epub.read_bytes()
