from agents.librarian.runtime.ocr import _visible_marked_text


def test_marked_sentence_stays_within_photographed_line() -> None:
    first = {"ocr_text": "前一句没有画线。正是帕森斯，在20世纪",
             "bbox": [.1, .2, .9, .23], "underline_span": [.7, .9]}
    last = {"ocr_text": "著作树立为社会学思想的核心构成部分。下一句没有画线",
            "bbox": [.1, .3, .9, .33], "underline_span": [.15, .35]}
    first_text, first_box = _visible_marked_text(first)
    last_text, last_box = _visible_marked_text(last)
    assert first_text == "正是帕森斯，在20世纪"
    assert first_box[0] > first["bbox"][0]
    assert last_text == "著作树立为社会学思想的核心构成部分。"
    assert last_box[2] < last["bbox"][2]
