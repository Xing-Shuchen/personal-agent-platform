import assert from 'node:assert/strict';
import test from 'node:test';
import { GatewaySessionMessageSubscriptionCoordinator } from '@openclaw/gateway-client';
import { FloorStore, GatewayObserver, normalizeSessionRow } from '@pap/openclaw-adapter';

test('session observer leases follow the visible session generation and release removed rows', async () => {
  const store = new FloorStore('e');
  const first = normalizeSessionRow({ key: 'k', agentId: 'a', sessionId: 's1' }, 'g', 1);
  store.replaceAgents([first], true);
  const calls: Array<{ method: string; key: string; agentId: unknown }> = [];
  const coordinator = new GatewaySessionMessageSubscriptionCoordinator({
    request: async <T>(method: string, params: Record<string, unknown>): Promise<T> => {
      calls.push({ method, key: String(params.key), agentId: params.agentId });
      return { key: 'canonical-k', agentId: 'a' } as T;
    }
  });
  const observer = new GatewayObserver({ gatewayId: 'g', gatewayUrl: 'ws://127.0.0.1:1', selectedAgentIds: ['a'] }, store);
  const internal = observer as unknown as {
    messageCoordinator: GatewaySessionMessageSubscriptionCoordinator;
    subscribeMessages(agents: readonly typeof first[], epoch: number): Promise<void>;
  };
  internal.messageCoordinator = coordinator;
  assert.deepEqual(observer.subscriptionCoverage(), { target: 1, leased: 0, queuedReads: 0, syncing: false, unsupported: false });
  await internal.subscribeMessages([first], 0);
  assert.deepEqual(calls, [{ method: 'sessions.messages.subscribe', key: 'k', agentId: 'a' }]);
  assert.deepEqual(observer.subscriptionCoverage(), { target: 1, leased: 1, queuedReads: 0, syncing: false, unsupported: false });
  const second = normalizeSessionRow({ key: 'k', agentId: 'a', sessionId: 's2' }, 'g', 2);
  store.replaceAgents([second], true);
  await internal.subscribeMessages([second], 0);
  assert.deepEqual(calls.map(call => [call.method, call.key]), [
    ['sessions.messages.subscribe', 'k'],
    ['sessions.messages.unsubscribe', 'canonical-k'],
    ['sessions.messages.subscribe', 'k']
  ]);
  store.replaceAgents([], true);
  await internal.subscribeMessages([], 0);
  assert.equal(calls.at(-1)?.method, 'sessions.messages.unsubscribe');
  assert.equal(observer.subscriptionCoverage().leased, 0);
  observer.stop();
});

test('a subscription acquired after connection replacement is released', async () => {
  const store = new FloorStore('e');
  const agent = normalizeSessionRow({ key: 'k', agentId: 'a', sessionId: 's1' }, 'g', 1);
  store.replaceAgents([agent], true);
  let finish!: (value: unknown) => void;
  const pending = new Promise<unknown>(resolve => { finish = resolve; });
  const calls: string[] = [];
  const coordinator = new GatewaySessionMessageSubscriptionCoordinator({
    request: async <T>(method: string): Promise<T> => {
      calls.push(method);
      return (method === 'sessions.messages.subscribe' ? await pending : {}) as T;
    }
  });
  const observer = new GatewayObserver({ gatewayId: 'g', gatewayUrl: 'ws://127.0.0.1:1',
    selectedAgentIds: ['a'] }, store);
  const internal = observer as unknown as {
    messageCoordinator: GatewaySessionMessageSubscriptionCoordinator;
    messageLeases: Map<string, unknown>;
    connectionEpoch: number;
    subscribeMessages(agents: readonly typeof agent[], epoch: number): Promise<void>;
  };
  internal.messageCoordinator = coordinator;
  const subscribing = internal.subscribeMessages([agent], 0);
  internal.connectionEpoch = 1;
  finish({ key: 'canonical-k', agentId: 'a' });
  await subscribing;
  assert.deepEqual(calls, ['sessions.messages.subscribe', 'sessions.messages.unsubscribe']);
  assert.equal(internal.messageLeases.size, 0);
  observer.stop();
});

test('polling the roster still acquires available per-session message leases', async () => {
  const store = new FloorStore('e');
  const calls: string[] = [];
  const coordinator = new GatewaySessionMessageSubscriptionCoordinator({
    request: async <T>(method: string): Promise<T> => {
      calls.push(method);
      return { key: 'canonical-k', agentId: 'a' } as T;
    }
  });
  const observer = new GatewayObserver({ gatewayId: 'g', gatewayUrl: 'ws://127.0.0.1:1', selectedAgentIds: ['a'] }, store);
  const internal = observer as unknown as {
    client: { connected: boolean; stop(): void };
    messageCoordinator: GatewaySessionMessageSubscriptionCoordinator;
    scan(first: unknown): Promise<void>;
  };
  internal.client = { connected: true, stop() {} };
  internal.messageCoordinator = coordinator;
  await internal.scan({ sessions: [{ key: 'k', agentId: 'a', sessionId: 's' }], hasMore: false });
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(store.snapshot().connection.mode, 'polling');
  assert.deepEqual(calls, ['sessions.messages.subscribe']);
  observer.stop();
});

test('an unsupported message-subscription method is not retried on every poll', async () => {
  const store = new FloorStore('e');
  let calls = 0;
  const coordinator = new GatewaySessionMessageSubscriptionCoordinator({
    request: async <T>(): Promise<T> => { calls++; throw new Error('unknown method'); }
  });
  const observer = new GatewayObserver({ gatewayId: 'g', gatewayUrl: 'ws://127.0.0.1:1', selectedAgentIds: ['a'] }, store);
  const internal = observer as unknown as {
    client: { connected: boolean; stop(): void };
    messageCoordinator: GatewaySessionMessageSubscriptionCoordinator;
    scan(first: unknown): Promise<void>;
  };
  internal.client = { connected: true, stop() {} };
  internal.messageCoordinator = coordinator;
  const page = { sessions: [{ key: 'k', agentId: 'a', sessionId: 's' }], hasMore: false };
  await internal.scan(page);
  await new Promise(resolve => setImmediate(resolve));
  await internal.scan(page);
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(calls, 1);
  observer.stop();
});
