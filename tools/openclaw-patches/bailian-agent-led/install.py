#!/usr/bin/env python3
"""Install a guarded, reversible adapter into a locally installed plugin."""
import argparse
import hashlib
import pathlib
import shutil
import subprocess

ORIGINAL = '83bb2a2b7da44305379087e6161deea5fe62e87528eaafeee24a5403dee3dca3'
parser = argparse.ArgumentParser()
parser.add_argument('action', choices=['apply', 'rollback', 'status'])
parser.add_argument('--plugin-dir', required=True, type=pathlib.Path)
args = parser.parse_args()
p = args.plugin_dir / 'bridge.js'
backup = args.plugin_dir / 'bridge.js.before-agent-led'
helper = args.plugin_dir / 'agent-led.mjs'
source = p.read_text()
marked = "import { createAgentLedController } from './agent-led.mjs';" in source
if args.action == 'status':
    print('agent-led' if marked else 'original'); raise SystemExit
if args.action == 'rollback':
    if not backup.exists(): raise SystemExit('No backup available')
    shutil.copy2(backup, p)
    print('Restored bridge; reload plugin to activate.'); raise SystemExit
if marked:
    raise SystemExit('Already patched; inspect before replacing an active adapter')
if hashlib.sha256(p.read_bytes()).hexdigest() != ORIGINAL:
    raise SystemExit('Unknown bridge build; refusing to patch')
def replace(old, new):
    global source
    if source.count(old) != 1: raise SystemExit('Adapter anchor mismatch: ' + old[:80])
    source = source.replace(old, new)
replace('import fs from "node:fs";', 'import fs from "node:fs";\nimport { createAgentLedController } from \'./agent-led.mjs\';')
replace('  const onServerEvent = (m) => {', '  const agentLed = createAgentLedController(req, sendJson);\n\n  const onServerEvent = (m) => {\n    if (agentLed.event(m)) return;')
replace('      supportsToolCalls: true,', '      supportsToolCalls: true,\n      handlesAgentConsult: true,')
replace('    isConfigured: (ctx) => Boolean(readApiKey(pluginConfig, ctx && ctx.providerConfig)),', '    isConfigured: (ctx) => Boolean(readApiKey(pluginConfig, ctx && ctx.providerConfig)),\n    isConfiguredAsync: async (ctx) => Boolean(readApiKey(pluginConfig, ctx && ctx.providerConfig)),')
replace('      case "session.created":', '      case "session.updated":')
replace('instructions: (req && req.instructions) || "你是一个简洁的语音助手。",', 'instructions: "你是朗读器。只逐字朗读用户提供的文本，不要回答问题，不得补充、解释、总结、改写或调用工具。",')
replace('silence_duration_ms: 700', 'silence_duration_ms: 1600')
replace('          const tools = (req && req.tools) || [];', '          const tools = []; // Agent-led: do not expose workflow decisions to voice model.')
replace('m.type === "session.created"', 'm.type === "session.updated"')
replace('closed before session.created', 'closed before session.updated')
start = source.index('    sendUserMessage(text) {')
end = source.index('    acknowledgeMark() {},', start)
source = source[:start] + '''    sendUserMessage(text) {
      return agentLed.speak(String(text));
    },
    triggerGreeting() {},
    submitToolResult(callId, result, options) {
      return agentLed.submit(callId, result, options);
    },
    handleBargeIn() { agentLed.cancel(); },
''' + source[end:]
replace('    close() {\n      if (closed) return;', '    close() {\n      agentLed.close();\n      if (closed) return;')
candidate = args.plugin_dir / 'bridge.agent-led-candidate.mjs'
candidate.write_text(source)
try:
    subprocess.run(['node', '--check', str(candidate)], check=True, capture_output=True)
    if not backup.exists(): shutil.copy2(p, backup)
    shutil.copy2(pathlib.Path(__file__).with_name('agent-led.mjs'), helper)
    candidate.replace(p)
finally:
    candidate.unlink(missing_ok=True)
print('Installed agent-led adapter; original bridge backed up. Reload plugin to activate.')
