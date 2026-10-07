import assert from 'node:assert/strict';
import test from 'node:test';
import { applyFloorUpdate, type FloorState, type FloorUpdate } from '@pap/floor-contract';
import { FloorStore, normalizeSessionRow } from '@pap/openclaw-adapter';
import { SseBatcher } from '../../apps/server/src/sse-batcher.ts';

function replay(updates: FloorUpdate[]): FloorState {
  let state: FloorState | null = null;
  for (const update of updates) state = applyFloorUpdate(state, update);
  assert.ok(state);
  return state;
}

test('burst patches preserve the final state and initial snapshot is immediate', () => {
  const store = new FloorStore('e');
  const raw: FloorUpdate[] = [];
  const delivered: FloorUpdate[] = [];
  const batcher = new SseBatcher(update => delivered.push(update));
  const off = store.observe(update => { raw.push(update); batcher.push(update); });
  assert.equal(delivered.length, 1);
  const agent = normalizeSessionRow({ key: 'k', agentId: 'a', sessionId: 's', status: 'running' }, 'g', 100);
  store.replaceAgents([agent], true);
  store.setCapability('sessionList', 'available');
  store.setConnection({ mode: 'subscription', state: 'live', lastConfirmedAtMs: 100, reason: null });
  assert.equal(delivered.length, 1);
  batcher.flush();
  assert.equal(delivered.length, 2);
  assert.deepEqual(replay(delivered), replay(raw));
  off(); batcher.close();
});

test('authorization revocation bypasses the batch timer and removes rows', () => {
  const store = new FloorStore('e');
  const delivered: FloorUpdate[] = [];
  const batcher = new SseBatcher(update => delivered.push(update));
  const off = store.observe(update => batcher.push(update));
  const agent = normalizeSessionRow({ key: 'k', agentId: 'a', sessionId: 's' }, 'g', 100);
  store.replaceAgents([agent], true);
  store.revokeAccess('revoked');
  assert.equal(delivered.length, 2);
  assert.equal(delivered[1].type, 'patch');
  if (delivered[1].type === 'patch') assert.deepEqual(delivered[1].upserts, []);
  assert.equal(replay(delivered).connection.state, 'auth_required');
  assert.deepEqual(Object.keys(replay(delivered).agents), []);
  off(); batcher.close();
});

test('a run terminal is sent immediately after any queued ordinary update', () => {
  const store = new FloorStore('e');
  const delivered: FloorUpdate[] = [];
  const batcher = new SseBatcher(update => delivered.push(update));
  const off = store.observe(update => batcher.push(update));
  const agent = normalizeSessionRow({ key: 'k', agentId: 'a', sessionId: 's',
    status: 'running', activeRunIds: ['r'], hasActiveRun: true }, 'g', 100);
  store.replaceAgents([agent], true);
  assert.equal(delivered.length, 1);
  assert.equal(store.setRunTerminal(agent.id, 's', 'r',
    { runId: 'r', result: 'success', endedAtMs: 101, message: null }, 2, 101), true);
  assert.equal(delivered.length, 2);
  assert.equal(replay(delivered).agents[agent.id].work.status, 'completed');
  off(); batcher.close();
});

test('loss of state certainty bypasses queued ordinary updates', () => {
  const store = new FloorStore('e');
  const delivered: FloorUpdate[] = [];
  const batcher = new SseBatcher(update => delivered.push(update));
  const off = store.observe(update => batcher.push(update));
  const agent = normalizeSessionRow({ key: 'k', agentId: 'a', sessionId: 's',
    status: 'running', activeRunIds: ['r'], hasActiveRun: true }, 'g', 100);
  store.replaceAgents([agent], true);
  assert.equal(delivered.length, 1);
  store.markStale();
  assert.equal(delivered.length, 2);
  assert.equal(replay(delivered).agents[agent.id].freshness, 'stale');
  assert.equal(replay(delivered).agents[agent.id].work.activeRunIds, null);
  store.setConnection({ mode: 'subscription', state: 'degraded', lastConfirmedAtMs: 100,
    reason: 'event gap' });
  assert.equal(delivered.length, 3);
  assert.equal(replay(delivered).connection.state, 'degraded');
  off(); batcher.close();
});

test('a new epoch snapshot supersedes queued old patches', () => {
  const store = new FloorStore('old');
  const delivered: FloorUpdate[] = [];
  const batcher = new SseBatcher(update => delivered.push(update));
  const off = store.observe(update => batcher.push(update));
  store.setCapability('sessionList', 'available');
  store.resetEpoch();
  assert.equal(delivered.length, 2);
  assert.equal(delivered[1].type, 'snapshot');
  assert.deepEqual(replay(delivered), store.snapshot());
  off(); batcher.close();
});
