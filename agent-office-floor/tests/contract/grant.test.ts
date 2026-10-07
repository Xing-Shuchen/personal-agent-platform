import assert from 'node:assert/strict';
import test from 'node:test';
import { isReadOnlyGrant } from '../../packages/openclaw-adapter/src/connection/grant.ts';
import { FloorStore, GatewayObserver } from '@pap/openclaw-adapter';
import { normalizeSessionRow } from '../../packages/openclaw-adapter/src/normalization/session.ts';
import { applyFloorUpdate } from '@pap/floor-contract';

test('the office accepts only the exact operator.read Gateway grant', () => {
  assert.equal(isReadOnlyGrant({ role: 'operator', scopes: ['operator.read'] }), true);
  assert.equal(isReadOnlyGrant({ role: 'operator', scopes: ['operator.read', 'operator.write'] }), false);
  assert.equal(isReadOnlyGrant({ role: 'operator', scopes: ['operator.admin'] }), false);
  assert.equal(isReadOnlyGrant({ role: 'node', scopes: ['operator.read'] }), false);
});

test('a later transport error cannot relabel a denied observer as merely offline', () => {
  const store = new FloorStore('denied');
  const agent = normalizeSessionRow({ key: 'k', agentId: 'a' }, 'g', 100);
  store.replaceAgents([agent], true);
  let browser = null as ReturnType<typeof store.snapshot> | null;
  const unobserve = store.observe(update => { browser = applyFloorUpdate(browser, update); });
  const observer = new GatewayObserver({ gatewayId: 'g', gatewayUrl: 'ws://127.0.0.1:1',
    selectedAgentIds: ['a'] }, store);
  let stops = 0;
  const internal = observer as unknown as {
    client: { stop(): void };
    handleConnectError(error: Error): void;
  };
  internal.client = { stop: () => { stops++; } };
  internal.handleConnectError(new Error('permission denied: insufficient scope'));
  assert.equal(store.snapshot().connection.state, 'auth_required');
  assert.equal(store.snapshot().capabilities.sessionList, 'forbidden');
  assert.deepEqual(Object.keys(store.snapshot().agents), []);
  assert.deepEqual(Object.keys(browser!.agents), []);
  assert.equal(browser!.connection.state, 'auth_required');
  internal.handleConnectError(new Error('socket closed'));
  assert.equal(store.snapshot().connection.state, 'auth_required');
  assert.equal(stops, 1);
  unobserve();
  observer.stop();
});
