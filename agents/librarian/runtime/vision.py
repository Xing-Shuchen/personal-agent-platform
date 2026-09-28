"""Claude Messages vision port for PageObservation extraction.

The immutable original remains in Library. This adapter sends an EXIF-oriented
derivative and returns the model's JSON text verbatim to process_capture, which
persists it before validating the observation. Credentials never enter records.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import os
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from PIL import Image, ImageOps

from .pipeline import ExtractionOutput, process_capture
from .store import Library


PROMPT_VERSION = "physical-page-v1"
PROMPT = """Return one JSON object only, with these required keys:
image_space, pages, printed_regions, marks, annotations, symbols, links,
warnings. Include optional visible_title only when it is legible.

This is an EXIF-oriented derivative of one physical book photo. Coordinates
must be [x1,y1,x2,y2] normalized to the ENTIRE supplied image, each in [0,1],
with positive area. The original image is {width}x{height} pixels. Set
image_space to {{"width":{width},"height":{height},
"basis":"exif_oriented_original"}}. A uniformly resized derivative has the
same normalized coordinates as the original. Do not report pixel coordinates.

For each visible page region return {{"id":"page_1","bbox":[...],
"side":"left|right|unknown","page":{{"value":{{"label":"171",
"number":171,"scheme":"arabic|roman|other"}} or null,
"confidence":0..1 or null,"basis":"vision|unknown",
"status":"resolved|unresolved"}}}}. Use null/unknown/unresolved if a page
number cannot be read. Do not infer one from neighboring images or text.

Return only printed text directly associated with a visible personal mark in
printed_regions. Each detection in printed_regions, marks, annotations and
symbols needs id, page_region_id, normalized bbox, kind, text (a TextField or
null), confidence (0..1 or null), linked_text_region_ids (array), and
link_confidence (0..1 or null). A TextField is {{"text":string or null,
"confidence":0..1 or null,"basis":"vision|unknown"}}. Use kind="printed"
for printed_regions; mark kinds may be underline, highlight, circle, bracket,
arrow, page_mark or unknown_mark; annotation kinds margin_note or inline_note;
symbol kind symbol. Keep every uncertain handwritten glyph as seen, such as
"Parsons?"; do not complete or reinterpret it. Text inside the printed page
is not a personal symbol. If a mark has no reliable associated text, leave its
links empty and keep the mark. Do not invent marks to match an expected count.

links is an array of {{"from_id":detection_id,"to_id":detection_id,
"kind":"annotates|continues|points_to","confidence":0..1 or null}} only
for visually supported relationships. A mark's linked_text_region_ids should
contain only directly associated printed region IDs. warnings is an array of
brief strings for visual limitations; use [] when none. All detection IDs must
be unique. Every detection must lie within its page region. If this is not a
book page, return empty pages/detection arrays and a warning.
"""


def _endpoint(base_url: str) -> str:
    base = base_url.rstrip("/")
    if base.endswith("/v1/messages"):
        return base
    if base.endswith("/v1"):
        return base + "/messages"
    return base + "/v1/messages"


def _chat_endpoint(base_url: str) -> str:
    base = base_url.rstrip("/")
    return base if base.endswith("/chat/completions") else base + "/chat/completions"


def _derivative(original: bytes, *, max_edge: int, max_pixels: int) -> tuple[bytes, int, int, int, int, tuple[str, ...]]:
    with Image.open(io.BytesIO(original)) as source:
        image = ImageOps.exif_transpose(source)
        image.load()
        width, height = image.size
        scale = min(1.0, max_edge / max(width, height),
                    (max_pixels / (width * height)) ** .5)
        if scale < 1:
            image = image.resize((max(1, int(width * scale)),
                                  max(1, int(height * scale))), Image.Resampling.LANCZOS)
        derivative_width, derivative_height = image.size
        if image.mode not in {"RGB", "L"}:
            image = image.convert("RGB")
        output = io.BytesIO()
        image.save(output, format="PNG", optimize=True)
        operations = ("exif_transpose", "uniform_resize") if scale < 1 else ("exif_transpose",)
        return output.getvalue(), width, height, derivative_width, derivative_height, operations


def anthropic_extractor(*, model: str, api_key: str, base_url: str = "https://api.anthropic.com",
                        max_edge: int = 2000, max_pixels: int = 2_000_000,
                        max_tokens: int = 8192, timeout: int = 180,
                        auth_mode: str = "api_key",
                        opener: Callable[..., Any] = urlopen) -> Callable[[bytes], ExtractionOutput]:
    """Build a callable compatible with process_capture's extraction port."""
    if not model or not api_key or not base_url.startswith("https://"):
        raise ValueError("model, key and HTTPS API base URL are required")
    if min(max_edge, max_pixels, max_tokens, timeout) <= 0:
        raise ValueError("positive vision limits required")
    if auth_mode not in {"api_key", "bearer"}:
        raise ValueError("unsupported vision auth mode")

    def extract(original: bytes) -> ExtractionOutput:
        derivative, width, height, derivative_width, derivative_height, operations = _derivative(
            original, max_edge=max_edge, max_pixels=max_pixels)
        payload = {"model": model, "max_tokens": max_tokens,
                   "messages": [{"role": "user", "content": [
                       {"type": "image", "source": {"type": "base64",
                        "media_type": "image/png",
                        "data": base64.b64encode(derivative).decode("ascii")},
                        "transformations": {"oversized_image": "error"}},
                       {"type": "text", "text": PROMPT.format(width=width, height=height)},
                   ]}]}
        auth_header = ({"x-api-key": api_key} if auth_mode == "api_key" else
                       {"authorization": f"Bearer {api_key}"})
        request = Request(_endpoint(base_url),
                          data=json.dumps(payload, separators=(",", ":")).encode(),
                          headers={**auth_header, "anthropic-version": "2023-06-01",
                                   "content-type": "application/json"}, method="POST")
        try:
            with opener(request, timeout=timeout) as response:
                envelope = json.load(response)
        except HTTPError as error:
            raise RuntimeError(f"vision provider HTTP {error.code}") from None
        except URLError as error:
            raise RuntimeError("vision provider unavailable") from error
        if not isinstance(envelope, dict) or envelope.get("stop_reason") != "end_turn":
            raise RuntimeError("vision response did not finish normally")
        blocks = envelope.get("content", [])
        texts = [block["text"] for block in blocks
                 if isinstance(block, dict) and block.get("type") == "text"
                 and isinstance(block.get("text"), str)]
        if len(texts) != 1:
            raise RuntimeError("vision response must contain one text block")
        return ExtractionOutput(raw=texts[0].encode("utf-8"), derivative=derivative,
                                derivative_width=derivative_width,
                                derivative_height=derivative_height,
                                operations=operations)

    return extract


