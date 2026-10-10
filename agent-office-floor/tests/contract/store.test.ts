import assert from 'node:assert/strict';
import test from 'node:test';
import { applyFloorUpdate, type FloorState } from '@pap/floor-contract';
import { FloorStore, normalizeSessionRow } from '@pap/openclaw-adapter';

test('new SSE observers receive a baseline before later revisions', () => {
  const store = new FloorStore('known-epoch');
  const messages: ReturnType<typeof store.snapshot>[] = [];
  let client = null as ReturnType<typeof store.snapshot> | null;
  const off = store.observe(update => { client = applyFloorUpdate(client, update); messages.push(client); });
  const agent = normalizeSessionRow({ key: 'k', agentId: 'a', sessionId: 's', status: 'running' }, 'g', 100);
  store.replaceAgents([agent], true);
  store.setConnection({ mode: 'subscription', state: 'offline', lastConfirmedAtMs: 100, reason: 'lost' });
  assert.deepEqual(messages.map(s => s.revision), [0,1,2]);
  assert.equal(client!.agents[agent.id].freshness, 'stale');
  assert.equal(client!.agents[agent.id].work.status, 'running');
  off();
});

test('disconnect preserves stale business status but drops unconfirmed transient fields', () => {
  const store = new FloorStore('e');
  const row = normalizeSessionRow({ key: 'k', agentId: 'a', sessionId: 's', status: 'running',
    activeRunIds: ['r'], hasActiveRun: true }, 'g', 100);
  store.replaceAgents([{ ...row, work: { ...row.work, tool: { name: 'read', callId: 'c', phase: 'start' },
    attention: [{ id: 'q', kind: 'question', runId: 'r', blocking: true, label: 'Question' }],
    compacting: true, looping: true } }], true);
  store.setConnection({ mode: 'subscription', state: 'offline', lastConfirmedAtMs: 100, reason: 'lost' });
  const agent = store.snapshot().agents[row.id];
  assert.equal(agent.freshness, 'stale');
  assert.equal(agent.work.status, 'running');
  assert.equal(agent.work.activeRunIds, null);
  assert.equal(agent.work.hasActiveRun, null);
  assert.equal(agent.work.tool, null);
  assert.equal(agent.work.attention, null);
  assert.equal(agent.work.compacting, null);
  assert.equal(agent.work.looping, null);
});

test('incomplete scans preserve rows', () => {
  const store = new FloorStore('known-epoch');
  const agent = normalizeSessionRow({ key: 'k', agentId: 'a', status: 'queued' }, 'g', 100);
  store.replaceAgents([agent], true);
  store.replaceAgents([], false);
  assert.ok(store.snapshot().agents[agent.id]);
  store.replaceAgents([], true);
  assert.equal(store.snapshot().agents[agent.id], undefined);
});

test('sequence uncertainty marks data stale without fabricating a run failure', () => {
  const store = new FloorStore('known-epoch');
  const agent = normalizeSessionRow({ key: 'k', agentId: 'a', sessionId: 's', status: 'running',
    activeRunIds: ['r'], hasActiveRun: true }, 'g', 100);
  store.replaceAgents([agent], true);
  store.markStale();
  const changed = store.snapshot().agents[agent.id];
  assert.equal(changed.freshness, 'stale');
  assert.equal(changed.work.status, 'running');
  assert.equal(changed.work.latestOutcome, null);
  assert.equal(changed.work.activeRunIds, null);
  assert.equal(changed.work.hasActiveRun, null);
  assert.equal(changed.work.phase, null);
});

test('new adapter epoch sends a snapshot and clears transient certainty', () => {
  const store = new FloorStore('old');
  const agent = normalizeSessionRow({ key: 'k', agentId: 'a', sessionId: 's', status: 'running', activeRunIds: ['r'] }, 'g', 100);
  store.replaceAgents([agent], true);
  store.setProgress(agent.id, 's', { revision: 1, updatedAtMs: 100, markdown: 'private card', steps: null });
  let lastType = '';
  const off = store.observe(update => { lastType = update.type; });
  store.resetEpoch();
  assert.equal(lastType, 'snapshot');
  assert.notEqual(store.snapshot().epoch, 'old');
  assert.equal(store.snapshot().revision, 0);
  assert.equal(store.snapshot().agents[agent.id].freshness, 'stale');
  assert.equal(store.snapshot().agents[agent.id].work.phase, null);
  assert.equal(store.snapshot().agents[agent.id].work.activeRunIds, null);
  assert.equal(store.snapshot().agents[agent.id].progress, null);
  off();
});

test('read permission revocation removes rows and transient effects from browser state', () => {
  const store = new FloorStore('e');
  const agent = normalizeSessionRow({ key: 'k', agentId: 'a' }, 'g', 100);
  let browser = null as ReturnType<typeof store.snapshot> | null;
  const off = store.observe(update => { browser = applyFloorUpdate(browser, update); });
  store.replaceAgents([agent], true);
  store.revokeAccess('revoked');
  assert.deepEqual(Object.keys(store.snapshot().agents), []);
  assert.deepEqual(Object.keys(browser!.agents), []);
  assert.deepEqual(browser!.handoffs, []);
  assert.equal(browser!.connection.state, 'auth_required');
  assert.equal(browser!.capabilities.sessionList, 'forbidden');
  off();
});

test('connection uncertainty or endpoint loss removes transient handoffs from browser state', () => {
  for (const transition of ['offline', 'degraded', 'gap', 'new-epoch', 'endpoint-stale', 'endpoint-removed'] as const) {
    const store = new FloorStore('e');
    const from = normalizeSessionRow({ key: 'from', agentId: 'a', sessionId: 's1' }, 'g', 100);
    const to = normalizeSessionRow({ key: 'to', agentId: 'a', sessionId: 's2' }, 'g', 100);
    store.replaceAgents([from, to], true);
    const now = Date.now();
    const handoff = { id: 'confirmed-communication', fromId: from.id, toId: to.id,
      kind: 'request' as const, observedAtMs: now, expiresAtMs: now + 2500,
      evidenceReference: 'event:confirmed' };
    (store as unknown as { state: FloorState }).state = { ...store.snapshot(), handoffs: [handoff] };
    let browser: FloorState | null = null;
    const off = store.observe(update => { browser = applyFloorUpdate(browser, update); });
    assert.equal(browser!.handoffs.length, 1);
    if (transition === 'offline') store.setConnection({ mode: 'subscription', state: 'offline',
      lastConfirmedAtMs: now, reason: 'lost' });
    else if (transition === 'degraded') store.setConnection({ mode: 'subscription', state: 'degraded',
      lastConfirmedAtMs: now, reason: 'uncertain' });
    else if (transition === 'gap') store.markStale();
    else if (transition === 'new-epoch') store.resetEpoch();
    else if (transition === 'endpoint-stale') store.markAgentStale(from.id);
    else store.replaceAgents([from], true);
    assert.deepEqual(store.snapshot().handoffs, [], transition);
    assert.deepEqual(browser!.handoffs, [], transition);
    off();
  }
});
