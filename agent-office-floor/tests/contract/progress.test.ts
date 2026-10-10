import assert from 'node:assert/strict';
import test from 'node:test';
import { canReadProgress, normalizeProgressCard, progressCardMatchesRequest, progressReadParams } from '../../packages/openclaw-adapter/src/normalization/progress.ts';
import { FloorStore, GatewayObserver, normalizeSessionRow } from '@pap/openclaw-adapter';

test('progress card projection keeps only revision, time, note and typed steps', () => {
  assert.deepEqual(normalizeProgressCard({ card: { sessionKey: 'agent:a:global', revision: 2,
    updatedAt: 1234, markdown: 'Reviewing', steps: [{ step: 'Inspect', status: 'completed' }],
    unrelated: { raw: 'discard' } } }), { revision: 2, updatedAtMs: 1234,
    markdown: 'Reviewing', steps: [{ text: 'Inspect', status: 'completed' }] });
  assert.equal(normalizeProgressCard({ card: null }), null);
  assert.throws(() => normalizeProgressCard({ card: { sessionKey: 'k', revision: 1, updatedAt: 1,
    steps: [{ step: 'x', status: 'invented' }] } }), /steps/);
  assert.throws(() => normalizeProgressCard({ card: { sessionKey: 'k', revision: 1, updatedAt: 1,
    markdown: '中'.repeat(2731) } }), /markdown/);
  assert.throws(() => normalizeProgressCard({ card: { sessionKey: 'k', revision: 1, updatedAt: 1,
    steps: [{ step: '中'.repeat(171), status: 'pending' }] } }), /steps/);
  assert.throws(() => normalizeProgressCard({ card: { sessionKey: 'k', revision: 1, updatedAt: 1,
    steps: [{ step: 'a', status: 'in_progress' }, { step: 'b', status: 'in_progress' }] } }), /steps/);
});

test('progress owner capability gates reads and late replies cannot attach to replacement instances', () => {
  assert.equal(canReadProgress({ methods: ['progressCard.get'] }), false);
  assert.equal(canReadProgress({ methods: ['progressCard.get'], capabilities: ['progress-card-agent-scope-v1'] }), true);
  const store = new FloorStore('e');
  const first = normalizeSessionRow({ key: 'global', agentId: 'a', sessionId: 's1' }, 'g', 100);
  assert.deepEqual(progressReadParams(first, true), { sessionKey: 'global', agentId: 'a' });
  assert.equal(progressReadParams(first, false), null);
  const replacement = normalizeSessionRow({ key: 'global', agentId: 'a', sessionId: 's2' }, 'g', 200);
  store.replaceAgents([first], true);
  store.replaceAgents([replacement], true);
  const card = normalizeProgressCard({ card: { sessionKey: 'agent:a:global', revision: 1, updatedAt: 1 } });
  assert.equal(store.setProgress(first.id, 's1', card), false);
  assert.equal(store.snapshot().agents[first.id].progress, null);
  assert.equal(store.setProgress(first.id, 's2', card), true);
  assert.equal(store.snapshot().agents[first.id].progress?.revision, 1);
  const sameInstance = normalizeSessionRow({ key: 'global', agentId: 'a', sessionId: 's2' }, 'g', 300,
    {}, store.snapshot().agents[first.id]);
  assert.equal(sameInstance.progress?.revision, 1);
  const changedInstance = normalizeSessionRow({ key: 'global', agentId: 'a', sessionId: 's3' }, 'g', 400,
    {}, store.snapshot().agents[first.id]);
  assert.equal(changedInstance.progress, null);
});

test('progress cards from another owner or session are never attached to the selected row', async () => {
  const params = { sessionKey: 'global', agentId: 'a' };
  assert.equal(progressCardMatchesRequest({ card: { sessionKey: 'agent:a:global' } }, params), true);
  assert.equal(progressCardMatchesRequest({ card: { sessionKey: 'agent:b:global' } }, params), false);
  assert.equal(progressCardMatchesRequest({ card: { sessionKey: 'agent:a:other' } }, params), false);
  assert.equal(progressCardMatchesRequest({ card: null }, params), true);
  const store = new FloorStore('e');
  const agent = normalizeSessionRow({ key: 'global', agentId: 'a', sessionId: 's' }, 'g', 100);
  store.replaceAgents([agent], true);
  store.setProgress(agent.id, 's', normalizeProgressCard({ card: {
    sessionKey: 'agent:a:global', revision: 1, updatedAt: 1 } }));
  const observer = new GatewayObserver({ gatewayId: 'g', gatewayUrl: 'ws://127.0.0.1:1', selectedAgentIds: ['a'] }, store);
  const internal = observer as unknown as {
    client: { connected: boolean; stop(): void };
    progressSupported: boolean;
    requestRead(): Promise<unknown>;
  };
  internal.client = { connected: true, stop() {} };
  internal.progressSupported = true;
  internal.requestRead = async () => ({ card: { sessionKey: 'agent:b:global', revision: 2, updatedAt: 2 } });
  assert.equal(await observer.refreshProgress(agent.id), false);
  assert.equal(store.snapshot().agents[agent.id].progress, null);
  assert.equal(store.snapshot().capabilities.progressCard, 'partial');
  observer.stop();
});

test('progress permission loss removes cached cards while retaining session rows', async () => {
  const store = new FloorStore('e');
  const agent = normalizeSessionRow({ key: 'k', agentId: 'a', sessionId: 's' }, 'g', 100);
  const card = normalizeProgressCard({ card: { sessionKey: 'agent:a:k', revision: 1,
    updatedAt: 1, markdown: 'private card' } });
  store.replaceAgents([agent], true);
  assert.equal(store.setProgress(agent.id, 's', card), true);
  const observer = new GatewayObserver({ gatewayId: 'g', gatewayUrl: 'ws://127.0.0.1:1', selectedAgentIds: ['a'] }, store);
  const internal = observer as unknown as {
    client: { connected: boolean; stop(): void };
    progressSupported: boolean;
    requestRead(): Promise<unknown>;
  };
  internal.client = { connected: true, stop() {} };
  internal.progressSupported = true;
  internal.requestRead = () => Promise.reject(new Error('forbidden: progressCard.get'));
  assert.equal(await observer.refreshProgress(agent.id), false);
  assert.equal(store.snapshot().capabilities.progressCard, 'forbidden');
  assert.ok(store.snapshot().agents[agent.id]);
  assert.equal(store.snapshot().agents[agent.id].progress, null);
  assert.equal(JSON.stringify(store.snapshot()).includes('private card'), false);
  observer.stop();
});
