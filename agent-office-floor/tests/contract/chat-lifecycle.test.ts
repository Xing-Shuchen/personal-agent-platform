import assert from 'node:assert/strict';
import test from 'node:test';
import { chatReceipt, chatTerminal } from '../../packages/openclaw-adapter/src/connection/chat-lifecycle.ts';
import { GatewayObserver } from '../../packages/openclaw-adapter/src/connection/observer.ts';
import { normalizeSessionRow } from '../../packages/openclaw-adapter/src/normalization/session.ts';
import { FloorStore } from '../../packages/openclaw-adapter/src/sessions/floor-store.ts';

test('pinned chat lifecycle semantics distinguish success, timeout, cancellation and yield without text', () => {
  const base = { runId: 'r', sessionKey: 'k', agentId: 'a', seq: 3 };
  const receipt = chatReceipt({ ...base, state: 'final', message: { secret: 'private' }, deltaText: 'private' });
  assert.ok(receipt);
  assert.equal(JSON.stringify(receipt).includes('private'), false);
  assert.deepEqual(chatTerminal(receipt, 100), { runId: 'r', result: 'success', endedAtMs: 100, message: null });
  assert.deepEqual(chatTerminal(chatReceipt({ ...base, state: 'error', errorKind: 'timeout', errorMessage: 'private' })!, 100),
    { runId: 'r', result: 'timeout', endedAtMs: 100, message: null });
  assert.deepEqual(chatTerminal(chatReceipt({ ...base, state: 'aborted' })!, 100),
    { runId: 'r', result: 'cancelled', endedAtMs: 100, message: null });
  assert.equal(chatTerminal(chatReceipt({ ...base, state: 'final', yielded: true, stopReason: 'end_turn' })!, 100), 'yielded');
  assert.equal(chatReceipt({ ...base, seq: -1, state: 'final' }), null);
});

test('verified chat terminals remove only their run and do not project raw messages', () => {
  const store = new FloorStore('fixture');
  const agent = normalizeSessionRow({ key: 'k', agentId: 'a', sessionId: 's1', status: 'running',
    activeRunIds: ['r1','r2'], hasActiveRun: true }, 'g', 100);
  store.replaceAgents([agent], true);
  const observer = new GatewayObserver({ gatewayId: 'g', gatewayUrl: 'ws://127.0.0.1:1', selectedAgentIds: ['a'] }, store);
  const admit = (payload: unknown) => (observer as unknown as { observeChatLifecycle(v: unknown): void }).observeChatLifecycle(payload);
  admit({ runId: 'r1', sessionKey: 'k', agentId: 'a', seq: 0, state: 'delta', deltaText: 'private' });
  assert.equal((observer as unknown as { invalidatedAt: number | null }).invalidatedAt, null);
  admit({ runId: 'r1', sessionKey: 'k', agentId: 'a', seq: 1, state: 'final', message: { secret: 'private' } });
  let current = store.snapshot().agents[agent.id];
  assert.deepEqual(current.work.activeRunIds, ['r2']);
  assert.equal(current.work.status, 'running');
  assert.equal(current.work.latestOutcome?.result, 'success');
  assert.equal(JSON.stringify(store.snapshot()).includes('private'), false);
  admit({ runId: 'r2', sessionKey: 'k', agentId: 'a', seq: 0, state: 'error', errorKind: 'timeout' });
  current = store.snapshot().agents[agent.id];
  assert.deepEqual(current.work.activeRunIds, []);
  assert.equal(current.work.status, 'error');
  assert.equal(current.work.latestOutcome?.result, 'timeout');
});

