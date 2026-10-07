"""Publish BookScan handwriting reviews to Feishu Base and import owner decisions."""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import mimetypes
import os
import subprocess
import time
import uuid
from pathlib import Path
from urllib import error, parse, request

from .handwriting_review import ACCEPTED, REJECTED, review_handwriting
from .review_index import _bookscan_run_dir, build_index
from .store import Library, LibrarianError

API = "https://open.feishu.cn/open-apis/"
FIELDS = {
    "条目": (1, None),
    "书名": (1, None),
    "页码": (1, None),
    "机器初稿": (1, None),
    "核对文字": (1, None),
    "核对决定": (3, ["待核对", "确认", "排除"]),
    "处理状态": (3, ["待处理", "已入库", "冲突", "失败"]),
    "错误说明": (1, None),
    "Vault 同步": (1, None),
    "Trace ID": (1, None),
    "源修订": (2, None),
    "原图局部": (17, None),
}
REVIEW_HIDDEN_FIELDS = ("Trace ID", "源修订", "错误说明", "Vault 同步")


class FeishuError(RuntimeError):
    def __init__(self, code: int, message: str):
        super().__init__(f"Feishu API {code}: {message}")
        self.code = code


class FeishuBase:
    def __init__(self, app_id: str, app_secret: str):
        if not app_id or not app_secret:
            raise ValueError("Feishu app ID and secret required")
        self.app_id = app_id
        self.app_secret = app_secret
        self.token: str | None = None

    def _send(self, method: str, path: str, body: bytes | None = None,
              content_type: str = "application/json") -> dict:
        headers = {"Content-Type": content_type}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        req = request.Request(API + path, data=body, headers=headers, method=method)
        try:
            with request.urlopen(req, timeout=45) as response:
                result = json.load(response)
        except error.HTTPError as exc:
            try:
                result = json.loads(exc.read())
            except (ValueError, UnicodeDecodeError):
                raise FeishuError(exc.code, "HTTP error") from exc
        if result.get("code") != 0:
            raise FeishuError(result.get("code", -1), result.get("msg", "unknown error"))
        if path == "auth/v3/tenant_access_token/internal":
            return result
        return result.get("data") or {}

    def json(self, method: str, path: str, payload: dict | None = None) -> dict:
        body = json.dumps(payload, ensure_ascii=False).encode() if payload is not None else None
        return self._send(method, path, body)

    def authenticate(self) -> None:
        data = self.json("POST", "auth/v3/tenant_access_token/internal",
                         {"app_id": self.app_id, "app_secret": self.app_secret})
        self.token = data.get("tenant_access_token")
        if not self.token:
            raise FeishuError(-1, "tenant_access_token missing")

    def upload_crop(self, base_token: str, image: Path) -> str:
        content = image.read_bytes()
        if not content or len(content) > 20 * 1024 * 1024:
            raise ValueError("handwriting crop missing or too large")
        boundary = "librarian-" + uuid.uuid4().hex
        fields = {"file_name": image.name, "parent_type": "bitable_file",
                  "parent_node": base_token, "size": str(len(content))}
        chunks = []
        for key, value in fields.items():
            chunks.append((f"--{boundary}\r\nContent-Disposition: form-data; "
                           f"name=\"{key}\"\r\n\r\n{value}\r\n").encode())
        mime = mimetypes.guess_type(image.name)[0] or "image/png"
        chunks.append((f"--{boundary}\r\nContent-Disposition: form-data; "
                       f"name=\"file\"; filename=\"{image.name}\"\r\n"
                       f"Content-Type: {mime}\r\n\r\n").encode())
        chunks.extend([content, f"\r\n--{boundary}--\r\n".encode()])
        data = self._send("POST", "drive/v1/medias/upload_all", b"".join(chunks),
                          f"multipart/form-data; boundary={boundary}")
        token = data.get("file_token")
        if not token:
            raise FeishuError(-1, "media upload returned no file token")
        return token

    def records(self, app_token: str, table_id: str) -> list[dict]:
        rows, cursor = [], None
        while True:
            params = {"page_size": "500"}
            if cursor:
                params["page_token"] = cursor
            path = f"bitable/v1/apps/{app_token}/tables/{table_id}/records?" + parse.urlencode(params)
            data = self.json("GET", path)
            rows.extend(data.get("items") or [])
            if not data.get("has_more"):
                return rows
            cursor = data.get("page_token")
            if not cursor:
                raise FeishuError(-1, "record pagination cursor missing")

    def create_record(self, app_token: str, table_id: str, fields: dict) -> dict:
        return self.json("POST", f"bitable/v1/apps/{app_token}/tables/{table_id}/records",
                         {"fields": fields}).get("record") or {}

    def update_record(self, app_token: str, table_id: str, record_id: str,
                      fields: dict) -> None:
        self.json("PUT", f"bitable/v1/apps/{app_token}/tables/{table_id}/records/{record_id}",
                  {"fields": fields})


