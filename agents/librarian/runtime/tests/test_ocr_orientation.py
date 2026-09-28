from types import SimpleNamespace

from agents.librarian.runtime.ocr import _flip_bbox, _upside_down_page


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
