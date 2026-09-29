"""EPUB spine index with normalized-to-source code-point mapping."""
from __future__ import annotations

import hashlib
import json
import posixpath
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from zipfile import ZipFile

from lxml import etree

from .inputs import sha256

INDEX_VERSION = "0.1"
SKIP_TAGS = {"script", "style", "nav", "rt", "rp"}
BLOCK_TAGS = {"p", "h1", "h2", "h3", "h4", "h5", "h6", "li", "blockquote", "div"}


def local_name(element: etree._Element) -> str:
    return etree.QName(element).localname.lower() if isinstance(element.tag, str) else ""


def visible_text(element: etree._Element) -> str:
    if local_name(element) in SKIP_TAGS:
        return ""
    parts = [element.text or ""]
    for child in element:
        parts.append(visible_text(child))
        parts.append(child.tail or "")
    return "".join(parts)


def normalized(text: str) -> tuple[str, list[int]]:
    chars, mapping = [], []
    for offset, char in enumerate(text):
        for item in unicodedata.normalize("NFKC", char).casefold():
            if item.isalnum():
                chars.append(item)
                mapping.append(offset)
    return "".join(chars), mapping


class EpubIndex:
    def __init__(self, path: Path):
        self.path = path.resolve()
        self.sha256 = sha256(path)
        self.chapters: list[dict] = []
        self.paragraphs: list[dict] = []
        self.ngrams: dict[str, set[int]] = defaultdict(set)
        with ZipFile(path) as archive:
            container = etree.fromstring(archive.read("META-INF/container.xml"))
            opf_path = container.xpath("string(//*[local-name()='rootfile']/@full-path)")
            if not opf_path:
                raise ValueError("EPUB has no OPF rootfile")
            opf = etree.fromstring(archive.read(opf_path))
            manifest = {}
            for item in opf.xpath("//*[local-name()='manifest']/*[local-name()='item']"):
                manifest[item.get("id")] = (item.get("href"), item.get("media-type"),
                                            item.get("properties", ""))
            spine = opf.xpath("//*[local-name()='spine']/*[local-name()='itemref']")
            base = posixpath.dirname(opf_path)
            for spine_index, itemref in enumerate(spine):
                href, media, properties = manifest[itemref.get("idref")]
                if "nav" in properties.split() or media not in {
                        "application/xhtml+xml", "text/html"}:
                    continue
                internal = posixpath.normpath(posixpath.join(base, href.split("#")[0]))
                if internal.startswith("../"):
                    raise ValueError(f"EPUB href escapes archive: {href}")
                root = etree.fromstring(archive.read(internal),
                                        parser=etree.XMLParser(recover=True, no_network=True))
                bodies = root.xpath("//*[local-name()='body']")
                if not bodies:
                    raise ValueError(f"XHTML has no body: {href}")
                paragraphs = []
                for element in bodies[0].iter():
                    name = local_name(element)
                    if name not in BLOCK_TAGS:
                        continue
                    # Avoid duplicating a wrapper div/blockquote's descendant text.
                    if any(local_name(child) in BLOCK_TAGS for child in element.iterdescendants()):
                        continue
                    if any(local_name(parent) in SKIP_TAGS for parent in element.iterancestors()):
                        continue
                    raw = " ".join(visible_text(element).split())
                    if raw:
                        paragraphs.append((raw, element.get("id")))
                chapter_text = "\n".join(p[0] for p in paragraphs)
                chapter = {"spine_index": spine_index, "href": href,
                           "text": chapter_text,
                           "extracted_text_sha256": hashlib.sha256(
                               chapter_text.encode("utf-8")).hexdigest(),
                           "paragraphs": []}
                offset = 0
                for raw, element_id in paragraphs:
                    norm, mapping = normalized(raw)
                    paragraph = {"spine_index": spine_index, "href": href,
                                 "chapter": chapter, "start": offset,
                                 "end": offset + len(raw), "text": raw,
                                 "element_id": element_id, "norm": norm,
                                 "map": mapping}
                    para_id = len(self.paragraphs)
                    self.paragraphs.append(paragraph)
                    chapter["paragraphs"].append([offset, offset + len(raw)])
                    for gram in {norm[i:i + 3] for i in range(max(0, len(norm) - 2))}:
                        self.ngrams[gram].add(para_id)
                    offset += len(raw) + 1
                self.chapters.append(chapter)

    def candidates(self, query: str, limit: int = 30) -> list[dict]:
        norm, _ = normalized(query)
        if len(norm) < 3:
            return []
        exact = [i for i, p in enumerate(self.paragraphs) if norm in p["norm"]]
        counts = Counter()
        for gram in {norm[i:i + 3] for i in range(len(norm) - 2)}:
            counts.update(self.ngrams.get(gram, ()))
        ids = list(dict.fromkeys(exact + [i for i, _ in counts.most_common(limit)]))[:limit]
        from rapidfuzz import fuzz
        found = []
        for para_id in ids:
            p = self.paragraphs[para_id]
            alignment = fuzz.partial_ratio_alignment(norm, p["norm"])
            if not alignment or alignment.dest_end <= alignment.dest_start:
                continue
            begin = p["map"][alignment.dest_start]
            end = p["map"][alignment.dest_end - 1] + 1
            exact_text = p["text"][begin:end]
            candidate = {"epub_sha256": self.sha256,
                         "spine_index": p["spine_index"], "href": p["href"],
                         "text_index_version": INDEX_VERSION,
                         "extracted_text_sha256": p["chapter"]["extracted_text_sha256"],
                         "start": p["start"] + begin, "end": p["start"] + end,
                         "exact": exact_text,
                         "prefix": p["text"][max(0, begin - 24):begin],
                         "suffix": p["text"][end:end + 24],
                         "similarity": round(alignment.score / 100, 4),
                         "query_coverage": round(
                             (alignment.src_end - alignment.src_start) / len(norm), 4),
                         "element_id": p["element_id"],
                         "_alignment": alignment}
            found.append(candidate)
        found.sort(key=lambda item: (item["similarity"] * item["query_coverage"],
                                     len(item["exact"])), reverse=True)
        for item in found:
            item.pop("_alignment")
        return found

    def metadata(self) -> dict:
        return {"epub_sha256": self.sha256, "text_index_version": INDEX_VERSION,
                "spine_items": [{k: v for k, v in chapter.items() if k != "text"}
                                for chapter in self.chapters],
                "paragraph_count": len(self.paragraphs)}

    def export(self) -> dict:
        """Persist the exact extracted-text coordinate system and search mapping."""
        return {"epub_sha256": self.sha256, "text_index_version": INDEX_VERSION,
                "chapters": [{"spine_index": chapter["spine_index"],
                    "href": chapter["href"], "text": chapter["text"],
                    "extracted_text_sha256": chapter["extracted_text_sha256"],
                    "paragraphs": [{"start": p["start"], "end": p["end"],
                        "element_id": p["element_id"], "normalized": p["norm"],
                        "normalized_to_text_offset": [p["start"] + offset
                                                       for offset in p["map"]]}
                        for p in self.paragraphs if p["spine_index"] == chapter["spine_index"]]}
                    for chapter in self.chapters]}
