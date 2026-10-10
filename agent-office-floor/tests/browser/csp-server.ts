import { createServer } from 'node:http';
import { createReadStream, existsSync, statSync } from 'node:fs';
import { extname, join, normalize } from 'node:path';
import { fileURLToPath } from 'node:url';
import { syntheticState } from '../../apps/web/src/synthetic.ts';
import type { FloorState } from '@pap/floor-contract';
import { contentPolicy } from '../../apps/server/src/http-policy.ts';
import { loginPage } from '../../apps/server/src/viewer-auth.ts';
import { readPapTasks } from '../../apps/server/src/pap-tasks.ts';
import { SseBatcher } from '../../apps/server/src/sse-batcher.ts';

const root = fileURLToPath(new URL('../../apps/web/dist/', import.meta.url));
const port = Number(process.env.PORT ?? 5190);
if (!Number.isInteger(port) || port < 1 || port > 65535) throw new Error('invalid PORT');
const handoffFixture = process.env.PAP_CSP_HANDOFF === '1';
const forbiddenInputFixture = process.env.PAP_CSP_BLOCKING_FORBIDDEN === '1';
const pollMutationFixture = process.env.PAP_CSP_POLL_MUTATION === '1';
const fixtureAgents = process.env.PAP_CSP_TOOL_LABEL === '1' ? {
  ...syntheticState.agents,
  'fixture-0': { ...syntheticState.agents['fixture-0'],
    work: { ...syntheticState.agents['fixture-0'].work,
      phase: 'reading' as const,
      tool: { name: 'read_file', callId: 'fixture-call', phase: 'start' as const } } }
} : process.env.PAP_CSP_SUMMARY_LABEL === '1' ? {
  ...syntheticState.agents,
  'fixture-0': { ...syntheticState.agents['fixture-0'],
    work: { ...syntheticState.agents['fixture-0'].work,
      summary: '正在整理已确认的资料', summarySource: 'narration' as const } }
} : syntheticState.agents;
const state = { ...syntheticState, agents: fixtureAgents,
  capabilities: { ...syntheticState.capabilities,
    ...(handoffFixture ? { handoff: 'partial' as const } : {}),
    ...(forbiddenInputFixture ? { blockingInput: 'forbidden' as const } : {}) },
  connection: { mode: 'subscription' as const, state: 'live' as const, lastConfirmedAtMs: Date.now(), reason: '办公室人物为合成测试数据' } };
let currentState: FloorState = state;
let pollMutations = 0;
const types: Record<string, string> = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.css': 'text/css; charset=utf-8', '.svg': 'image/svg+xml', '.tmj': 'application/json' };
const headers = { 'Cache-Control': 'no-store', 'Content-Security-Policy': contentPolicy, 'X-Content-Type-Options': 'nosniff' };
const resourceReads = new Map<string, number>();
let sseAttempts = 0;
const failSseCount = Number(process.env.PAP_CSP_SSE_FAIL_COUNT ?? 0);
if (!Number.isSafeInteger(failSseCount) || failSseCount < 0) throw new Error('invalid PAP_CSP_SSE_FAIL_COUNT');
let stateReads = 0;
const failStateCount = Number(process.env.PAP_CSP_STATE_FAIL_COUNT ?? 0);
if (!Number.isSafeInteger(failStateCount) || failStateCount < 0) throw new Error('invalid PAP_CSP_STATE_FAIL_COUNT');
const failStateAt = Number(process.env.PAP_CSP_STATE_FAIL_AT ?? 0);
if (!Number.isSafeInteger(failStateAt) || failStateAt < 0) throw new Error('invalid PAP_CSP_STATE_FAIL_AT');
const invalidPatchDelayMs = Number(process.env.PAP_CSP_INVALID_PATCH_DELAY_MS ?? 0);
if (!Number.isSafeInteger(invalidPatchDelayMs) || invalidPatchDelayMs < 0) throw new Error('invalid PAP_CSP_INVALID_PATCH_DELAY_MS');
const authExpireDelayMs = Number(process.env.PAP_CSP_AUTH_EXPIRE_DELAY_MS ?? 0);
if (!Number.isSafeInteger(authExpireDelayMs) || authExpireDelayMs < 0) throw new Error('invalid PAP_CSP_AUTH_EXPIRE_DELAY_MS');
const revokeDelayMs = Number(process.env.PAP_CSP_REVOKE_DELAY_MS ?? 0);
if (!Number.isSafeInteger(revokeDelayMs) || revokeDelayMs < 0) throw new Error('invalid PAP_CSP_REVOKE_DELAY_MS');
const patchIntervalMs = Number(process.env.PAP_CSP_PATCH_INTERVAL_MS ?? 0);
if (!Number.isSafeInteger(patchIntervalMs) || patchIntervalMs < 0 ||
    (patchIntervalMs > 0 && patchIntervalMs < 150)) throw new Error('invalid PAP_CSP_PATCH_INTERVAL_MS');
