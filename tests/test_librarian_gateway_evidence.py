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


def test_upside_down_trace_crop_is_upright_for_delivery(tmp_path: Path) -> None:
    source = BytesIO()
    image = Image.new("RGB", (200, 200), "red")
    from PIL import ImageDraw
    ImageDraw.Draw(image).rectangle((0, 100, 199, 199), fill="blue")
    image.save(source, "PNG")

    class FakeLibrary:
        def get(self, owner, model, identifier):
            assert owner == "owner"
            if model == "ReadingTrace":
                return {"medium": "physical", "location": {"kind": "physical",
                        "bbox": [0, 0, 1, 1], "page_bbox": [0, 0, 1, 1]},
                        "source": {"capture_id": "capture_one",
                                   "observation_id": "observation_one"}}
            assert (model, identifier) == ("PageObservation", "observation_one")
            return {"warnings": ["Upside-down scan analyzed after 180-degree rotation"]}

        def read_original(self, owner, capture_id):
            assert (owner, capture_id) == ("owner", "capture_one")
            return source.getvalue()

    result = prepare_evidence(FakeLibrary(), "owner", "rt_one", tmp_path / "delivery")
    with Image.open(result["media_path"]) as crop:
        assert crop.getpixel((100, 25))[2] > 200
        assert crop.getpixel((100, 175))[0] > 200


def test_bookscan_rotation_orients_stored_trace_crop(tmp_path: Path) -> None:
    import json
    source = BytesIO()
    image = Image.new("RGB", (200, 200), "red")
    from PIL import ImageDraw
    ImageDraw.Draw(image).rectangle((0, 100, 199, 199), fill="blue")
    image.save(source, "PNG")

    class FakeLibrary:
        def get(self, _owner, model, _identifier):
            if model == "ReadingTrace":
                return {"medium": "physical", "location": {"kind": "physical",
                        "bbox": [0, 0, 1, 1], "page_bbox": [0, 0, 1, 1]},
                        "source": {"capture_id": "capture_one",
                                   "observation_id": "observation_one"}}
            return {"extractor": "bookscan-segment-v1:test", "warnings": [],
                    "raw_output_asset": {}, "capture_id": "capture_one"}

        def _read_object(self, _asset):
            return json.dumps({"pages": [{"rotation": 180}]}).encode()

        def read_original(self, *_args):
            return source.getvalue()

    result = prepare_evidence(FakeLibrary(), "owner", "rt_one", tmp_path / "delivery")
    with Image.open(result["media_path"]) as crop:
        assert crop.getpixel((100, 25))[2] > 200
        assert crop.getpixel((100, 175))[0] > 200


def test_pending_scan_crop_uses_review_candidate_without_promotion(tmp_path: Path, monkeypatch) -> None:
    source = BytesIO()
    image = Image.new("RGB", (1000, 800), "white")
    from PIL import ImageDraw
    ImageDraw.Draw(image).rectangle((200, 320, 700, 400), fill="black")
    image.save(source, "PNG")

    def review(_lib, owner, capture_id):
        assert (owner, capture_id) == ("owner", "capture_scan")
        return {"proposed": [{"candidate_id": "candidate_one", "bbox": [.2, .4, .7, .5],
                              "page": {"number": 39, "label": "39"}}]}

    monkeypatch.setattr("agents.librarian.runtime.gateway_evidence.pending_extractions", review)

    class FakeLibrary:
        def get(self, owner, model, capture_id):
            assert (owner, model, capture_id) == ("owner", "PageCapture", "capture_scan")
            return {"id": capture_id}

        def read_original(self, owner, capture_id):
            assert (owner, capture_id) == ("owner", "capture_scan")
            return source.getvalue()

    directory = tmp_path / "delivery-evidence"
    result = prepare_evidence(FakeLibrary(), "owner", None, directory,
                              capture_id="capture_scan", candidate_index=0)
    assert result["source_status"] == "pending_review"
    assert result["candidate_index"] == 0
    assert result["candidate_id"] == "candidate_one"
    with Image.open(result["media_path"]) as crop:
        assert crop.size == (540, 112)
        assert crop.getpixel((270, 55)) == (0, 0, 0)
    with pytest.raises(LibrarianError):
        prepare_evidence(FakeLibrary(), "owner", None, directory,
                         capture_id="capture_scan", candidate_index=1)
    by_id = prepare_evidence(FakeLibrary(), "owner", None, directory,
                             capture_id="capture_scan", candidate_id="candidate_one")
    assert by_id["candidate_index"] == 0


def test_pending_handwritten_note_crop_shows_undetected_top_line(
        tmp_path: Path, monkeypatch) -> None:
    image = Image.new("RGB", (1000, 800), "white")
    from PIL import ImageDraw
    ImageDraw.Draw(image).rectangle((830, 295, 890, 315), fill="red")
    source = BytesIO()
    image.save(source, "PNG")

    monkeypatch.setattr(
        "agents.librarian.runtime.gateway_evidence.pending_extractions",
        lambda *_args: {"proposed": [{"candidate_id": "candidate_note",
                                      "bbox": [.8, .45, .92, .52],
                                      "annotation": "detected lower line",
                                      "page": None}]})

    class FakeLibrary:
        def get(self, _owner, _model, capture_id):
            return {"id": capture_id}

        def read_original(self, *_args):
            return source.getvalue()

    result = prepare_evidence(FakeLibrary(), "owner", None, tmp_path,
                              capture_id="capture_scan", candidate_index=0)
    with Image.open(result["media_path"]) as crop:
        assert crop.width >= 280 and crop.height >= 200
        red_pixels = sum(1 for pixel in crop.getdata()
                         if pixel[0] > 180 and pixel[1] < 90 and pixel[2] < 90)
        assert red_pixels > 100


def test_ocr_gap_crop_is_bound_to_current_pending_run(tmp_path: Path, monkeypatch) -> None:
    image = Image.new("RGB", (1000, 800), "white")
    from PIL import ImageDraw
    ImageDraw.Draw(image).rectangle((350, 350, 650, 380), fill="black")
    source = BytesIO()
    image.save(source, "PNG")
    monkeypatch.setattr(
        "agents.librarian.runtime.gateway_evidence.pending_extractions",
        lambda *_args: {"pending_run_id": "run_current", "ocr_gaps": [
            {"bbox": [.35, .43, .65, .49],
             "reason": "visible_ink_without_reliable_print_text"}]})

    class FakeLibrary:
        def get(self, _owner, _model, capture_id):
            return {"id": capture_id}

        def read_original(self, *_args):
            return source.getvalue()

    with pytest.raises(LibrarianError) as error:
        prepare_evidence(FakeLibrary(), "owner", None, tmp_path,
                         capture_id="capture_scan", pending_run_id="run_stale",
                         gap_index=0)
    assert error.value.code == "REVISION_CONFLICT"
    result = prepare_evidence(FakeLibrary(), "owner", None, tmp_path,
                              capture_id="capture_scan", pending_run_id="run_current",
                              gap_index=0)
    assert result["source_status"] == "pending_ocr_gap"
    assert result["gap_index"] == 0
    with Image.open(result["media_path"]) as crop:
        assert crop.getpixel((crop.width // 2, crop.height // 2))[0] < 100
