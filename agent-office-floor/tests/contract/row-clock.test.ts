import assert from 'node:assert/strict';
import test from 'node:test';
import { GatewayObserver, FloorStore, normalizeSessionRow } from '@pap/openclaw-adapter';
import { newerRow, rowClock } from '../../packages/openclaw-adapter/src/normalization/row-clock.ts';

test('an event received during a list read wins an older or tied page for the same instance', () => {
  const page = rowClock({ key: 'k', sessionId: 's', snapshotAt: 200 }, 1)!;
  const event = rowClock({ key: 'k', sessionId: 's', snapshotAt: 200 }, 2)!;
  assert.equal(newerRow(page, event), true);
  assert.equal(newerRow(event, page), false);
  assert.equal(newerRow(event, rowClock({ key: 'k', sessionId: 's', snapshotAt: 199 }, 3)), false);
  assert.equal(newerRow(event, rowClock({ key: 'k', sessionId: 's', snapshotAt: 201 }, 3)), true);
  assert.equal(rowClock({ key: 'k', sessionId: 's' }, 3), null);
});

test('keyed events update only a held matching instance and project no raw message', () => {
  const store = new FloorStore('e');
  const held = normalizeSessionRow({ key: 'k', agentId: 'a', sessionId: 's', snapshotAt: 100, activeRunIds: ['r1'] }, 'g', 100);
  store.replaceAgents([held], true);
  const observer = new GatewayObserver({ gatewayId: 'g', gatewayUrl: 'ws://127.0.0.1:1', selectedAgentIds: ['a'] }, store);
  const admit = (observer as unknown as { admitHeldRow(payload: unknown): void }).admitHeldRow.bind(observer);
  admit({ session: { key: 'k', agentId: 'a', sessionId: 's', snapshotAt: 101,
    activeRunIds: ['r2'], secretMessage: 'private' } });
  assert.deepEqual(store.snapshot().agents[held.id].work.activeRunIds, ['r2']);
  assert.equal(JSON.stringify(store.snapshot()).includes('private'), false);
  admit({ session: { key: 'k', agentId: 'a', sessionId: 's', snapshotAt: 102, status: 'running' } });
  assert.deepEqual(store.snapshot().agents[held.id].work.activeRunIds, ['r2']);
  admit({ session: { key: 'k', agentId: 'a', sessionId: 's', snapshotAt: 103 }, activeRunIds: null });
  assert.equal(store.snapshot().agents[held.id].work.activeRunIds, null);
  const revision = store.snapshot().revision;
  admit({ session: { key: 'k', agentId: 'a', sessionId: 's', snapshotAt: 100, activeRunIds: ['old'] } });
  admit({ session: { key: 'k', agentId: 'a', sessionId: 'replacement', snapshotAt: 102, activeRunIds: ['wrong'] } });
  admit({ session: { key: 'k', agentId: 'other', sessionId: 's', snapshotAt: 102, activeRunIds: ['wrong'] } });
  assert.equal(store.snapshot().revision, revision);
  assert.equal(store.snapshot().agents[held.id].work.activeRunIds, null);
});

test('an event during an overlapping scan survives the older list response', async () => {
  const store = new FloorStore('e');
  const held = normalizeSessionRow({ key: 'k', agentId: 'a', sessionId: 's', snapshotAt: 199,
    activeRunIds: ['old'] }, 'g', 100);
  store.replaceAgents([held], true);
  const observer = new GatewayObserver({ gatewayId: 'g', gatewayUrl: 'ws://127.0.0.1:1', selectedAgentIds: ['a'] }, store);
  let completeRead!: (value: unknown) => void;
  const read = new Promise<unknown>(resolve => { completeRead = resolve; });
  const internals = observer as unknown as {
    client: { connected: boolean; stop(): void };
    requestRead(): Promise<unknown>;
    scan(): Promise<void>;
    admitHeldRow(payload: unknown): void;
  };
  internals.client = { connected: true, stop() {} };
  internals.requestRead = () => read;
  const scan = internals.scan();
  internals.admitHeldRow({ session: { key: 'k', agentId: 'a', sessionId: 's', snapshotAt: 200,
    activeRunIds: ['new'] } });
  completeRead({ sessions: [{ key: 'k', agentId: 'a', sessionId: 's', snapshotAt: 200,
    activeRunIds: ['old'] }], hasMore: false });
  await scan;
  assert.deepEqual(store.snapshot().agents[held.id].work.activeRunIds, ['new']);
  observer.stop();
});

test('a stale row stays uncertain until a list snapshot catches up', async () => {
  const store = new FloorStore('e');
  const held = normalizeSessionRow({ key: 'k', agentId: 'a', sessionId: 's', snapshotAt: 100,
    activeRunIds: ['r'] }, 'g', 10);
  store.replaceAgents([held], true);
  const observer = new GatewayObserver({ gatewayId: 'g', gatewayUrl: 'ws://127.0.0.1:1', selectedAgentIds: ['a'] }, store);
  const internal = observer as unknown as {
    client: { connected: boolean; stop(): void };
    admitHeldRow(payload: unknown): void;
    scan(first: unknown): Promise<void>;
  };
  internal.client = { connected: true, stop() {} };
  internal.admitHeldRow({ session: { key: 'k', agentId: 'a', sessionId: 's', snapshotAt: 200,
    activeRunIds: ['new'] } });
  store.markAgentStale(held.id);
  await internal.scan({ sessions: [{ key: 'k', agentId: 'a', sessionId: 's', snapshotAt: 199,
    activeRunIds: ['old'] }], hasMore: false });
  assert.equal(store.snapshot().agents[held.id].freshness, 'stale');
  assert.equal(store.snapshot().agents[held.id].work.activeRunIds, null);
  assert.equal(store.snapshot().connection.state, 'degraded');
  await internal.scan({ sessions: [{ key: 'k', agentId: 'a', sessionId: 's', snapshotAt: 201,
    activeRunIds: ['current'] }], hasMore: false });
  assert.equal(store.snapshot().agents[held.id].freshness, 'fresh');
  assert.deepEqual(store.snapshot().agents[held.id].work.activeRunIds, ['current']);
  assert.equal(store.snapshot().connection.state, 'live');
  observer.stop();
});
