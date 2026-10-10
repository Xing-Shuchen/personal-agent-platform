import assert from 'node:assert/strict';
import test from 'node:test';
import { GatewayObserver } from '../../packages/openclaw-adapter/src/connection/observer.ts';
import { compactReceipt, initialCompactionCapability } from '../../packages/openclaw-adapter/src/normalization/operation.ts';
import { normalizeSessionRow } from '../../packages/openclaw-adapter/src/normalization/session.ts';
import { FloorStore } from '../../packages/openclaw-adapter/src/sessions/floor-store.ts';

const row = (sessionId = 's1') => ({ key: 'k', agentId: 'a', sessionId,
  updatedAt: 100, activeRunIds: [], hasActiveRun: false, status: 'idle' });
const event = (operationId: string, phase: 'start' | 'end', ts: number) =>
  ({ operationId, operation: 'compact', phase, sessionKey: 'k', agentId: 'a', ts,
    reason: 'private reason must not reach the browser' });

test('compaction receipt retains only protocol identity and lifecycle fields', () => {
  const receipt = compactReceipt(event('op', 'start', 120));
  assert.deepEqual(receipt, { operationId: 'op', sessionKey: 'k', agentId: 'a', phase: 'start', ts: 120 });
  assert.equal(JSON.stringify(receipt).includes('private'), false);
  assert.equal(compactReceipt({ ...event('op', 'start', 120), phase: 'progress' }), null);
});

test('Gateway event advertisement distinguishes unsupported from unverified compaction', () => {
  assert.equal(initialCompactionCapability(['sessions.changed']), 'unsupported');
  assert.equal(initialCompactionCapability(['sessions.changed', 'session.operation']), 'unverified');
});

test('paired operation survives list calibration; wrong end and replacement instance do not apply', async () => {
  const store = new FloorStore('fixture');
  const first = normalizeSessionRow(row(), 'g', 100);
  store.replaceAgents([first], true);
  const observer = new GatewayObserver({ gatewayId: 'g', gatewayUrl: 'ws://127.0.0.1:1', selectedAgentIds: ['a'] }, store);
  const internal = observer as unknown as {
    client: { connected: boolean; stop(): void };
    observeOperation(value: unknown): void;
    scan(first?: unknown): Promise<void>;
  };
  internal.client = { connected: true, stop() {} };
  internal.observeOperation(event('op1', 'start', 120));
  assert.equal(store.snapshot().agents[first.id].work.compacting, true);
  assert.equal(store.snapshot().capabilities.compaction, 'partial');
  await internal.scan({ sessions: [{ ...row(), snapshotAt: 130 }], hasMore: false });
  assert.equal(store.snapshot().agents[first.id].work.compacting, true);
  internal.observeOperation(event('other', 'end', 140));
  assert.equal(store.snapshot().agents[first.id].work.compacting, true);
  internal.observeOperation(event('op1', 'end', 150));
  assert.equal(store.snapshot().agents[first.id].work.compacting, false);
  assert.equal(store.snapshot().capabilities.compaction, 'available');
  await internal.scan({ sessions: [{ ...row('s2'), updatedAt: 200, snapshotAt: 200 }], hasMore: false });
  assert.equal(store.snapshot().agents[first.id].work.compacting, null);
  internal.observeOperation(event('op1', 'end', 210));
  assert.equal(store.snapshot().agents[first.id].work.compacting, null);
  observer.stop();
});

test('an operation older than the current row cannot claim a reused key', () => {
  const store = new FloorStore('fixture');
  const agent = normalizeSessionRow({ ...row('s2'), updatedAt: 200 }, 'g', 200);
  store.replaceAgents([agent], true);
  const observer = new GatewayObserver({ gatewayId: 'g', gatewayUrl: 'ws://127.0.0.1:1', selectedAgentIds: ['a'] }, store);
  (observer as unknown as { observeOperation(value: unknown): void }).observeOperation(event('old', 'start', 150));
  assert.equal(store.snapshot().agents[agent.id].work.compacting, null);
  assert.equal(store.snapshot().agents[agent.id].freshness, 'stale');
  observer.stop();
});
