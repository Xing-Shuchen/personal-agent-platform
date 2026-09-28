from __future__ import annotations

import base64
import io
import json

import pytest
from PIL import Image

from agents.librarian.runtime.pipeline import process_capture
from agents.librarian.runtime.store import Library, LibrarianError
from agents.librarian.runtime.vision import anthropic_extractor, chat_completions_extractor


def _photo() -> bytes:
    output = io.BytesIO()
    exif = Image.Exif()
    exif[274] = 6
    Image.new("RGB", (1000, 1400), "white").save(output, format="JPEG", exif=exif)
    return output.getvalue()


def test_vision_port_orients_derivative_and_persists_model_text(tmp_path):
    observation = {"image_space": {"width": 1400, "height": 1000,
                                   "basis": "exif_oriented_original"},
                   "pages": [{"id": "page_1", "bbox": [0, 0, 1, 1],
                              "side": "unknown",
                              "page": {"value": None, "confidence": None,
                                       "basis": "unknown", "status": "unresolved"}}],
                   "printed_regions": [{"id": "printed_1", "page_region_id": "page_1",
                                        "bbox": [.1, .2, .8, .3], "kind": "printed",
                                        "text": {"text": "Synthetic sentence", "confidence": .8,
                                                 "basis": "vision"}, "confidence": .8,
                                        "linked_text_region_ids": [], "link_confidence": None}],
                   "marks": [{"id": "mark_1", "page_region_id": "page_1",
                              "bbox": [.1, .29, .8, .32], "kind": "underline",
                              "text": None, "confidence": .9,
                              "linked_text_region_ids": ["printed_1"],
                              "link_confidence": .9}], "annotations": [],
                   "symbols": [], "links": [], "warnings": []}
    raw_text = json.dumps(observation, ensure_ascii=False).encode()
    sent = []

    def opener(request, *, timeout):
        sent.append((request, timeout))
        payload = json.loads(request.data)
        assert request.full_url == "https://vision.example/v1/messages"
        assert payload["model"] == "synthetic-vision"
        image = payload["messages"][0]["content"][0]
        assert image["transformations"]["oversized_image"] == "error"
        with Image.open(io.BytesIO(base64.b64decode(image["source"]["data"]))) as derivative:
            assert derivative.size == (700, 500)
        prompt = payload["messages"][0]["content"][1]["text"]
        assert '"width":1400' in prompt and '"height":1000' in prompt
        return io.BytesIO(json.dumps({"content": [{"type": "text", "text": raw_text.decode()}],
                                      "stop_reason": "end_turn"}).encode())

    extractor = anthropic_extractor(model="synthetic-vision", api_key="test-key",
                                    base_url="https://vision.example/v1",
                                    max_edge=700, max_pixels=1_000_000, opener=opener)
    with Library(tmp_path) as lib:
        receipt = lib.ingest("owner_a", transport="gateway", account_id="a",
                             conversation_id="c", source_event_id="m",
                             attachments=[{"source_item_id": "i", "mime_type": "image/jpeg",
                                           "data": _photo()}], idempotency_key="k")
        capture_id = receipt["capture_ids"][0]
        traces = process_capture(lib, "owner_a", capture_id, extractor,
                                 extractor_version="synthetic-vision")
        assert len(traces) == 1
        row = lib.db.execute("SELECT raw_asset FROM extractor_attempts").fetchone()
        raw_asset = json.loads(row["raw_asset"])
        assert (tmp_path / raw_asset["object_key"]).read_bytes() == raw_text
        derivative = json.loads(lib.db.execute(
            "SELECT derivative FROM extractor_derivatives WHERE owner_id='owner_a'").fetchone()[0])
        assert derivative["width"] == 700 and derivative["height"] == 500
        assert derivative["operations"] == ["exif_transpose", "uniform_resize"]
        assert (tmp_path / derivative["asset"]["object_key"]).is_file()
        observation = json.loads(lib.db.execute(
            "SELECT body FROM records WHERE model='PageObservation'").fetchone()[0])
        assert observation["derivative"] == derivative
        assert traces[0]["provenance"][1] == derivative["asset"]
        assert lib.read_trace_evidence("owner_a", traces[0]["id"], index=1)[0] == (
            tmp_path / derivative["asset"]["object_key"]).read_bytes()
        assert len(sent) == 1
        assert process_capture(lib, "owner_a", capture_id, extractor,
                               extractor_version="synthetic-vision") == traces
        assert len(sent) == 1


def test_invalid_vision_json_keeps_raw_text_and_derivative(tmp_path):
    def opener(_request, *, timeout):
        return io.BytesIO(json.dumps({"content": [{"type": "text", "text": "{invalid"}],
                                      "stop_reason": "end_turn"}).encode())

    extractor = anthropic_extractor(model="synthetic-vision", api_key="test-key",
                                    base_url="https://vision.example", max_edge=700,
                                    opener=opener)
    with Library(tmp_path) as lib:
        receipt = lib.ingest("owner_a", transport="gateway", account_id="a",
                             conversation_id="c", source_event_id="m",
                             attachments=[{"source_item_id": "i", "mime_type": "image/jpeg",
                                           "data": _photo()}], idempotency_key="k")
        with pytest.raises(LibrarianError) as error:
            process_capture(lib, "owner_a", receipt["capture_ids"][0], extractor,
                            extractor_version="synthetic-vision")
        assert error.value.code == "EXTRACTION_SCHEMA_INVALID"
        row = lib.db.execute("SELECT run_id,raw_asset FROM extractor_attempts").fetchone()
        assert (tmp_path / json.loads(row["raw_asset"])["object_key"]).read_bytes() == b"{invalid"
        derivative = json.loads(lib.db.execute(
            "SELECT derivative FROM extractor_derivatives WHERE run_id=?",
            (row["run_id"],)).fetchone()[0])
        assert (tmp_path / derivative["asset"]["object_key"]).is_file()
        assert lib.db.execute("SELECT COUNT(*) FROM records WHERE model='ReadingTrace'").fetchone()[0] == 0