const patchCount = Number(process.env.PAP_CSP_PATCH_COUNT ?? 0);
if (!Number.isSafeInteger(patchCount) || patchCount < 0 || patchCount > 1000) throw new Error('invalid PAP_CSP_PATCH_COUNT');
const eventLatencyFixture = process.env.PAP_CSP_EVENT_LATENCY === '1';

createServer((req, res) => {
  if (req.method !== 'GET') { res.writeHead(405, headers).end(); return; }
  const path = new URL(req.url ?? '/', 'http://127.0.0.1').pathname;
  if (path === '/' && authExpireDelayMs > 0 && stateReads >= 2) {
    res.writeHead(200, { ...headers, 'Content-Type': 'text/html; charset=utf-8' }).end(loginPage);
    return;
  }
  if (path === '/test/requests') {
    res.writeHead(200, { ...headers, 'Content-Type': 'application/json' }).end(JSON.stringify({ ...Object.fromEntries(resourceReads), sseAttempts, stateReads }));
    return;
  }
  if (path === '/test/mutate' && pollMutationFixture) {
    const prior = currentState;
    const first = prior.agents['fixture-0'];
    if (!first) { res.writeHead(409, headers).end(); return; }
    pollMutations++;
    const mutatedAtMs = Date.now();
    const updated = { ...first, name: `测试专员 1 · 变更 ${pollMutations}` };
    currentState = { ...prior, revision: prior.revision + 1, generatedAtMs: mutatedAtMs,
      agents: { ...prior.agents, [updated.id]: updated } };
    res.writeHead(200, { ...headers, 'Content-Type': 'application/json' }).end(JSON.stringify({
      mutatedAtMs, revision: currentState.revision, count: pollMutations }));
    return;
  }
  if (path === '/theme/missing.tmj' || path === '/office/map.tmj')
    resourceReads.set(path, (resourceReads.get(path) ?? 0) + 1);
  if (path === '/office/map.tmj' && process.env.PAP_CSP_HIDE_OWNED_MAP === '1') {
    res.writeHead(404, headers).end(); return;
  }
  if (path === '/api/floor/state') {
    stateReads++;
    if (authExpireDelayMs > 0 && stateReads >= 2) { res.writeHead(401, headers).end(); return; }
    if (stateReads <= failStateCount || stateReads === failStateAt) { res.writeHead(503, headers).end(); return; }
    res.writeHead(200, { ...headers, 'Content-Type': 'application/json' }).end(JSON.stringify(currentState)); return;
  }
  if (path === '/api/pap/tasks') {
    void readPapTasks().then(json => { if (!res.writableEnded) res.writeHead(200,
      { ...headers, 'Content-Type': 'application/json' }).end(json); })
      .catch(() => { if (!res.writableEnded) res.writeHead(503, headers).end(); });
    return;
  }
  if (path === '/api/floor/events') {
    sseAttempts++;
    if (sseAttempts <= failSseCount) { res.writeHead(503, headers).end(); return; }
    res.writeHead(200, { ...headers, 'Content-Type': 'text/event-stream; charset=utf-8' });
    res.write(`event: floor\ndata: ${JSON.stringify({ type: 'snapshot', state: currentState })}\n\n`);
    const batcher = patchIntervalMs > 0 && patchCount > 0 ? new SseBatcher(update =>
      res.write(`event: floor\ndata: ${JSON.stringify(update)}\n\n`)) : null;
    let patchesSent = 0;
    const patches = batcher ? setInterval(() => {
      if (patchesSent >= patchCount) { clearInterval(patches!); return; }
      const prior = currentState;
      const first = prior.agents['fixture-0'];
      if (!first) { clearInterval(patches!); return; }
      patchesSent++;
      const updated = eventLatencyFixture ? { ...first, work: { ...first.work,
        tool: { name: `read_file_${patchesSent}`, callId: `fixture-call-${patchesSent}`, phase: 'start' as const },
        evidence: [...first.work.evidence.slice(-7), { source: 'tool_event' as const,
          reference: `fixture-run:${patchesSent}`, sourceAtMs: null, observedAtMs: Date.now() }] } } :
        { ...first, name: `测试专员 1 · ${patchesSent}` };
      const patch = { type: 'patch' as const, schemaVersion: 1 as const, epoch: prior.epoch,
        baseRevision: prior.revision, revision: prior.revision + 1, generatedAtMs: Date.now(),
        upserts: [updated], removeIds: [] };
      currentState = { ...prior, revision: patch.revision, generatedAtMs: patch.generatedAtMs,
        agents: { ...prior.agents, [updated.id]: updated } };
      batcher!.push(patch);
    }, patchIntervalMs) : null;
    const invalidPatch = invalidPatchDelayMs > 0 ? setTimeout(() => res.write('event: floor\ndata: {"type":"patch"}\n\n'), invalidPatchDelayMs) : null;
    const handoff = handoffFixture ? setTimeout(() => {
      const prior = currentState;
      const observedAtMs = Date.now();
      const event = { id: 'fixture-handoff-1', fromId: 'fixture-0', toId: 'fixture-1',
        kind: 'request' as const, observedAtMs, expiresAtMs: observedAtMs + 3000,
        evidenceReference: 'fixture:verified-communication' };
      const patch = { type: 'patch' as const, schemaVersion: 1 as const, epoch: prior.epoch,
        baseRevision: prior.revision, revision: prior.revision + 1, generatedAtMs: Date.now(),
        upserts: [], removeIds: [], handoffs: [event] };
      currentState = { ...prior, revision: patch.revision, generatedAtMs: patch.generatedAtMs,
        handoffs: [event] };
      res.write(`event: floor\ndata: ${JSON.stringify(patch)}\n\n`);
    }, 1800) : null;
    const expiry = authExpireDelayMs > 0 ? setTimeout(() => res.end(), authExpireDelayMs) : null;
    const revocation = revokeDelayMs > 0 && Object.keys(currentState.agents).length ? setTimeout(() => {
      const prior = currentState;
      const connection = { ...prior.connection, mode: 'none' as const, state: 'auth_required' as const,
        reason: '测试权限撤销' };
      const capabilities = { ...prior.capabilities, sessionList: 'forbidden' as const };
      const patch = { type: 'patch' as const, schemaVersion: 1 as const, epoch: prior.epoch,
        baseRevision: prior.revision, revision: prior.revision + 1, generatedAtMs: Date.now(),
        upserts: [], removeIds: Object.keys(prior.agents), connection, capabilities, handoffs: [] };
      currentState = { ...prior, revision: patch.revision, generatedAtMs: patch.generatedAtMs,
        agents: {}, handoffs: [], connection, capabilities };
      res.write(`event: floor\ndata: ${JSON.stringify(patch)}\n\n`);
    }, revokeDelayMs) : null;
    const heartbeat = setInterval(() => res.write('event: heartbeat\ndata: {}\n\n'), 15000);
    req.on('close', () => { clearInterval(heartbeat); if (patches) clearInterval(patches); batcher?.close();
      if (invalidPatch) clearTimeout(invalidPatch);
      if (handoff) clearTimeout(handoff);
      if (expiry) clearTimeout(expiry); if (revocation) clearTimeout(revocation); });
    return;
  }
  const file = normalize(join(root, path === '/' ? 'index.html' : path.slice(1)));
  if (!file.startsWith(root) || !existsSync(file) || !statSync(file).isFile()) { res.writeHead(404, headers).end(); return; }
  res.writeHead(200, { ...headers, 'Content-Type': types[extname(file)] ?? 'application/octet-stream' });
  createReadStream(file).pipe(res);
}).listen(port, '127.0.0.1', () => process.stdout.write(`Strict CSP fixture listening on ${port}\n`));