def _text(value: object) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "".join(item.get("text", "") for item in value if isinstance(item, dict))
    return "" if value is None else str(value)


def _state_path(root: Path) -> Path:
    return root / "bitable-handwriting.json"


def _load_state(root: Path) -> dict:
    path = _state_path(root)
    if not path.is_file():
        raise RuntimeError("Bitable not initialized; run bootstrap first")
    return json.loads(path.read_text(encoding="utf-8"))


def _save_state(root: Path, state: dict) -> None:
    path = _state_path(root)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n",
                         encoding="utf-8")
    os.chmod(temporary, 0o600)
    temporary.replace(path)


def bootstrap(client: FeishuBase, root: Path) -> dict:
    state = json.loads(_state_path(root).read_text()) if _state_path(root).is_file() else {}
    if not state.get("app_token"):
        app = client.json("POST", "bitable/v1/apps",
                          {"name": "图书专员 · 手写笔记核对"}).get("app") or {}
        state["app_token"] = app["app_token"]
        state["url"] = app.get("url") or f"https://feishu.cn/base/{app['app_token']}"
        _save_state(root, state)
    app_token = state["app_token"]
    if not state.get("table_id"):
        listed = client.json("GET", f"bitable/v1/apps/{app_token}/tables?page_size=100")
        matches = [item for item in listed.get("items") or []
                   if item.get("name") == "手写笔记核对"]
        if len(matches) > 1:
            raise RuntimeError("multiple handwriting tables found")
        if matches:
            state["table_id"] = matches[0]["table_id"]
        else:
            table = client.json("POST", f"bitable/v1/apps/{app_token}/tables",
                                {"table": {"name": "手写笔记核对",
                                           "default_view_name": "全部",
                                           "fields": [{"field_name": "条目", "type": 1}]}})
            state["table_id"] = table["table_id"]
        _save_state(root, state)
    state.setdefault("base_url", state["url"].split("?", 1)[0])
    state["url"] = f"{state['base_url']}?table={state['table_id']}"
    _save_state(root, state)
    path = f"bitable/v1/apps/{app_token}/tables/{state['table_id']}/fields"
    found = {}
    cursor = None
    while True:
        params = {"page_size": "100"}
        if cursor:
            params["page_token"] = cursor
        result = client.json("GET", path + "?" + parse.urlencode(params))
        found.update({field["field_name"]: field for field in result.get("items") or []})
        if not result.get("has_more"):
            break
        cursor = result.get("page_token")
        if not cursor:
            raise FeishuError(-1, "field pagination cursor missing")
    for name, (field_type, options) in FIELDS.items():
        if name in found:
            if found[name]["type"] != field_type:
                raise RuntimeError(f"field type mismatch: {name}")
            continue
        field = {"field_name": name, "type": field_type}
        if options:
            field["property"] = {"options": [{"name": option} for option in options]}
        created = client.json("POST", path, field).get("field") or {}
        found[name] = created
    views_path = f"bitable/v1/apps/{app_token}/tables/{state['table_id']}/views"
    views = client.json("GET", views_path + "?page_size=100").get("items") or []
    grid = next((view for view in views if view.get("view_type") == "grid"), None)
    if grid:
        hidden = [found[name]["field_id"] for name in REVIEW_HIDDEN_FIELDS]
        client.json("PATCH", f"{views_path}/{grid['view_id']}", {
            "view_name": "手写笔记核对（表格）", "property": {"hidden_fields": hidden}})
    gallery = next((view for view in views if view.get("view_name") == "看图核对"), None)
    if not gallery:
        gallery = client.json("POST", views_path,
                              {"view_name": "看图核对", "view_type": "gallery"})["view"]
    state["review_url"] = f"{state['url']}&view={gallery['view_id']}"
    _save_state(root, state)
    return state


