import assert from 'node:assert/strict';
import test from 'node:test';
import { FloorStore, GatewayObserver, normalizeSessionRow } from '@pap/openclaw-adapter';
import { advanceRunSequence, runReceipt } from '../../packages/openclaw-adapter/src/connection/run-sequence.ts';

test('per-run sequence rejects duplicates and identifies forward gaps', () => {
  assert.deepEqual(runReceipt({ runId: 'r', seq: 3, data: { secret: 'hidden' } }), { runId: 'r', seq: 3 });
  assert.equal(runReceipt({ runId: 'r', seq: -1 }), null);
  assert.equal(runReceipt({ runId: 'r', seq: 1.5 }), null);
  assert.equal(advanceRunSequence(undefined, 3), 'first');
  assert.equal(advanceRunSequence(3, 3), 'duplicate');
  assert.equal(advanceRunSequence(3, 2), 'duplicate');
  assert.equal(advanceRunSequence(3, 4), 'next');
  assert.equal(advanceRunSequence(3, 5), 'gap');
});

test('a mapped run gap marks only its session stale; unknown runs are never assigned', () => {
  const store = new FloorStore('e');
  const a = normalizeSessionRow({ key: 'a', agentId: 'one', sessionId: 's1', activeRunIds: ['r1'] }, 'g', 10);
  const b = normalizeSessionRow({ key: 'b', agentId: 'two', sessionId: 's2', activeRunIds: ['r2'] }, 'g', 10);
  store.replaceAgents([a, b], true);
  const observer = new GatewayObserver({ gatewayId: 'g', gatewayUrl: 'ws://127.0.0.1:1', selectedAgentIds: ['one', 'two'] }, store);
  const internal = observer as unknown as {
    client: { connected: boolean; stop(): void };
    observeRunSequence(payload: unknown): void;
  };
  internal.client = { connected: true, stop() {} };
  internal.observeRunSequence({ runId: 'unknown', seq: 0 });
  assert.equal(store.snapshot().agents[a.id].freshness, 'fresh');
  internal.observeRunSequence({ runId: 'r1', seq: 7 });
  internal.observeRunSequence({ runId: 'r1', seq: 7 });
  internal.observeRunSequence({ runId: 'r1', seq: 9 });
  assert.equal(store.snapshot().agents[a.id].freshness, 'stale');
  assert.equal(store.snapshot().agents[b.id].freshness, 'fresh');
  assert.equal(store.snapshot().agents[a.id].work.activeRunIds, null);
  observer.stop();
});

test('in-order run events do not poll per token and unmatched runs calibrate once', () => {
  const store = new FloorStore('e');
  const agent = normalizeSessionRow({ key: 'k', agentId: 'a', sessionId: 's', activeRunIds: ['r'] }, 'g', 10);
  store.replaceAgents([agent], true);
  const observer = new GatewayObserver({ gatewayId: 'g', gatewayUrl: 'ws://127.0.0.1:1', selectedAgentIds: ['a'] }, store);
  const internal = observer as unknown as {
    observeRunSequence(payload: unknown): void;
    observeChatLifecycle(payload: unknown): void;
    invalidatedAt: number | null;
    unmatchedRuns: Map<string, string>;
  };
  internal.observeRunSequence({ runId: 'r', seq: 0, data: { text: 'private' } });
  internal.observeRunSequence({ runId: 'r', seq: 1, data: { text: 'private' } });
  assert.equal(internal.invalidatedAt, null);
  internal.observeRunSequence({ runId: 'unknown', seq: 0 });
  assert.equal(internal.unmatchedRuns.get('unknown'), 'seen');
  internal.invalidatedAt = null;
  internal.observeRunSequence({ runId: 'unknown', seq: 1 });
  internal.observeChatLifecycle({ runId: 'unknown', sessionKey: 'missing', seq: 2, state: 'delta', deltaText: 'private' });
  assert.equal(internal.invalidatedAt, null);
  internal.observeChatLifecycle({ runId: 'unknown', sessionKey: 'missing', seq: 3, state: 'final', message: 'private' });
  assert.equal(internal.unmatchedRuns.get('unknown'), 'terminal');
  assert.notEqual(internal.invalidatedAt, null);
  observer.stop();
});

test('a reused run ID cannot inherit the agent sequence of a replaced session', () => {
  const store = new FloorStore('e');
  const row = (sessionId: string) => normalizeSessionRow({ key: 'k', agentId: 'a', sessionId,
    activeRunIds: ['r'] }, 'g', 10);
  store.replaceAgents([row('old')], true);
  const observer = new GatewayObserver({ gatewayId: 'g', gatewayUrl: 'ws://127.0.0.1:1', selectedAgentIds: ['a'] }, store);
  const internal = observer as unknown as { observeRunSequence(payload: unknown): void };
  internal.observeRunSequence({ runId: 'r', seq: 0 });
  store.replaceAgents([row('new')], true);
  internal.observeRunSequence({ runId: 'r', seq: 1 });
  assert.equal(store.snapshot().agents[row('new').id].freshness, 'stale');
  observer.stop();
});

test('unmergeable notices debounce for 250 ms but continuous notices calibrate within one second', () => {
  const observer = new GatewayObserver({ gatewayId: 'g', gatewayUrl: 'ws://127.0.0.1:1', selectedAgentIds: ['a'] }, new FloorStore('e'));
  const delays: number[] = [];
  const internal = observer as unknown as { invalidate(): void; invalidatedAt: number | null; queueScan(ms: number): void };
  internal.queueScan = ms => { delays.push(ms); };
  internal.invalidate();
  assert.equal(delays[0], 250);
  internal.invalidatedAt = Date.now() - 950;
  internal.invalidate();
  assert.ok(delays[1] >= 0 && delays[1] <= 50);
  observer.stop();
});
