#!/usr/bin/env python3
"""Add specific prompts and pin the first blocked action in a voice turn."""
import argparse
import hashlib
from pathlib import Path
import shutil
import subprocess

NAME = 'agent-tools.before-tool-call-iy-Keqfw.mjs'
BASE = '530f268db318327dd80dd46aac439e0948ef841e5cd13b660cc71e6f0241253d'
p = argparse.ArgumentParser()
p.add_argument('action', choices=['apply', 'rollback', 'status'])
p.add_argument('--dist', required=True, type=Path)
a = p.parse_args()
target = a.dist / NAME
backup = target.with_suffix('.before-specific-confirmation')
s = target.read_text()
marker = 'A voice turn keeps its first blocked action'
if a.action == 'status':
    print('specific-confirmation' if marker in s else 'base'); raise SystemExit
if a.action == 'rollback':
    if not backup.exists(): raise SystemExit('No backup available')
    shutil.copy2(backup, target); print('Restored base confirmation policy'); raise SystemExit
if marker in s:
    print('Already applied'); raise SystemExit
if hashlib.sha256(target.read_bytes()).hexdigest() != BASE:
    raise SystemExit('Unknown host build; refusing to patch')
def replace(old, new):
    global s
    if s.count(old) != 1: raise SystemExit('Anchor mismatch: ' + old[:80])
    s = s.replace(old, new)
replace('''	const pending = state.pending;
	const existing = pending?.fingerprint === fingerprint ? pending : void 0;''', '''	const pending = state.pending;
	// A voice turn keeps its first blocked action until the user can answer.
	// Alternate tools must not silently replace the challenge just presented.
	const priorObservation = params.runId ? state.observationsByRun.get(params.runId) : void 0;
	if (pending && pending.fingerprint !== fingerprint && priorObservation?.has(pending.fingerprint)) return {
		allowed: false,
		reason: `VOICE_CONFIRMATION_REQUIRED:${pending.confirmationId} The first pending action is still awaiting confirmation. STOP this turn. Do not replace it with another command, background task, scheduler, or tool. Ask the user to confirm or cancel the original action.`
	};
	const existing = pending?.fingerprint === fingerprint ? pending : void 0;''')
replace('''	state.pending = confirmation;
	const observation''', '''	const title = typeof params.toolParams?.title === "string" ? params.toolParams.title.replace(/[\\r\\n\\t]/g, " ").slice(0, 120) : "";
	const command = typeof params.toolParams?.command === "string" ? params.toolParams.command : "";
	const minutesSearch = params.toolName === "exec" && /^lark-cli minutes \\+search\\s/.test(command);
	const startDate = minutesSearch ? /--start\\s+(\\d{4}-\\d{2}-\\d{2})\\b/.exec(command)?.[1] : void 0;
	confirmation.actionLabel = minutesSearch ? `查询飞书妙记${startDate ? `（起始日期 ${startDate}）` : ""}` : title || params.toolName;
	state.pending = confirmation;
	const observation''')
replace('''const speech = "One pending action has not run. Say \\"yes\\" or \\"确认\\" to confirm that action, or \\"no\\" or \\"取消\\" to cancel it.";'''.replace('\\"','\\"'), '''const speech = `待确认：${pending.actionLabel ?? pending.blockedCall?.toolName ?? "所请求的操作"}。这项操作尚未执行。请说“确认”仅批准这项操作，或说“取消”。`;''')
# Add only an exact action-reference suffix; conditionals and altered commands
# still fail the whole-utterance match and the host keeps its one-shot grant.
replace('''\\s*)+(?:(?:不用再问了|不用再問了)''', '''\\s*)+(?:这项操作|這項操作|该操作|当前操作)?(?:(?:不用再问了|不用再問了)''')
replace('Ask for confirmation in the user\'s language: English yes/confirm', 'STOP this turn and return the confirmation request. Do not try alternate tools. Ask for confirmation in the user\'s language: English yes/confirm')
candidate = target.with_suffix('.specific-confirmation-candidate.mjs')
candidate.write_text(s)
try:
    subprocess.run(['node','--check',str(candidate)],check=True,capture_output=True)
    if not backup.exists(): shutil.copy2(target,backup)
    candidate.replace(target)
finally:
    candidate.unlink(missing_ok=True)
print('Specific confirmation prompts installed; restart Gateway to activate.')
