"""OCR-to-EPUB matching with explicit visual and EPUB text provenance."""
from __future__ import annotations

from difflib import SequenceMatcher

from .epub import EpubIndex, normalized

SENTENCE_ENDINGS = "。！？!?"
CLAUSE_BOUNDARIES = "，,、；;：:"


def _expand_to_punctuation(index: EpubIndex, match: dict) -> dict:
    paragraph = next((p for p in index.paragraphs
                      if p["spine_index"] == match["spine_index"]
                      and p["start"] <= match["start"]
                      and match["end"] <= p["end"]), None)
    if paragraph is None:
        return {**match, "expanded_exact": match["exact"],
                "expanded_start": match["start"], "expanded_end": match["end"],
                "extension_prefix": "", "extension_suffix": ""}
    text = paragraph["text"]
    start = match["start"] - paragraph["start"]
    end = match["end"] - paragraph["start"]
    left = max((i + 1 for i, char in enumerate(text[:start])
                if char in SENTENCE_ENDINGS), default=None)
    if left is None:
        left = max((i + 1 for i, char in enumerate(text[:start])
                    if char in CLAUSE_BOUNDARIES), default=0)
    sentence_end = next((i + 1 for i in range(end, len(text))
                         if text[i] in SENTENCE_ENDINGS), None)
    if end > 0 and text[end - 1] in SENTENCE_ENDINGS:
        right = end
    elif sentence_end is not None:
        right = sentence_end
    else:
        clause_end = next((i for i in range(end, len(text))
                           if text[i] in CLAUSE_BOUNDARIES), len(text))
        right = clause_end
        if right == end and end > 0 and text[end - 1] in CLAUSE_BOUNDARIES:
            right -= 1
    # Whitespace at boundaries is presentation, not visible sentence content.
    while left < start and text[left].isspace():
        left += 1
    while right > end and text[right - 1].isspace():
        right -= 1
    if not (left <= start and right >= end - 1):
        raise AssertionError("EPUB expansion unexpectedly contracted its matched span")
    return {**match, "expanded_exact": text[left:right],
            "expanded_start": paragraph["start"] + left,
            "expanded_end": paragraph["start"] + right,
            "extension_prefix": text[left:start],
            "extension_suffix": text[end:right]}


def _map_ocr_boundary(source: str, target: str, position: int) -> int:
    """Map a character boundary through the full-line OCR/EPUB alignment."""
    opcodes = SequenceMatcher(None, source, target, autojunk=False).get_opcodes()
    for _, a1, a2, b1, b2 in opcodes:
        if a1 <= position <= a2 and a2 > a1:
            return b1 + round((position - a1) / (a2 - a1) * (b2 - b1))
    return len(target)


def align_group(ocr_query: str, index: EpubIndex, config: dict,
                marked_ocr_span: list[int] | None = None) -> dict:
    base = {"epub_candidate": None, "epub_expanded_text": None,
            "text_effective": ocr_query, "text_basis": "visual_ocr",
            "match_status": "unmatched", "review_reasons": []}
    if not ocr_query.strip():
        return {**base, "match_status": "ocr_failed",
                "review_reasons": ["empty_ocr"]}
    candidates = index.candidates(ocr_query)
    if not candidates:
        return {**base, "review_reasons": ["no_epub_candidate"]}
    first = candidates[0].copy()
    if marked_ocr_span is not None:
        a, b = marked_ocr_span
        if not (0 <= a < b <= len(ocr_query)):
            return {**base, "match_status": "needs_review",
                    "review_reasons": ["invalid_marked_span"]}
        full = first.copy()
        start = _map_ocr_boundary(ocr_query, full["exact"], a)
        end = _map_ocr_boundary(ocr_query, full["exact"], b)
        if start >= end:
            return {**base, "epub_candidate": full,
                    "match_status": "needs_review",
                    "review_reasons": ["unmapped_marked_span"]}
        first.update({"full_match_start": full["start"],
                      "full_match_end": full["end"],
                      "full_match_exact": full["exact"],
                      "start": full["start"] + start,
                      "end": full["start"] + end,
                      "exact": full["exact"][start:end]})
    first = _expand_to_punctuation(index, first)
    second = candidates[1] if len(candidates) > 1 else None
    margin = first["similarity"] * first["query_coverage"] - (
        second["similarity"] * second["query_coverage"] if second else 0)
    first["runner_up_margin"] = round(margin, 4)
    reasons = []
    if first["similarity"] < float(config.get("min_similarity", .87)):
        reasons.append("weak_similarity")
    if first["query_coverage"] < float(config.get("min_query_coverage", .9)):
        reasons.append("low_query_coverage")
    if margin < float(config.get("min_runner_up_margin", .06)):
        reasons.append("epub_ambiguous")
    if reasons:
        return {**base, "epub_candidate": first,
                "epub_expanded_text": first["expanded_exact"],
                "match_status": "needs_review", "review_reasons": reasons}
    return {**base, "epub_candidate": first,
            "epub_expanded_text": first["expanded_exact"],
            "text_effective": first["expanded_exact"],
            "text_basis": "epub_punctuation_expansion",
            "match_status": "matched"}


