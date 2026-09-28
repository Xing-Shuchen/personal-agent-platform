from types import SimpleNamespace

from PIL import Image

from agents.librarian.runtime.ocr import _flip_bbox, _retry_ink_line_ocr, _upside_down_page


def _number(y):
    return [[5, y], [25, y], [25, y + 10], [5, y + 10]]


def test_bottom_header_number_detects_upside_down_page():
    assert _upside_down_page(SimpleNamespace(boxes=[_number(800)], txts=["23"]),
                             100, 1000)
    assert not _upside_down_page(SimpleNamespace(boxes=[_number(30)], txts=["23"]),
                                 100, 1000)
    assert not _upside_down_page(SimpleNamespace(boxes=[_number(800), _number(30)],
                                                 txts=["23", "42"]), 100, 1000)


def test_half_turn_maps_normalized_box_back_to_original():
    box = [.1, .2, .3, .4]
    assert _flip_bbox(_flip_bbox(box)) == box


def test_local_ocr_retry_selects_the_marked_line_not_its_neighbors():
    image = Image.new("RGB", (1000, 1000), "white")
    line = {"bbox": [.2, .5, .8, .52]}
    class GroundTruth:
        def match(self, value):
            return value, 1.0

    def engine(_pixels):
        return SimpleNamespace(
            boxes=[[[0, 0], [500, 0], [500, 10], [0, 10]],
                   [[0, 23], [500, 23], [500, 33], [0, 33]]],
            txts=["前一行文字应当排除在外而不能误选", "当前画线文字应当保留下来作为证据"],
            scores=[.99, .91])

    recovered = _retry_ink_line_ocr(engine, image, line, GroundTruth())
    assert recovered["ocr_text"] == "当前画线文字应当保留下来作为证据"
    assert recovered["local_ocr_retry"] is True
