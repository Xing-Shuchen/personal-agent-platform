import assert from 'node:assert/strict';
import test from 'node:test';
import { applyFloorUpdate } from '@pap/floor-contract';
import { FloorStore, GatewayObserver, floorId, normalizeSessionRow } from '@pap/openclaw-adapter';

test('a reconnect baseline replaces stale running rows with terminal and continuing rounds', async () => {
  const store = new FloorStore('before');
  const observer = new GatewayObserver({ gatewayId: 'g', gatewayUrl: 'ws://127.0.0.1:1',
    selectedAgentIds: ['a'] }, store);
  const initial = ['success', 'failure', 'continuing'].map(key => normalizeSessionRow({
    key, agentId: 'a', sessionId: `instance-${key}`, status: 'running',
    activeRunIds: [`old-${key}`], hasActiveRun: true, snapshotAt: 100
  }, 'g', 100));
  let browser = null as ReturnType<typeof store.snapshot> | null;
  const updates: string[] = [];
  const off = store.observe(update => {
    updates.push(update.type);
    browser = applyFloorUpdate(browser, update);
  });
  store.replaceAgents(initial, true);
  assert.equal(store.setCompacting(floorId('g', 'a', 'continuing'), 'instance-continuing',
    'old-operation', true, 100, 101), true);
  store.setConnection({ mode: 'subscription', state: 'offline', lastConfirmedAtMs: 100,
    reason: 'connection lost' });
  for (const agent of Object.values(browser!.agents)) {
    assert.equal(agent.freshness, 'stale');
    assert.equal(agent.work.status, 'running');
    assert.equal(agent.work.activeRunIds, null);
    assert.equal(agent.work.latestOutcome, null);
    assert.equal(agent.work.compacting, null);
  }

  const oldEpoch = browser!.epoch;
  store.resetEpoch();
  const internal = observer as unknown as {
    client: { connected: boolean; stop(): void };
    connectionEpoch: number;
    scan(first: unknown, epoch: number): Promise<void>;
  };
  internal.client = { connected: true, stop() {} };
  internal.connectionEpoch = 1;
  await internal.scan({ sessions: [
    { key: 'success', agentId: 'a', sessionId: 'instance-success', status: 'done',
      lastRunId: 'old-success', activeRunIds: [], hasActiveRun: false, snapshotAt: 200 },
    { key: 'failure', agentId: 'a', sessionId: 'instance-failure', status: 'failed',
      lastRunId: 'old-failure', activeRunIds: [], hasActiveRun: false, snapshotAt: 200 },
    { key: 'continuing', agentId: 'a', sessionId: 'instance-continuing', status: 'running',
      activeRunIds: ['new-continuing'], hasActiveRun: true, snapshotAt: 200 }
  ], hasMore: false }, 1);

  assert.notEqual(browser!.epoch, oldEpoch);
  assert.equal(updates.filter(type => type === 'snapshot').length, 2);
  assert.equal(browser!.connection.state, 'live');
  const completed = browser!.agents[floorId('g', 'a', 'success')];
  const failed = browser!.agents[floorId('g', 'a', 'failure')];
  const continuing = browser!.agents[floorId('g', 'a', 'continuing')];
  assert.equal(completed.freshness, 'fresh');
  assert.equal(completed.work.status, 'completed');
  assert.equal(completed.work.latestOutcome?.result, 'success');
  assert.equal(failed.freshness, 'fresh');
  assert.equal(failed.work.status, 'error');
  assert.equal(failed.work.latestOutcome?.result, 'error');
  assert.equal(continuing.freshness, 'fresh');
  assert.equal(continuing.work.status, 'running');
  assert.deepEqual(continuing.work.activeRunIds, ['new-continuing']);
  assert.equal(continuing.work.latestOutcome, null);
  assert.equal(continuing.work.compacting, null);
  off();
  observer.stop();
});
