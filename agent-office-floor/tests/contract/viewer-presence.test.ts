import assert from 'node:assert/strict';
import test from 'node:test';
import { ViewerPresence } from '../../apps/server/src/viewer-presence.ts';
import { GatewayObserver } from '../../packages/openclaw-adapter/src/connection/observer.ts';
import { FloorStore } from '../../packages/openclaw-adapter/src/sessions/floor-store.ts';

test('multiple visible pages keep the observer active until the last leaves or expires', () => {
  const changes: boolean[] = [];
  const presence = new ViewerPresence(visible => changes.push(visible), 45);
  presence.report('a', true, 0);
  presence.report('b', true, 10);
  presence.report('a', false, 20);
  assert.equal(presence.visible, true);
  presence.expire(54);
  assert.equal(presence.visible, true);
  presence.expire(55);
  assert.equal(presence.visible, false);
  assert.deepEqual(changes, [true, false]);
});

test('a visible viewer triggers immediate calibration; hidden polling waits 15 seconds', () => {
  const observer = new GatewayObserver({ gatewayId: 'g', gatewayUrl: 'ws://127.0.0.1:1', selectedAgentIds: [] }, new FloorStore());
  const queued: number[] = [];
  const internal = observer as unknown as { queueScan(ms: number): void };
  internal.queueScan = ms => queued.push(ms);
  observer.setVisibleViewer(true);
  observer.setVisibleViewer(true);
  observer.setVisibleViewer(false);
  assert.deepEqual(queued, [0, 15000]);
});

test('visibility during bootstrap waits for the subscription baseline', () => {
  const observer = new GatewayObserver({ gatewayId: 'g', gatewayUrl: 'ws://127.0.0.1:1', selectedAgentIds: [] }, new FloorStore());
  const queued: number[] = [];
  const internal = observer as unknown as { bootstrapping: boolean; bootstrapDirty: boolean; queueScan(ms: number): void };
  internal.bootstrapping = true;
  internal.queueScan = ms => queued.push(ms);
  observer.setVisibleViewer(true);
  assert.deepEqual(queued, []);
  assert.equal(internal.bootstrapDirty, true);
});