def chat_completions_extractor(*, model: str, api_key: str, base_url: str,
                               max_edge: int = 2000, max_pixels: int = 2_000_000,
                               max_tokens: int = 8192, timeout: int = 180,
                               opener: Callable[..., Any] = urlopen) -> Callable[[bytes], ExtractionOutput]:
    """Build an OpenAI-compatible image extractor with the same evidence output."""
    if not model or not api_key or not base_url.startswith("https://"):
        raise ValueError("model, key and HTTPS API base URL are required")
    if min(max_edge, max_pixels, max_tokens, timeout) <= 0:
        raise ValueError("positive vision limits required")

    def extract(original: bytes) -> ExtractionOutput:
        derivative, width, height, derivative_width, derivative_height, operations = _derivative(
            original, max_edge=max_edge, max_pixels=max_pixels)
        payload = {"model": model, "max_tokens": max_tokens, "stream": False,
                   "messages": [{"role": "user", "content": [
                       {"type": "text", "text": PROMPT.format(width=width, height=height)},
                       {"type": "image_url", "image_url": {"url":
                        "data:image/png;base64," + base64.b64encode(derivative).decode("ascii")}},
                   ]}]}
        request = Request(_chat_endpoint(base_url),
                          data=json.dumps(payload, separators=(",", ":")).encode(),
                          headers={"authorization": f"Bearer {api_key}",
                                   "content-type": "application/json"}, method="POST")
        try:
            with opener(request, timeout=timeout) as response:
                envelope = json.load(response)
        except HTTPError as error:
            raise RuntimeError(f"vision provider HTTP {error.code}") from None
        except URLError as error:
            raise RuntimeError("vision provider unavailable") from error
        if not isinstance(envelope, dict):
            raise RuntimeError("vision response is not an object")
        choices = envelope.get("choices")
        if (not isinstance(choices, list) or len(choices) != 1
                or not isinstance(choices[0], dict)
                or choices[0].get("finish_reason") != "stop"):
            raise RuntimeError("vision response did not finish normally")
        message = choices[0].get("message")
        if (not isinstance(message, dict) or not isinstance(message.get("content"), str)
                or not message["content"].strip()):
            raise RuntimeError("vision response must contain one text message")
        return ExtractionOutput(raw=message["content"].encode("utf-8"), derivative=derivative,
                                derivative_width=derivative_width,
                                derivative_height=derivative_height,
                                operations=operations)

    return extract


def main() -> None:
    parser = argparse.ArgumentParser(description="Process one already accepted Librarian capture")
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--owner", required=True, help="trusted local owner ID")
    parser.add_argument("--capture", required=True)
    parser.add_argument("--provider", choices=("anthropic", "chat-completions"), default="anthropic")
    parser.add_argument("--model")
    parser.add_argument("--base-url")
    parser.add_argument("--max-edge", type=int, default=2000)
    parser.add_argument("--max-pixels", type=int, default=2_000_000)
    args = parser.parse_args()
    if args.provider == "anthropic":
        base_url = args.base_url or os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com")
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        model = args.model or os.environ.get("ANTHROPIC_MODEL")
        extractor = anthropic_extractor(
            model=model, api_key=api_key or os.environ.get("ANTHROPIC_AUTH_TOKEN", ""),
            auth_mode="api_key" if api_key else "bearer", base_url=base_url,
            max_edge=args.max_edge, max_pixels=args.max_pixels)
    else:
        base_url = args.base_url or os.environ.get("LIBRARIAN_VISION_BASE_URL", "")
        model = args.model or os.environ.get("LIBRARIAN_VISION_MODEL")
        extractor = chat_completions_extractor(
            model=model, api_key=os.environ.get("LIBRARIAN_VISION_API_KEY", ""),
            base_url=base_url, max_edge=args.max_edge, max_pixels=args.max_pixels)
    with Library(args.root) as lib:
        endpoint_id = hashlib.sha256(base_url.encode()).hexdigest()[:12]
        traces = process_capture(lib, args.owner, args.capture, extractor,
                                 extractor_version=(f"{args.provider}:{model}:{PROMPT_VERSION}:"
                                                    f"{args.max_edge}:{args.max_pixels}:{endpoint_id}"))
    print(json.dumps({"capture_id": args.capture,
                      "trace_refs": [{"trace_id": trace["id"],
                                      "revision": trace["revision"]} for trace in traces]}))


if __name__ == "__main__":
    main()
