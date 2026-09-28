from agents.librarian.runtime.worker import _processing_batches


def _batch(number: int, second: int, conversation: str = "chat") -> dict:
    return {"id": f"batch_{number}", "received_at": f"2026-09-28T15:26:{second:02d}+00:00",
            "origin": {"transport": "feishu", "account_id": "librarian",
                       "conversation_id": conversation, "source_event_id": f"msg_{number}"},
            "capture_ids": [f"capture_{number}"]}


def test_quick_photo_sequence_gets_one_stable_review_batch():
    batches = [_batch(1, 0), _batch(2, 3), _batch(3, 7),
               _batch(4, 40), _batch(5, 41, "other")]
    grouped = _processing_batches(batches)
    assert [len(item["capture_ids"]) for item in grouped] == [3, 1, 1]
    assert grouped[0]["capture_ids"] == ["capture_1", "capture_2", "capture_3"]
    assert _processing_batches(batches)[0]["id"] == grouped[0]["id"]
