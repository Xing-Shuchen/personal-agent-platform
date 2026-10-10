import assert from 'node:assert/strict';
import test from 'node:test';
import { FloorStore, GatewayObserver, floorId } from '@pap/openclaw-adapter';

test('observer keeps 100+ sessions across pages and prefers the newer overlapping row', async () => {
  const store = new FloorStore('e');
  const observer = new GatewayObserver({ gatewayId: 'g', gatewayUrl: 'ws://127.0.0.1:1', selectedAgentIds: ['a'] }, store);
  const rows = Array.from({ length: 101 }, (_, i) => ({
    key: `k${i}`, agentId: 'a', sessionId: `s${i}`, snapshotAt: 100,
    activeRunIds: [] as string[]
  }));
  const requests: object[] = [];
  const internal = observer as unknown as {
    client: { connected: boolean; stop(): void };
    requestRead(method: string, params: object): Promise<unknown>;
    scan(first: unknown): Promise<void>;
  };
  internal.client = { connected: true, stop() {} };
  internal.requestRead = async (_method, params) => {
    requests.push(params);
    return { sessions: [{ ...rows[99], snapshotAt: 200, activeRunIds: ['r99'] }, rows[100]], hasMore: false };
  };
  await internal.scan({ sessions: rows.slice(0, 100), hasMore: true, nextOffset: 100 });
  assert.deepEqual(requests, [{ limit: 100, offset: 100, includeLastMessage: false }]);
  assert.equal(Object.keys(store.snapshot().agents).length, 101);
  assert.deepEqual(store.snapshot().agents[floorId('g', 'a', 'k99')].work.activeRunIds, ['r99']);
  assert.equal(store.snapshot().agents[floorId('g', 'a', 'k100')].session.sessionId, 's100');

  internal.requestRead = async () => { throw new Error('page unavailable'); };
  await internal.scan({ sessions: rows.slice(0, 100), hasMore: true, nextOffset: 100 });
  assert.equal(Object.keys(store.snapshot().agents).length, 101);
  assert.equal(store.snapshot().connection.state, 'degraded');
  observer.stop();
});