def pending_notes(lib: Library, root: Path, owner: str) -> list[dict]:
    notes = []
    for row in lib.db.execute("SELECT body FROM records WHERE owner_id=? AND "
                              "model='ReadingTrace' AND current=1", (owner,)):
        trace = json.loads(row["body"])
        ids = trace.get("source", {}).get("detection_ids", [])
        if (trace["medium"] != "physical" or trace["status"] != "active" or
                "margin_note" not in trace["trace_types"] or len(ids) != 1 or
                not ids[0].startswith("bookscan_note_") or
                trace["review"].get("reason") in {ACCEPTED, REJECTED}):
            continue
        try:
            index = int(ids[0][len("bookscan_note_"):])
            observation = lib.get(owner, "PageObservation", trace["source"]["observation_id"])
            report = json.loads(lib._read_object(observation["raw_output_asset"]))
            annotation = report["annotations"][index]
            image = (_bookscan_run_dir(root, report["run"]) / "annotations" /
                     f"{annotation['annotation_id']}.png").resolve()
            image.relative_to((root / "bookscan-runs").resolve())
            if not image.is_file():
                continue
            work = lib.get(owner, "Work", trace["work_id"]) if trace["work_id"] else None
            notes.append({"trace_id": trace["id"], "revision": trace["revision"],
                          "book": work["title"] if work else "",
                          "page": (trace["location"].get("page") or {}).get("number"),
                          "machine_text": annotation.get("ocr_raw") or "",
                          "text": trace["content"]["annotation"]["text"] or "",
                          "image": image})
        except (KeyError, IndexError, TypeError, ValueError, LibrarianError, OSError):
            continue
    return sorted(notes, key=lambda n: (n["book"], n["page"] or 0, n["trace_id"]))


def publish(client: FeishuBase, root: Path, owner: str) -> dict:
    state = _load_state(root)
    app, table = state["app_token"], state["table_id"]
    rows = client.records(app, table)
    existing = {_text(row.get("fields", {}).get("Trace ID")): row for row in rows}
    by_id = {row["record_id"]: row for row in rows}
    bindings = state.setdefault("bindings", {})
    created, conflicted = 0, 0
    with Library(root) as lib:
        notes = pending_notes(lib, root, owner)
    for note in notes:
        binding = bindings.get(note["trace_id"])
        row = by_id.get(binding["record_id"]) if binding else existing.get(note["trace_id"])
        if row:
            if not binding:
                bindings[note["trace_id"]] = {"record_id": row["record_id"],
                                               "revision": note["revision"]}
                _save_state(root, state)
            if _text(row.get("fields", {}).get("处理状态")) == "已入库":
                continue
            fields = row.get("fields", {})
            revision = _text(fields.get("源修订"))
            if revision == str(note["revision"]) and _text(
                    fields.get("处理状态")) == "冲突" and _text(
                    fields.get("错误说明")) == "源记录已更新，请重新发布审核项":
                client.update_record(app, table, row["record_id"],
                                     {"处理状态": "待处理", "错误说明": ""})
            elif revision != str(note["revision"]) and _text(
                    fields.get("处理状态")) != "冲突":
                client.update_record(app, table, row["record_id"],
                                     {"处理状态": "冲突", "错误说明": "源记录已更新，请重新发布审核项"})
                conflicted += 1
            continue
        token = client.upload_crop(app, note["image"])
        record = client.create_record(app, table, {
            "条目": f"笔记 {len(rows) + created + 1:02d}", "Trace ID": note["trace_id"],
            "书名": note["book"], "页码": str(note["page"] or ""),
            "机器初稿": note["machine_text"], "核对文字": note["text"],
            "核对决定": "待核对", "处理状态": "待处理",
            "源修订": note["revision"], "原图局部": [{"file_token": token}],
        })
        if not record.get("record_id"):
            raise FeishuError(-1, "record creation returned no ID")
        bindings[note["trace_id"]] = {"record_id": record["record_id"],
                                       "revision": note["revision"]}
        _save_state(root, state)
        created += 1
    return {"created": created, "conflicted": conflicted, "pending": len(notes),
            "url": state.get("review_url") or state["url"]}


def collect_decisions(client: FeishuBase, root: Path, owner: str) -> dict:
    state = _load_state(root)
    app, table = state["app_token"], state["table_id"]
    binding_by_record = {item["record_id"]: (trace_id, item["revision"])
                         for trace_id, item in state.get("bindings", {}).items()}
    applied, failed, conflict = 0, 0, 0
    applied_records = []
    for row in client.records(app, table):
        fields = row.get("fields") or {}
        verdict = _text(fields.get("核对决定"))
        if verdict not in {"确认", "排除"}:
            continue
        if _text(fields.get("处理状态")) == "已入库":
            if _text(fields.get("Vault 同步")) != "已验证":
                applied_records.append({"record_id": row["record_id"],
                                        "book": _text(fields.get("书名"))})
            continue
        bound = binding_by_record.get(row["record_id"])
        if bound is None or _text(fields.get("Trace ID")) != bound[0] or \
                _text(fields.get("源修订")) != str(bound[1]):
            client.update_record(app, table, row["record_id"],
                                 {"处理状态": "冲突", "错误说明": "审核项标识与本地绑定不一致"})
            conflict += 1
            continue
        trace_id = bound[0]
        try:
            revision = bound[1]
            text = _text(fields.get("核对文字")).strip() if verdict == "确认" else ""
            with Library(root) as lib:
                result = review_handwriting(lib, owner, {
                    "trace_id": trace_id, "expected_revision": revision,
                    "decision": "accepted" if verdict == "确认" else "rejected",
                    "text": text})
            client.update_record(app, table, row["record_id"],
                                 {"处理状态": "已入库", "错误说明": "",
                                  "源修订": result["revision"],
                                  "Vault 同步": "待同步"})
            state["bindings"][trace_id]["revision"] = result["revision"]
            _save_state(root, state)
            applied += 1
            applied_records.append({"record_id": row["record_id"],
                                    "book": _text(fields.get("书名"))})
        except (LibrarianError, ValueError) as exc:
            status = "冲突" if isinstance(exc, LibrarianError) and exc.code == "REVISION_CONFLICT" else "失败"
            client.update_record(app, table, row["record_id"],
                                 {"处理状态": status, "错误说明": str(exc)[:400]})
            if status == "冲突":
                conflict += 1
            else:
                failed += 1
    return {"applied": applied, "failed": failed, "conflicted": conflict,
            "applied_records": applied_records}


