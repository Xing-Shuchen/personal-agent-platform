import io
import json
from types import SimpleNamespace

from PIL import Image

from agents.librarian.runtime import ocr
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


def test_marked_sentence_start_near_prior_punctuation_is_clipped() -> None:
    line = {"ocr_text": "社会学家帕森斯（TalcottParsons，1902—1979）的名字。正是帕森斯，在20世纪",
            "bbox": [.2, .5, .86, .53], "underline_span": [.7694, .8873]}
    text, box = ocr._visible_marked_text(line)
    assert text.startswith("正是帕森斯")
    assert box[0] > .69


def test_generic_ocr_keeps_mark_without_epub(monkeypatch) -> None:
    import rapidocr

    boxes = []
    for top in (200, 280, 360, 440, 520):
        boxes.append([[100, top], [800, top], [800, top + 35], [100, top + 35]])
    result = SimpleNamespace(boxes=boxes,
                             txts=[f"这是照片上第{i}行完整的印刷正文，可以用来检查画线。"
                                   for i in range(5)],
                             scores=[.95] * 5)
    monkeypatch.setattr(rapidocr, "RapidOCR", lambda: lambda _pixels: result)
    calls = []
    def underline(_gray, _points):
        calls.append(1)
        return (.3, [.1, .9]) if len(calls) == 2 else (0.0, [0, 0])
    monkeypatch.setattr(ocr, "_underline_evidence", underline)
    image = io.BytesIO()
    Image.new("RGB", (1000, 1400), "white").save(image, "PNG")
    output = ocr.ocr_extractor()(image.getvalue())
    observation = json.loads(output.observation)
    assert len(observation["marks"]) == 1
    assert len(observation["printed_regions"]) == 1
    assert observation["printed_regions"][0]["text"]["text"].startswith("这是照片上第1行")
    assert observation["pages"][0]["page"]["status"] == "unresolved"
    assert json.loads(output.raw)["epub_sha256"] is None


def test_printed_header_number_outweighs_inline_marginal_number(monkeypatch) -> None:
    from agents.librarian.runtime import ocr
    import rapidocr

    body_boxes = [[[150, top], [800, top], [800, top + 32], [150, top + 32]]
                  for top in (100, 190, 280, 370, 460)]
    boxes = ([[480, 45], [670, 45], [670, 65], [480, 65]],
             [[680, 45], [705, 45], [705, 65], [680, 65]],
             *body_boxes,
             [[810, 570], [835, 570], [835, 590], [810, 590]])
    texts = ["第二讲帕森斯与社会学理论", "23",
             *[f"这里是第{i}行完整的印刷正文，包含一整句话。" for i in range(5)], "41"]
    result = SimpleNamespace(boxes=boxes, txts=texts, scores=[.95] * len(texts))
    monkeypatch.setattr(rapidocr, "RapidOCR", lambda: lambda _pixels: result)
    monkeypatch.setattr(ocr, "_underline_evidence", lambda *_: (0.0, [0, 0]))
    image = io.BytesIO()
    Image.new("RGB", (1000, 1400), "white").save(image, "PNG")
    output = ocr.ocr_extractor()(image.getvalue())
    observation = json.loads(output.observation)
    assert [page["page"]["value"]["number"] for page in observation["pages"]] == [23]
    assert json.loads(output.raw)["page_markers"][0]["source"] == "header_ocr"


def test_visual_review_removes_weak_false_underline_but_retains_raw_evidence(monkeypatch) -> None:
    from agents.librarian.runtime import ocr
    import rapidocr

    boxes = [[[100, top], [800, top], [800, top + 35], [100, top + 35]]
             for top in (200, 280, 360, 440, 520)]
    result = SimpleNamespace(boxes=boxes,
                             txts=[f"这是照片上第{i}行完整的印刷正文，可以用来检查画线。"
                                   for i in range(5)], scores=[.95] * 5)
    monkeypatch.setattr(rapidocr, "RapidOCR", lambda: lambda _pixels: result)
    calls = []
    def underline(_gray, _points):
        calls.append(1)
        return (.08, [.1, .9]) if len(calls) == 2 else (0.0, [0, 0])
    monkeypatch.setattr(ocr, "_underline_evidence", underline)
    image = io.BytesIO()
    Image.new("RGB", (1000, 1400), "white").save(image, "PNG")
    output = ocr.ocr_extractor(underline_refiner=lambda _crop: (
        {"has_underline": False, "underlined_text": "", "uncertain": False},
        {"model": "fixture"}))(image.getvalue())
    observation = json.loads(output.observation)
    assert observation["marks"] == []
    assert observation["printed_regions"] == []
    raw = json.loads(output.raw)
    assert raw["lines"][1]["underline_score"] == .08
    assert raw["underline_refinements"][0]["answer"]["has_underline"] is False
