import assert from 'node:assert/strict';
import test from 'node:test';
import { applyFloorUpdate, emptyFloorState, isFloorState, type FloorUpdate } from '@pap/floor-contract';
import { floorId, normalizeSessionRow } from '@pap/openclaw-adapter';

test('identity is per gateway, confirmed owner, and raw key', () => {
  const a = floorId('g1', 'a1', 'same');
  assert.equal(a, floorId('g1', 'a1', 'same'));
  assert.notEqual(a, floorId('g1', 'a2', 'same'));
  assert.notEqual(a, floorId('g2', 'a1', 'same'));
});

test('snapshot and patch preserve exact run null and empty semantics', () => {
  const row = { key: 'session:one', agentId: 'a1', sessionId: 'instance-1', kind: 'direct', status: 'running', activeRunIds: ['r1','r2'], hasActiveRun: true };
  const first = normalizeSessionRow(row, 'g1', 100);
  assert.equal(first.work.status, 'running');
  assert.deepEqual(first.work.activeRunIds, ['r1','r2']);
  const partial = normalizeSessionRow({ key: row.key, agentId: row.agentId, sessionId: row.sessionId }, 'g1', 200, {}, first, false);
  assert.deepEqual(partial.work.activeRunIds, ['r1','r2']);
  const cleared = normalizeSessionRow({ ...row, activeRunIds: null, hasActiveRun: false, status: 'done', lastRunId: 'r2' }, 'g1', 300);
  assert.equal(cleared.work.activeRunIds, null);
  assert.equal(cleared.work.status, 'completed');
  const newInstance = normalizeSessionRow({ key: row.key, agentId: row.agentId, sessionId: 'instance-2' }, 'g1', 400, {}, first, false);
  assert.equal(newInstance.work.activeRunIds, null);
  assert.equal(newInstance.work.status, 'unknown');
  let state = emptyFloorState('epoch', 100);
  state = applyFloorUpdate(state, { type: 'patch', schemaVersion: 1, epoch: 'epoch', baseRevision: 0, revision: 1, generatedAtMs: 100, upserts: [first], removeIds: [] });
  assert.ok(isFloorState(state));
  assert.equal(Object.keys(state.agents).length, 1);
  assert.throws(() => applyFloorUpdate(state, { type: 'patch', schemaVersion: 1, epoch: 'epoch', baseRevision: 0, revision: 2, generatedAtMs: 101, upserts: [], removeIds: [] }), /revision gap/);
});

test('activity and query timeouts never imply a run outcome', () => {
  const idle = normalizeSessionRow({ key: 'k', agentId: 'a', lastActivityAt: 1 }, 'g', 100000);
  assert.equal(idle.work.status, 'unknown');
  assert.equal(idle.work.latestOutcome, null);
  const running = normalizeSessionRow({ key: 'k', agentId: 'a', status: 'running', lastRunError: 'tool failed' }, 'g', 100);
  assert.equal(running.work.status, 'running');
  assert.equal(running.work.latestOutcome, null);
});

test('a failed row keeps the outcome but excludes unconstrained Gateway error text', () => {
  const failed = normalizeSessionRow({ key: 'k', agentId: 'a', sessionId: 's', status: 'failed',
    lastRunId: 'r', activeRunIds: [], hasActiveRun: false,
    lastRunError: 'private prompt and provider details' }, 'g', 100);
  assert.equal(failed.work.status, 'error');
  assert.deepEqual(failed.work.latestOutcome, { runId: 'r', result: 'error', endedAtMs: null, message: null });
  assert.equal(JSON.stringify(failed).includes('private prompt'), false);
});