def _verify_remote_notes(vault: Path, books: set[str]) -> bool:
    import boto3
    from botocore.config import Config

    encoded = json.loads((vault / ".obsidian/plugins/remotely-save/data.json").read_text())["d"]
    reversed_text = encoded[::-1]
    settings = json.loads(base64.b64decode(reversed_text + "=" * (-len(reversed_text) % 4)))
    s3 = settings["s3"]
    bucket = s3["s3BucketName"]
    prefix = (s3.get("s3PrefixPath") or "").strip("/")
    client = boto3.client("s3", endpoint_url=s3["s3Endpoint"],
                          region_name=s3["s3Region"],
                          aws_access_key_id=s3["s3AccessKeyID"],
                          aws_secret_access_key=s3["s3SecretAccessKey"],
                          config=Config(signature_version="s3v4",
                                        s3={"addressing_style": "virtual"}))
    for book in books:
        note = vault / "2Area" / "40 学习与阅读" / "阅读笔记" / f"{book}.md"
        relative = note.relative_to(vault).as_posix()
        key = f"{prefix}/{relative}" if prefix else relative
        remote = client.get_object(Bucket=bucket, Key=key)["Body"].read()
        if hashlib.sha256(remote).digest() != hashlib.sha256(note.read_bytes()).digest():
            return False
    return True


def _finish_vault(client: FeishuBase, state: dict, root: Path, vault: Path | None,
                  owner: str, applied_records: list[dict]) -> dict:
    if not applied_records:
        return {"vault_sync": "unchanged"}
    result = {"vault_sync": "failed"}
    try:
        if vault is None:
            raise RuntimeError("Vault path missing")
        from .worker import run as run_worker
        build_index(root, owner)
        worker = run_worker(root, vault, owner, physical_only=True)
        if any(item.get("status") in {"error", "review_required", "already_running"}
               for item in worker):
            raise RuntimeError("Vault export did not finish")
        sync = subprocess.run(
            [os.environ.get("PAP_OBSIDIAN_BIN", "obsidian"), "command",
             "id=remotely-save:start-sync"], capture_output=True, text=True,
            timeout=60, env=os.environ.copy())
        if sync.returncode:
            raise RuntimeError("Obsidian sync command failed")
        books = {item["book"] for item in applied_records if item["book"]}
        verified = False
        for attempt in range(4):
            try:
                verified = _verify_remote_notes(vault, books)
            except Exception:
                verified = False
            if verified:
                break
            if attempt < 3:
                time.sleep(5)
        if not verified:
            raise RuntimeError("Vault note differs from COS after sync")
        result["vault_sync"] = "verified"
    except Exception as exc:
        result["vault_error"] = str(exc)[:200]
    for item in applied_records:
        client.update_record(state["app_token"], state["table_id"],
                             item["record_id"],
                             {"Vault 同步": "已验证" if result["vault_sync"] == "verified"
                              else "同步失败"})
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["bootstrap", "publish", "poll", "sync"])
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--owner", required=True)
    parser.add_argument("--vault", type=Path)
    parser.add_argument("--credentials", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    credentials = json.loads(args.credentials.read_text(encoding="utf-8"))
    client = FeishuBase(credentials["app_id"], credentials["app_secret"])
    client.authenticate()
    if args.action == "bootstrap":
        result = bootstrap(client, root)
    elif args.action == "publish":
        result = publish(client, root, args.owner)
    else:
        published = publish(client, root, args.owner) if args.action == "sync" else None
        result = collect_decisions(client, root, args.owner)
        result.update(_finish_vault(client, _load_state(root), root, args.vault,
                                    args.owner, result.pop("applied_records")))
        if published is not None:
            result["published"] = published
    print(json.dumps(result, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
