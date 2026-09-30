import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agents.librarian.runtime import bitable_handwriting as module


class FakeBase:
    def __init__(self, records=None):
        self.rows = records or []
        self.created = []
        self.updated = []
        self.uploaded = []

    def records(self, _app, _table):
        return self.rows

    def upload_crop(self, _app, image):
        self.uploaded.append(image)
        return "box_test"

    def create_record(self, _app, _table, fields):
        self.created.append(fields)
        return {"record_id": "rec_test"}

    def update_record(self, _app, _table, record_id, fields):
        self.updated.append((record_id, fields))


class ReviewBridgeTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "bitable-handwriting.json").write_text(
            '{"app_token":"bas_test","table_id":"tbl_test","url":"https://feishu.cn/base/bas_test"}')
        self.image = self.root / "note.png"
        self.image.write_bytes(b"image")

    def tearDown(self):
        self.temp.cleanup()

    def test_publish_preserves_existing_owner_edit(self):
        base = FakeBase([{"record_id": "rec_existing", "fields": {
            "Trace ID": "rt_existing", "源修订": 1,
            "核对文字": "用户已编辑", "处理状态": "待处理"}}])
        notes = [{"trace_id": name, "revision": 1, "book": "测试书",
                  "page": 23, "machine_text": "机器", "text": "机器",
                  "image": self.image} for name in ("rt_existing", "rt_new")]
        with patch.object(module, "Library"), patch.object(module, "pending_notes", return_value=notes):
            result = module.publish(base, self.root, "owner")
        self.assertEqual(result["created"], 1)
        self.assertEqual(base.updated, [])
        self.assertEqual(base.created[0]["Trace ID"], "rt_new")
        self.assertEqual(base.created[0]["原图局部"], [{"file_token": "box_test"}])

    def test_poll_applies_only_confirmed_decision(self):
        (self.root / "bitable-handwriting.json").write_text(
            '{"app_token":"bas_test","table_id":"tbl_test",'
            '"bindings":{"rt_a":{"record_id":"rec_a","revision":3},'
            '"rt_b":{"record_id":"rec_b","revision":1}}}')
        base = FakeBase([
            {"record_id": "rec_a", "fields": {"Trace ID": "rt_a", "源修订": 3,
             "核对决定": "确认", "核对文字": "  核对结果  ", "处理状态": "待处理"}},
            {"record_id": "rec_b", "fields": {"Trace ID": "rt_b", "源修订": 1,
             "核对决定": "待核对", "核对文字": "草稿", "处理状态": "待处理"}},
        ])
        with patch.object(module, "Library"), patch.object(
                module, "review_handwriting", return_value={
                    "status": "applied", "revision": 4}) as review:
            result = module.collect_decisions(base, self.root, "owner")
        self.assertEqual(result, {"applied": 1, "failed": 0, "conflicted": 0,
                                  "applied_records": [{"record_id": "rec_a", "book": ""}]})
        review.assert_called_once()
        self.assertEqual(review.call_args.args[2]["text"], "核对结果")
        self.assertEqual(base.updated[0][1]["处理状态"], "已入库")
        self.assertIn('"revision": 4',
                      (self.root / "bitable-handwriting.json").read_text())


if __name__ == "__main__":
    unittest.main()