test('chat gaps and reused run IDs cannot produce a fresh terminal for a replacement session', () => {
  const store = new FloorStore('fixture');
  const row = (sessionId: string) => normalizeSessionRow({ key: 'k', agentId: 'a', sessionId,
    status: 'running', activeRunIds: ['r'], hasActiveRun: true }, 'g', 100);
  store.replaceAgents([row('s1')], true);
  const observer = new GatewayObserver({ gatewayId: 'g', gatewayUrl: 'ws://127.0.0.1:1', selectedAgentIds: ['a'] }, store);
  const admit = (payload: unknown) => (observer as unknown as { observeChatLifecycle(v: unknown): void }).observeChatLifecycle(payload);
  const base = { runId: 'r', sessionKey: 'k', agentId: 'a' };
  admit({ ...base, seq: 1, state: 'delta' });
  admit({ ...base, seq: 3, state: 'final' });
  assert.equal(store.snapshot().agents[row('s1').id].freshness, 'stale');
  store.replaceAgents([row('s2')], true);
  admit({ ...base, seq: 4, state: 'final' });
  const current = store.snapshot().agents[row('s2').id];
  assert.equal(current.session.sessionId, 's2');
  assert.equal(current.work.latestOutcome, null);
  assert.equal(current.freshness, 'stale');
});

test('a start event for a known key cannot claim an unconfirmed run or reused instance', () => {
  const store = new FloorStore('fixture');
  const idle = normalizeSessionRow({ key: 'k', agentId: 'a', sessionId: 's2',
    status: 'idle', activeRunIds: [], hasActiveRun: false }, 'g', 100);
  store.replaceAgents([idle], true);
  const observer = new GatewayObserver({ gatewayId: 'g', gatewayUrl: 'ws://127.0.0.1:1', selectedAgentIds: ['a'] }, store);
  const internal = observer as unknown as {
    observeChatLifecycle(value: unknown): void;
    unmatchedRuns: Map<string, string>;
  };
  internal.observeChatLifecycle({ runId: 'r-old', sessionKey: 'k', agentId: 'a', seq: 0,
    state: 'status', phase: 'starting_model' });
  assert.equal(store.snapshot().agents[idle.id].work.status, 'idle');
  assert.deepEqual(store.snapshot().agents[idle.id].work.activeRunIds, []);
  assert.equal(internal.unmatchedRuns.get('r-old'), 'seen');
  observer.stop();
});

test('a list read started before a terminal cannot restore the ended run', async () => {
  const store = new FloorStore('fixture');
  const base = { key: 'k', agentId: 'a', sessionId: 's', status: 'running',
    activeRunIds: ['r'], hasActiveRun: true, snapshotAt: 100 };
  const agent = normalizeSessionRow(base, 'g', 100);
  store.replaceAgents([agent], true);
  const observer = new GatewayObserver({ gatewayId: 'g', gatewayUrl: 'ws://127.0.0.1:1', selectedAgentIds: ['a'] }, store);
  let completeRead!: (value: unknown) => void;
  const read = new Promise<unknown>(resolve => { completeRead = resolve; });
  const internal = observer as unknown as {
    client: { connected: boolean; stop(): void };
    requestRead(): Promise<unknown>;
    scan(first?: unknown): Promise<void>;
    observeChatLifecycle(value: unknown): void;
  };
  internal.client = { connected: true, stop() {} };
  internal.requestRead = () => read;
  const scanning = internal.scan();
  internal.observeChatLifecycle({ runId: 'r', sessionKey: 'k', agentId: 'a', seq: 0, state: 'final' });
  completeRead({ sessions: [base], hasMore: false });
  await scanning;
  assert.deepEqual(store.snapshot().agents[agent.id].work.activeRunIds, []);
  assert.equal(store.snapshot().agents[agent.id].freshness, 'stale');
  await internal.scan({ sessions: [{ ...base, snapshotAt: 99, activeRunIds: [], hasActiveRun: false,
    status: 'idle' }], hasMore: false });
  assert.equal(store.snapshot().agents[agent.id].work.status, 'completed');
  assert.equal(store.snapshot().agents[agent.id].freshness, 'stale');
  await internal.scan({ sessions: [{ ...base, snapshotAt: 101, activeRunIds: [], hasActiveRun: false,
    status: 'done', lastRunId: 'r' }], hasMore: false });
  assert.equal(store.snapshot().agents[agent.id].freshness, 'fresh');
  assert.equal(store.snapshot().agents[agent.id].work.status, 'completed');
  observer.stop();
});

