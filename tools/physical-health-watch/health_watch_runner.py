#!/usr/bin/env python3
"""Run the physical health checker without an OpenClaw scheduler.

The checker is deliberately the cheap path.  The LLM is contacted only when
the checker reports a non-OK severity; in that case the last five checker
results are supplied for trend analysis and the resulting advice is delivered
through the OpenClaw message CLI.
"""
from __future__ import annotations

import fcntl
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

CHECKER = Path("/home/xingzeng/.hermes/profiles/feishu3/skills/physical-health-watch/bin/physical-health-check.py")
STATE_DIR = Path(os.path.expanduser("~/.cache/hermes-physical-health"))
HISTORY = STATE_DIR / "recent-results.jsonl"
LOCK = STATE_DIR / "runner.lock"
ENV_FILE = Path("/home/xingzeng/.hermes/.env")
OPENCLAW = "/home/xingzeng/.local/bin/openclaw"
MODEL = "deepseek-v4.1-flash-expires-on-0910"
TARGET = "user:ou_0352bbdc9ad22d85aed7fc1355ba5346"
ANALYSIS_STATE = STATE_DIR / "analysis-state.json"
ANALYSIS_COOLDOWN_SECONDS = 30 * 60


def load_api_key() -> str:
    value = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if value:
        return value
    try:
        for line in ENV_FILE.read_text().splitlines():
            match = re.match(r"^DEEPSEEK_API_KEY=(.*)$", line)
            if match:
                value = match.group(1).strip().strip("'\"")
                if value:
                    return value
    except OSError:
        pass
    raise RuntimeError("DEEPSEEK_API_KEY is not available")


def run_checker() -> dict:
    completed = subprocess.run(
        [sys.executable, str(CHECKER), "--json"],
        capture_output=True,
        text=True,
        timeout=45,
        check=False,
    )
    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"checker returned invalid JSON: {exc}; stderr={completed.stderr[-500:]}") from exc
    result["runner_timestamp"] = int(time.time())
    result["checker_exit_code"] = completed.returncode
    return result


def append_history(result: dict) -> list[dict]:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with HISTORY.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(result, ensure_ascii=False, separators=(",", ":")) + "\n")
    rows: list[dict] = []
    try:
        for line in HISTORY.read_text(encoding="utf-8").splitlines()[-5:]:
            rows.append(json.loads(line))
    except (OSError, json.JSONDecodeError):
        pass
    return rows


def analysis_fingerprint(result: dict) -> str:
    codes = sorted(str(issue.get("code", "")) for issue in result.get("issues", []))
    return json.dumps({"severity": result.get("severity"), "codes": codes}, sort_keys=True)


def analysis_is_due(result: dict) -> bool:
    fingerprint = analysis_fingerprint(result)
    try:
        state = json.loads(ANALYSIS_STATE.read_text(encoding="utf-8"))
        return state.get("fingerprint") != fingerprint or int(time.time()) - int(state.get("timestamp", 0)) >= ANALYSIS_COOLDOWN_SECONDS
    except (OSError, ValueError, TypeError):
        return True


def mark_analysis(result: dict) -> None:
    ANALYSIS_STATE.write_text(json.dumps({"fingerprint": analysis_fingerprint(result), "timestamp": int(time.time())}), encoding="utf-8")


def ask_llm(history: list[dict]) -> str:
    prompt = {
        "role": "user",
        "content": (
            "你是机器健康监控分析器。下面是最近五次确定性脚本检查结果，按时间升序排列。"
            "只根据这些结果分析趋势，不要臆测未提供的数据。判断是否需要询问用户采取操作。"
            "如果需要，给出安全、具体的建议（例如先检查/结束哪个 PID，或应补充哪条只读诊断）；"
            "不要自动执行任何操作。请用简体中文，严格按以下四行输出：\n"
            "需要用户操作：是/否\n严重性：ok/warning/critical/error\n"
            "依据：不超过两句\n建议：不需要操作时写“无需操作”；需要时给出一条建议。\n\n"
            + json.dumps(history, ensure_ascii=False, indent=2)
        ),
    }
    body = json.dumps({
        "model": MODEL,
        "messages": [
            {"role": "system", "content": "你输出简短、可执行、保守的健康告警分析。"},
            prompt,
        ],
        "temperature": 0.1,
        "max_tokens": 700,
    }).encode()
    request = urllib.request.Request(
        "https://api.deepseek.com/chat/completions",
        data=body,
        method="POST",
        headers={"Authorization": f"Bearer {load_api_key()}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=90) as response:
        payload = json.loads(response.read().decode())
    return str(payload["choices"][0]["message"]["content"]).strip()


def deliver(message: str) -> None:
    subprocess.run(
        [OPENCLAW, "message", "send", "--channel", "feishu", "--account", "feishu3",
         "--target", TARGET, "--message", message, "--json"],
        check=True,
        timeout=45,
        stdout=subprocess.DEVNULL,
    )


def needs_user_action(analysis: str) -> bool:
    match = re.search(r"需要用户操作\s*：\s*(是|否)", analysis)
    if match:
        return match.group(1) == "是"
    # An unstructured analyst response is not permission to interrupt the user.
    return False


def main() -> int:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with LOCK.open("w") as lock:
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return 0
        result = run_checker()
        history = append_history(result)
        severity = result.get("severity", "error")
        # This is the important cost gate: healthy runs never call the LLM.
        if severity == "ok":
            return 0
        # Keep a persistent breach from generating an LLM call every five minutes;
        # all five-minute samples are still retained for the next analysis.
        if not analysis_is_due(result):
            return 0
        try:
            analysis = ask_llm(history)
        except Exception as exc:
            # A threshold breach with an unavailable analyst is itself actionable.
            analysis = f"需要用户操作：是\n严重性：error\n依据：LLM 分析失败（{exc}）\n建议：查看最近五次脚本结果并进行只读诊断。"
        if needs_user_action(analysis):
            message = "🖥️ Workstation health analysis\n" + analysis
            deliver(message)
        mark_analysis(result)
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
