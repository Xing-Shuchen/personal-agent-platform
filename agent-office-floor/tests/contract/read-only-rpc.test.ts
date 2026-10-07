import assert from 'node:assert/strict';
import test from 'node:test';
import { FloorStore, GatewayObserver } from '@pap/openclaw-adapter';

test('runtime RPC gate rejects writes before the Gateway client sees them', async () => {
  const observer = new GatewayObserver({ gatewayId: 'g', gatewayUrl: 'ws://127.0.0.1:1',
    selectedAgentIds: ['a'] }, new FloorStore('e'));
  const methods: string[] = [];
  const internal = observer as unknown as {
    client: { connected: boolean; request(method: string, params: object): Promise<unknown>; stop(): void };
    requestRead(method: string, params: object): Promise<unknown>;
  };
  internal.client = { connected: true, request: async method => { methods.push(method); return {}; }, stop() {} };
  for (const method of ['chat.send', 'sessions.delete', 'progressCard.refresh', 'approvals.resolve', 'agents.create']) {
    await assert.rejects(internal.requestRead(method, {}), /observer RPC not allowed/);
  }
  assert.deepEqual(methods, []);
  await internal.requestRead('sessions.list', { limit: 1 });
  assert.deepEqual(methods, ['sessions.list']);
  observer.stop();
});