test('a delayed keyed row cannot restore a run ended by chat', () => {
  for (const activeRunIds of [['r'], null, []] as const) {
    const store = new FloorStore('fixture');
    const base = { key: 'k', agentId: 'a', sessionId: 's', status: 'running',
      activeRunIds: ['r'], hasActiveRun: true, snapshotAt: 100 };
    const agent = normalizeSessionRow(base, 'g', 100);
    store.replaceAgents([agent], true);
    const observer = new GatewayObserver({ gatewayId: 'g', gatewayUrl: 'ws://127.0.0.1:1', selectedAgentIds: ['a'] }, store);
    const internal = observer as unknown as {
      observeChatLifecycle(value: unknown): void;
      admitHeldRow(value: unknown): void;
    };
    internal.observeChatLifecycle({ runId: 'r', sessionKey: 'k', agentId: 'a', seq: 0, state: 'final' });
    internal.admitHeldRow({ session: { ...base, snapshotAt: 101, activeRunIds } });
    const current = store.snapshot().agents[agent.id];
    assert.deepEqual(current.work.activeRunIds, []);
    assert.equal(current.work.status, 'completed');
    assert.equal(current.freshness, 'stale');
    observer.stop();
  }
});

test('two later exact lists release a terminal fence when another run owns lastRunId', async () => {
  const store = new FloorStore('fixture');
  const base = { key: 'k', agentId: 'a', sessionId: 's', status: 'running',
    activeRunIds: ['r1','r2'], hasActiveRun: true, snapshotAt: 100 };
  const agent = normalizeSessionRow(base, 'g', 100);
  store.replaceAgents([agent], true);
  const observer = new GatewayObserver({ gatewayId: 'g', gatewayUrl: 'ws://127.0.0.1:1', selectedAgentIds: ['a'] }, store);
  const internal = observer as unknown as {
    client: { connected: boolean; stop(): void };
    observeChatLifecycle(value: unknown): void;
    scan(first?: unknown): Promise<void>;
  };
  internal.client = { connected: true, stop() {} };
  internal.observeChatLifecycle({ runId: 'r1', sessionKey: 'k', agentId: 'a', seq: 0, state: 'final' });
  const later = { ...base, snapshotAt: 101, activeRunIds: ['r2'], lastRunId: 'r2' };
  await internal.scan({ sessions: [later], hasMore: false });
  assert.equal(store.snapshot().agents[agent.id].freshness, 'stale');
  assert.deepEqual(store.snapshot().agents[agent.id].work.activeRunIds, ['r2']);
  await internal.scan({ sessions: [{ ...later, snapshotAt: 102 }], hasMore: false });
  assert.equal(store.snapshot().agents[agent.id].freshness, 'fresh');
  assert.deepEqual(store.snapshot().agents[agent.id].work.activeRunIds, ['r2']);
  observer.stop();
});

test('a missing session interrupts terminal absence confirmation', async () => {
  const store = new FloorStore('fixture');
  const base = { key: 'k', agentId: 'a', sessionId: 's', status: 'running',
    activeRunIds: ['r1','r2'], hasActiveRun: true, snapshotAt: 100 };
  const agent = normalizeSessionRow(base, 'g', 100);
  store.replaceAgents([agent], true);
  const observer = new GatewayObserver({ gatewayId: 'g', gatewayUrl: 'ws://127.0.0.1:1', selectedAgentIds: ['a'] }, store);
  const internal = observer as unknown as {
    client: { connected: boolean; stop(): void };
    observeChatLifecycle(value: unknown): void;
    scan(first?: unknown): Promise<void>;
  };
  internal.client = { connected: true, stop() {} };
  internal.observeChatLifecycle({ runId: 'r1', sessionKey: 'k', agentId: 'a', seq: 0, state: 'final' });
  const later = { ...base, activeRunIds: ['r2'], lastRunId: 'r2' };
  await internal.scan({ sessions: [{ ...later, snapshotAt: 101 }], hasMore: false });
  await internal.scan({ sessions: [], hasMore: false });
  await internal.scan({ sessions: [{ ...later, snapshotAt: 102 }], hasMore: false });
  assert.equal(store.snapshot().agents[agent.id].freshness, 'stale');
  await internal.scan({ sessions: [{ ...later, snapshotAt: 103 }], hasMore: false });
  assert.equal(store.snapshot().agents[agent.id].freshness, 'fresh');
  observer.stop();
});
