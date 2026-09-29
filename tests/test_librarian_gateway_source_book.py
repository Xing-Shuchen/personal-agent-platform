from pathlib import Path

import pytest

from agents.librarian.runtime.gateway_source_book import source_book_for_owner
from agents.librarian.runtime.store import Library, LibrarianError


def test_source_book_delivery_resolves_only_owner_catalogue(tmp_path: Path) -> None:
    source = tmp_path / "source-books"
    source.mkdir()
    epub = source / "9787208171411.epub"
    epub.write_bytes(b"synthetic epub payload")
    common = {"schema_version": "0.1.0", "owner_id": "owner_a",
              "created_at": "2026-09-29T00:00:00+00:00", "revision": 1,
              "supersedes_revision": None}
    with Library(tmp_path) as lib:
        lib.register("owner_a", {**common, "object_type": "Work",
                                 "id": "work_one", "title": "社会理论二十讲",
                                 "original_title": None, "authors": [],
                                 "identifiers": []})
        lib.register("owner_a", {**common, "object_type": "Edition",
                                 "id": "edition_one", "work_id": "work_one",
                                 "edition_label": None, "publisher": None,
                                 "publication_year": None,
                                 "isbn": {"isbn13": "9787208171411", "isbn10": None},
                                 "language": None, "page_count": None,
                                 "volume_label": None})
        result = source_book_for_owner(lib, "owner_a", "社会理论二十讲")
        assert result == {"book_title": "社会理论二十讲",
                          "isbn13": "9787208171411",
                          "media_path": str(epub.resolve()),
                          "byte_size": epub.stat().st_size}
        with pytest.raises(LibrarianError) as error:
            source_book_for_owner(lib, "owner_b", "社会理论二十讲")
        assert error.value.code == "OBJECT_NOT_FOUND"
        epub.unlink()
        with pytest.raises(LibrarianError) as error:
            source_book_for_owner(lib, "owner_a", "社会理论二十讲")
        assert error.value.code == "OBJECT_NOT_FOUND"


def test_source_book_rejects_path_escape(tmp_path: Path) -> None:
    source = tmp_path / "source-books"
    source.mkdir()
    outside = tmp_path / "outside.epub"
    outside.write_bytes(b"private")
    (source / "9787208171411.epub").symlink_to(outside)
    common = {"schema_version": "0.1.0", "owner_id": "owner_a",
              "created_at": "2026-09-29T00:00:00+00:00", "revision": 1,
              "supersedes_revision": None}
    with Library(tmp_path) as lib:
        lib.register("owner_a", {**common, "object_type": "Work", "id": "work_one",
                                 "title": "Test", "original_title": None,
                                 "authors": [], "identifiers": []})
        lib.register("owner_a", {**common, "object_type": "Edition",
                                 "id": "edition_one", "work_id": "work_one",
                                 "edition_label": None, "publisher": None,
                                 "publication_year": None,
                                 "isbn": {"isbn13": "9787208171411", "isbn10": None},
                                 "language": None, "page_count": None,
                                 "volume_label": None})
        with pytest.raises(LibrarianError) as error:
            source_book_for_owner(lib, "owner_a", "Test")
        assert error.value.code == "OBJECT_NOT_FOUND"