def edits_for(ocr: str, candidate: dict) -> list[dict]:
    target = candidate["exact"]
    edits = []
    for operation, a1, a2, b1, b2 in SequenceMatcher(
            None, ocr, target, autojunk=False).get_opcodes():
        if operation == "replace":
            operation = "substitute"
        if operation == "equal":
            continue
        edge = a1 == 0 or a2 == len(ocr) or b1 == 0 or b2 == len(target)
        edits.append({"operation": operation,
                      "ocr_span": [a1, a2],
                      "epub_span": [candidate["start"] + b1,
                                    candidate["start"] + b2],
                      "before": ocr[a1:a2], "after": target[b1:b2],
                      "position": "leading" if a1 == 0 or b1 == 0 else
                                  "trailing" if edge else "internal",
                      "evidence": "ocr_alignment" if operation == "substitute" and not edge
                                  else "unverified"})
    return edits


def align_line(ocr_raw: str, index: EpubIndex, config: dict) -> dict:
    empty = {"candidate_text": None, "corrected_text": None,
             "text_effective": ocr_raw, "match_status": "unmatched",
             "review_status": "unreviewed", "epub_match": None,
             "epub_runner_up": None, "edits": [], "review_reasons": []}
    if not ocr_raw.strip():
        return {**empty, "match_status": "ocr_failed",
                "review_reasons": ["empty_ocr"]}
    candidates = index.candidates(ocr_raw)
    if not candidates:
        return {**empty, "review_reasons": ["no_candidate"]}
    first = candidates[0].copy()
    second = candidates[1].copy() if len(candidates) > 1 else None
    margin = first["similarity"] * first["query_coverage"] - (
        second["similarity"] * second["query_coverage"] if second else 0)
    first["runner_up_margin"] = round(margin, 4)
    edits = edits_for(ocr_raw, first)
    min_similarity = float(config.get("min_similarity", .87))
    min_coverage = float(config.get("min_query_coverage", .9))
    min_margin = float(config.get("min_runner_up_margin", .06))
    reasons = []
    if first["similarity"] < min_similarity:
        reasons.append("weak_similarity")
    if first["query_coverage"] < min_coverage:
        reasons.append("low_query_coverage")
    if margin < min_margin:
        reasons.append("epub_ambiguous")
    # A line span cannot be much longer than the OCR line. This catches many
    # accidental paragraph expansions before considering any edit operation.
    source_norm, _ = normalized(ocr_raw)
    target_norm, _ = normalized(first["exact"])
    if len(target_norm) > len(source_norm) + 2:
        reasons.append("boundary_risk")
    if any(edit["operation"] != "substitute" or edit["position"] != "internal"
           or len(edit["before"]) != len(edit["after"]) or
           len(edit["before"]) > 2 for edit in edits):
        reasons.append("edit_requires_visual_review")
    # The EPUB can be a different edition; a candidate is not image evidence.
    if reasons:
        status, corrected = "needs_review", None
    else:
        status, corrected = "matched", first["exact"]
    return {**empty, "candidate_text": first["exact"],
            "corrected_text": corrected,
            "text_effective": corrected if corrected is not None else ocr_raw,
            "match_status": status, "epub_match": first,
            "epub_runner_up": second, "edits": edits,
            "review_reasons": reasons}