def test_bearer_mode_sends_authorization_header():
    def opener(request, *, timeout):
        assert request.get_header("Authorization") == "Bearer test-token"
        assert request.get_header("X-api-key") is None
        return io.BytesIO(json.dumps({"content": [{"type": "text", "text": "{}"}],
                                      "stop_reason": "end_turn"}).encode())

    extractor = anthropic_extractor(model="synthetic-vision", api_key="test-token",
                                    base_url="https://vision.example", auth_mode="bearer",
                                    opener=opener)
    assert extractor(_photo()).raw == b"{}"


def test_truncated_provider_reply_is_not_accepted_as_observation():
    def opener(_request, *, timeout):
        return io.BytesIO(json.dumps({"content": [{"type": "text", "text": "{}"}],
                                      "stop_reason": "max_tokens"}).encode())

    extractor = anthropic_extractor(model="synthetic-vision", api_key="test-key",
                                    base_url="https://vision.example", opener=opener)
    with pytest.raises(RuntimeError, match="did not finish normally"):
        extractor(_photo())


def test_provider_timeout_keeps_original_and_records_failed_run(tmp_path):
    def opener(_request, *, timeout):
        raise TimeoutError("provider timed out")

    extractor = anthropic_extractor(model="synthetic-vision", api_key="test-key",
                                    base_url="https://vision.example", opener=opener)
    photo = _photo()
    with Library(tmp_path) as lib:
        receipt = lib.ingest("owner_a", transport="gateway", account_id="a",
                             conversation_id="c", source_event_id="m",
                             attachments=[{"source_item_id": "i", "mime_type": "image/jpeg",
                                           "data": photo}], idempotency_key="k")
        capture_id = receipt["capture_ids"][0]
        with pytest.raises(LibrarianError) as error:
            process_capture(lib, "owner_a", capture_id, extractor,
                            extractor_version="synthetic-vision")
        assert error.value.code == "EXTRACTOR_UNAVAILABLE"
        assert lib.read_original("owner_a", capture_id) == photo
        failed = json.loads(lib.db.execute(
            "SELECT body FROM records WHERE model='ProcessingRun'").fetchone()[0])
        assert failed["capture_id"] == capture_id
        assert failed["outcome"] == "failed"
        assert lib.db.execute(
            "SELECT COUNT(*) FROM records WHERE model='ReadingTrace'").fetchone()[0] == 0


def test_chat_completions_image_transport_persists_observation(tmp_path):
    observation = {"image_space": {"width": 1400, "height": 1000,
                                   "basis": "exif_oriented_original"},
                   "pages": [{"id": "page_1", "bbox": [0, 0, 1, 1], "side": "unknown",
                              "page": {"value": None, "confidence": None,
                                       "basis": "unknown", "status": "unresolved"}}],
                   "printed_regions": [],
                   "marks": [{"id": "mark_1", "page_region_id": "page_1",
                              "bbox": [.1, .2, .8, .3], "kind": "underline",
                              "text": None, "confidence": .9,
                              "linked_text_region_ids": [], "link_confidence": None}],
                   "annotations": [], "symbols": [], "links": [], "warnings": []}
    raw_text = json.dumps(observation).encode()

    def opener(request, *, timeout):
        assert request.full_url == "https://vision.example/v1/chat/completions"
        assert request.get_header("Authorization") == "Bearer test-key"
        payload = json.loads(request.data)
        assert payload["model"] == "vision-model"
        assert payload["stream"] is False
        content = payload["messages"][0]["content"]
        assert content[0]["type"] == "text"
        assert '"width":1400' in content[0]["text"]
        assert content[1]["type"] == "image_url"
        data_url = content[1]["image_url"]["url"]
        assert data_url.startswith("data:image/png;base64,")
        with Image.open(io.BytesIO(base64.b64decode(data_url.split(",", 1)[1]))) as image:
            assert image.size == (700, 500)
        return io.BytesIO(json.dumps({"choices": [{"finish_reason": "stop",
                        "message": {"role": "assistant", "content": raw_text.decode()}}]}).encode())

    extractor = chat_completions_extractor(model="vision-model", api_key="test-key",
                                           base_url="https://vision.example/v1",
                                           max_edge=700, opener=opener)
    with Library(tmp_path) as lib:
        receipt = lib.ingest("owner_a", transport="gateway", account_id="a",
                             conversation_id="c", source_event_id="m",
                             attachments=[{"source_item_id": "i", "mime_type": "image/jpeg",
                                           "data": _photo()}], idempotency_key="k")
        traces = process_capture(lib, "owner_a", receipt["capture_ids"][0], extractor,
                                 extractor_version="chat-vision")
        assert len(traces) == 1
        raw_asset = json.loads(lib.db.execute(
            "SELECT raw_asset FROM extractor_attempts").fetchone()[0])
        assert (tmp_path / raw_asset["object_key"]).read_bytes() == raw_text
        assert lib.db.execute("SELECT COUNT(*) FROM extractor_derivatives").fetchone()[0] == 1


def test_chat_completions_rejects_unfinished_reply():
    def opener(_request, *, timeout):
        return io.BytesIO(json.dumps({"choices": [{"finish_reason": "length",
                        "message": {"role": "assistant", "content": "{}"}}]}).encode())

    extractor = chat_completions_extractor(model="vision-model", api_key="test-key",
                                           base_url="https://vision.example/v1",
                                           opener=opener)
    with pytest.raises(RuntimeError, match="did not finish normally"):
        extractor(_photo())
