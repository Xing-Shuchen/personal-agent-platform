"""Evidence delivery uses a temporary crop of the immutable original."""
from io import BytesIO
from pathlib import Path

from PIL import Image
import pytest

from agents.librarian.runtime.gateway_evidence import prepare_evidence
from agents.librarian.runtime.store import LibrarianError


def test_prepare_evidence_crops_original_in_private_delivery_dir(tmp_path: Path) -> None:
    source = BytesIO()
    Image.new("RGB", (1000, 800), "white").save(source, "PNG")

    class FakeLibrary:
        def get(self, owner, model, trace_id):
            assert (owner, model, trace_id) == ("owner", "ReadingTrace", "rt_one")
            return {"medium": "physical", "location": {"kind": "physical",
                    "bbox": [.3, .4, .7, .5], "page_bbox": [0, 0, .8, 1]},
                    "source": {"capture_id": "capture_one"}}

        def read_original(self, owner, capture_id):
            assert (owner, capture_id) == ("owner", "capture_one")
            return source.getvalue()

    result = prepare_evidence(FakeLibrary(), "owner", "rt_one", tmp_path / "delivery-evidence")
    media = Path(result["media_path"])
    assert media.parent == tmp_path / "delivery-evidence"
    assert result["capture_id"] == "capture_one"
    assert media.stat().st_mode & 0o777 == 0o600
    with Image.open(media) as crop:
        assert crop.width < 800 and crop.height < 800
    assert source.getvalue().startswith(b"\x89PNG")


def test_digital_trace_cannot_be_opened_as_a_photo(tmp_path: Path) -> None:
    class DigitalLibrary:
        def get(self, *_args):
            return {"medium": "digital", "location": {"kind": "digital"}}

        def read_trace_evidence(self, *_args):
            raise AssertionError("digital source must not be read")

    with pytest.raises(LibrarianError) as error:
        prepare_evidence(DigitalLibrary(), "owner", "rt_digital", tmp_path / "delivery")
    assert error.value.code == "VALIDATION_FAILED"
