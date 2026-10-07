import assert from 'node:assert/strict';
import test from 'node:test';
import { FloorStore, GatewayObserver, floorId } from '@pap/openclaw-adapter';

test('an event during subscribe waits for the initial list and forces a trailing scan', async () => {
  const store = new FloorStore('e');
  const observer = new GatewayObserver({ gatewayId: 'g', gatewayUrl: 'ws://127.0.0.1:1', selectedAgentIds: ['a'] }, store);
  let finishSubscribe!: (value: unknown) => void;
  const subscribing = new Promise<unknown>(resolve => { finishSubscribe = resolve; });
  let finishListCall!: () => void;
  const listCalled = new Promise<void>(resolve => { finishListCall = resolve; });
  let listReads = 0;
  const internal = observer as unknown as {
    client: { connected: boolean; stop(): void };
    bootstrapping: boolean;
    requestRead(method: string): Promise<unknown>;
    bootstrap(epoch: number): Promise<void>;
    invalidate(): void;
  };
  internal.client = { connected: true, stop() {} };
  internal.bootstrapping = true;
  internal.requestRead = async method => {
    if (method === 'sessions.subscribe') return subscribing;
    listReads++; finishListCall();
    return { sessions: [{ key: 'k', agentId: 'a', sessionId: 's', snapshotAt: 101,
      activeRunIds: ['new'] }], hasMore: false };
  };
  const bootstrap = internal.bootstrap(0);
  internal.invalidate();
  assert.equal(listReads, 0);
  finishSubscribe({ subscribed: true, list: { sessions: [{ key: 'k', agentId: 'a', sessionId: 's',
    snapshotAt: 100, activeRunIds: ['old'] }], hasMore: false } });
  await bootstrap;
  assert.equal(store.snapshot().connection.state, 'degraded');
  await listCalled;
  await new Promise<void>(resolve => setImmediate(resolve));
  assert.equal(listReads, 1);
  assert.deepEqual(store.snapshot().agents[floorId('g', 'a', 'k')].work.activeRunIds, ['new']);
  assert.equal(store.snapshot().connection.state, 'live');
  assert.equal(store.snapshot().capabilities.blockingInput, 'forbidden');
  observer.stop();
});

test('an old connection scan cannot overwrite the new epoch baseline', async () => {
  const store = new FloorStore('e');
  const observer = new GatewayObserver({ gatewayId: 'g', gatewayUrl: 'ws://127.0.0.1:1', selectedAgentIds: ['a'] }, store);
  let finishOld!: (value: unknown) => void;
  const oldReply = new Promise<unknown>(resolve => { finishOld = resolve; });
  const internal = observer as unknown as {
    client: { connected: boolean; stop(): void };
    connectionEpoch: number;
    scanBusyEpoch: number | null;
    requestRead(): Promise<unknown>;
    scan(first?: unknown, epoch?: number): Promise<void>;
  };
  internal.client = { connected: true, stop() {} };
  internal.requestRead = () => oldReply;
  const oldScan = internal.scan(undefined, 0);
  internal.connectionEpoch = 1;
  internal.scanBusyEpoch = null;
  await internal.scan({ sessions: [{ key: 'new', agentId: 'a', sessionId: 'new', snapshotAt: 200 }],
    hasMore: false }, 1);
  finishOld({ sessions: [{ key: 'old', agentId: 'a', sessionId: 'old', snapshotAt: 100 }], hasMore: false });
  await oldScan;
  assert.ok(store.snapshot().agents[floorId('g', 'a', 'new')]);
  assert.equal(store.snapshot().agents[floorId('g', 'a', 'old')], undefined);
  observer.stop();
});

test('subscription failure reports its coverage before polling fallback', async () => {
  for (const [message, expected] of [
    ['unknown method', 'unsupported'], ['forbidden', 'forbidden'], ['request timeout', 'partial']
  ] as const) {
    const store = new FloorStore('e');
    const observer = new GatewayObserver({ gatewayId: 'g', gatewayUrl: 'ws://127.0.0.1:1', selectedAgentIds: ['a'] }, store);
    const internal = observer as unknown as {
      client: { connected: boolean; stop(): void };
      requestRead(method: string): Promise<unknown>;
      bootstrap(epoch: number): Promise<void>;
    };
    internal.client = { connected: true, stop() {} };
    internal.requestRead = async method => {
      if (method === 'sessions.subscribe') throw new Error(message);
      return { sessions: [{ key: 'k', agentId: 'a', sessionId: 's' }], hasMore: false };
    };
    await internal.bootstrap(0);
    assert.equal(store.snapshot().capabilities.sessionEvents, expected);
    assert.equal(store.snapshot().connection.mode, 'polling');
    assert.ok(store.snapshot().agents[floorId('g', 'a', 'k')]);
    observer.stop();
  }
});