test('runtime contract rejects extra nested data and conflicting patch IDs', () => {
  const agent = normalizeSessionRow({ key: 'k', agentId: 'a' }, 'g', 100);
  const state = { ...emptyFloorState('e', 100), agents: { [agent.id]: agent } };
  assert.equal(isFloorState(state), true);
  assert.equal(isFloorState({ ...state, secret: 'leaked' }), false);
  assert.equal(isFloorState({ ...state, agents: { [agent.id]: { ...agent, work: { ...agent.work, rawEvent: { prompt: 'private' } } } } }), false);
  assert.equal(isFloorState({ ...state, agents: { [agent.id]: { ...agent, work: { ...agent.work,
    tool: { name: '/private/source', callId: 'c', phase: 'start' } } } } }), false);
  assert.equal(isFloorState({ ...state, agents: { [agent.id]: { ...agent, progress: { revision: 1, updatedAtMs: 1, markdown: null, steps: [{ text: 'step', status: 'pending', hidden: 'raw' }] } } } }), false);
  assert.equal(isFloorState({ ...state, agents: { [agent.id]: { ...agent, progress: { revision: 1, updatedAtMs: 1, markdown: '中'.repeat(2731), steps: null } } } }), false);
  assert.equal(isFloorState({ ...state, agents: { [agent.id]: { ...agent, progress: { revision: 1, updatedAtMs: 1, markdown: null, steps: [{ text: '中'.repeat(171), status: 'pending' }] } } } }), false);
  const patch = { type: 'patch' as const, schemaVersion: 1 as const, epoch: 'e', baseRevision: 0,
    revision: 1, generatedAtMs: 101, upserts: [agent], removeIds: [] };
  assert.throws(() => applyFloorUpdate(state, { ...patch, rawEvent: 'private' } as FloorUpdate), /envelope/);
  assert.throws(() => applyFloorUpdate(state, { ...patch, upserts: [agent, agent] }), /conflicting/);
  assert.throws(() => applyFloorUpdate(state, { ...patch, removeIds: [agent.id] }), /conflicting/);
});

test('future display text is bounded and a summary requires its source', () => {
  const agent = normalizeSessionRow({ key: 'k', agentId: 'a' }, 'g', 100);
  const state = { ...emptyFloorState('e', 100), agents: { [agent.id]: agent } };
  const withAgent = (changed: typeof agent) => ({ ...state, agents: { [agent.id]: changed } });
  assert.equal(isFloorState(withAgent({ ...agent, work: { ...agent.work,
    summary: '正在读取文件', summarySource: 'tool' } })), true);
  assert.equal(isFloorState(withAgent({ ...agent, work: { ...agent.work,
    summary: '来源缺失' } })), false);
  assert.equal(isFloorState(withAgent({ ...agent, work: { ...agent.work,
    summary: '中'.repeat(171), summarySource: 'narration' } })), false);
  assert.equal(isFloorState(withAgent({ ...agent, lastMessagePreview: '中'.repeat(171) })), false);
  assert.equal(isFloorState(withAgent({ ...agent, work: { ...agent.work,
    attention: [{ id: 'q', kind: 'question', runId: null, blocking: true, label: '中'.repeat(86) }] } })), false);
});

test('handoffs must identify two visible sessions with bounded event evidence and lifetime', () => {
  const from = normalizeSessionRow({ key: 'from', agentId: 'a' }, 'g', 100);
  const to = normalizeSessionRow({ key: 'to', agentId: 'b' }, 'g', 100);
  const event = { id: 'handoff-1', fromId: from.id, toId: to.id, kind: 'request',
    observedAtMs: 100, expiresAtMs: 3100, evidenceReference: 'event:1' };
  const base = { ...emptyFloorState('e', 100), agents: { [from.id]: from, [to.id]: to }, handoffs: [event] };
  assert.equal(isFloorState(base), true);
  assert.equal(isFloorState({ ...base, handoffs: [event, event] }), false);
  assert.equal(isFloorState({ ...base, handoffs: [{ ...event, toId: 'not-visible' }] }), false);
  assert.equal(isFloorState({ ...base, handoffs: [{ ...event, expiresAtMs: 3101 }] }), false);
  assert.equal(isFloorState({ ...base, handoffs: [{ ...event, evidenceReference: '../private' }] }), false);
});

test('terminal status requires a run and current instance; exact empty activity wins over stale running status', () => {
  const noRun = normalizeSessionRow({ key: 'k', agentId: 'a', sessionId: 's', status: 'done', activeRunIds: [] }, 'g', 200);
  assert.equal(noRun.work.status, 'idle');
  assert.equal(noRun.work.latestOutcome, null);
  const noInstance = normalizeSessionRow({ key: 'k', agentId: 'a', status: 'failed', lastRunId: 'r' }, 'g', 200);
  assert.equal(noInstance.work.status, 'unknown');
  const empty = normalizeSessionRow({ key: 'k', agentId: 'a', sessionId: 's', status: 'running', hasActiveRun: false, activeRunIds: [] }, 'g', 200);
  assert.equal(empty.work.status, 'idle');
});
