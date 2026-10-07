#!/usr/bin/env python3
"""Daily local-only incremental export from the verified WeChat snapshot source."""
from __future__ import annotations

import base64
import csv
import fcntl
import hashlib
import json
import os
import sqlite3
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path

ROOT = Path(os.environ.get("PAP_ROOT", str(Path(__file__).resolve().parents[3])))
STATE = Path(os.environ.get("PAP_AGENT_STATE_DIR", str(ROOT / "var" / "wechat-archivist")))
DBROOT = Path(os.environ.get("WECHAT_DBROOT", ""))
KEYS = Path(os.environ.get("WECHAT_KEYS", ""))
TOOL = ROOT / "agents" / "wechat-archivist" / "runtime" / "wcdb_key_tool.py"
MSG_ARCHIVE = STATE / "messages.jsonl"
CHECKPOINT = STATE / "checkpoint.json"
RUNLOG = STATE / "run-log.jsonl"


def now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def append_log(event: dict) -> None:
    with RUNLOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")
        f.flush()
        os.fsync(f.fileno())


def main() -> int:
    if not os.environ.get("WECHAT_DBROOT") or not os.environ.get("WECHAT_KEYS"):
        raise RuntimeError("Set WECHAT_DBROOT and WECHAT_KEYS to local WeChat export paths")
    STATE.mkdir(mode=0o700, parents=True, exist_ok=True)
    lock_path = STATE / ".lock"
    with lock_path.open("a+") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        started = now()
        try:
            checkpoint = json.loads(CHECKPOINT.read_text(encoding="utf-8")) if CHECKPOINT.exists() else {}
            with tempfile.TemporaryDirectory(prefix="wechat-incremental-", dir=STATE) as tmp:
                subprocess.run([
                    "python3", str(TOOL), "decrypt", "--db-dir", str(DBROOT),
                    "--keys", str(KEYS), "--output", tmp,
                ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
                db = Path(tmp) / "message" / "message_0.db"
                con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
                con.row_factory = sqlite3.Row
                try:
                    names = {hashlib.md5(r[0].encode()).hexdigest(): r[0] for r in con.execute("SELECT user_name FROM Name2Id")}
                    senders = {r["rowid"]: r["user_name"] for r in con.execute("SELECT rowid,user_name FROM Name2Id")}
                    new_rows = []
                    for (table,) in con.execute("SELECT name FROM sqlite_schema WHERE type='table' AND name GLOB 'Msg_*' ORDER BY name"):
                        conversation = names.get(table[4:], f"unmapped:{table}")
                        last = int(checkpoint.get(table, 0))
                        for row in con.execute(f'SELECT * FROM "{table}" WHERE local_id > ? ORDER BY local_id', (last,)):
                            record = dict(row)
                            record.update({"conversation_id": conversation, "table": table, "sender_id": senders.get(record.get("real_sender_id")), "captured_at": now()})
                            for key, value in list(record.items()):
                                if isinstance(value, bytes):
                                    record[key] = {"encoding": "base64", "data": base64.b64encode(value).decode("ascii")}
                            new_rows.append(record)
                    with MSG_ARCHIVE.open("a", encoding="utf-8") as archive:
                        for record in new_rows:
                            archive.write(json.dumps(record, ensure_ascii=False) + "\n")
                        archive.flush()
                        os.fsync(archive.fileno())
                    for table in [r[0] for r in con.execute("SELECT name FROM sqlite_schema WHERE type='table' AND name GLOB 'Msg_*'")]:
                        value = con.execute(f'SELECT COALESCE(MAX(local_id),0) FROM "{table}"').fetchone()[0]
                        checkpoint[table] = int(value)
                finally:
                    con.close()
            tmp_checkpoint = CHECKPOINT.with_suffix(".tmp")
            tmp_checkpoint.write_text(json.dumps(checkpoint, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            os.replace(tmp_checkpoint, CHECKPOINT)
            append_log({"at": now(), "started_at": started, "status": "success", "new_rows": len(new_rows)})
            return 0
        except Exception as exc:
            append_log({"at": now(), "started_at": started, "status": "failed", "error": str(exc)[:500]})
            return 1


if __name__ == "__main__":
    raise SystemExit(main())
