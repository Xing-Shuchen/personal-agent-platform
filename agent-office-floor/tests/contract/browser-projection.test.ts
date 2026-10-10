import assert from 'node:assert/strict';
import test from 'node:test';
import { BrowserProjection } from '../../apps/server/src/browser-projection.ts';
import { emptyFloorState, isFloorState } from '../../packages/floor-contract/src/index.ts';
import { normalizeSessionRow } from '../../packages/openclaw-adapter/src/normalization/session.ts';

test('browser projection keeps the required session address but hides composite run identifiers', () => {
  const secret = Buffer.alloc(32, 7);
  const projection = new BrowserProjection(secret);
  const raw = 'announce:requester-settle:feishu:direct:recipient-private:retry-2';
  const agent = normalizeSessionRow({ key: 'agent:a:feishu:direct:recipient-private',
    agentId: 'a', sessionId: 'instance-private', activeRunIds: [raw], hasActiveRun: true,
    status: 'running' }, 'gateway', 100);
  const decorated = { ...agent, work: { ...agent.work,
    latestOutcome: { runId: raw, result: 'error' as const, endedAtMs: 99, message: null },
    tool: { name: 'read_file', callId: 'call-private', phase: 'start' as const },
    evidence: [{ source: 'run_event' as const, reference: `${raw}:1`, sourceAtMs: null, observedAtMs: 100 }]
  } };
  const state = { ...emptyFloorState('epoch'), agents: { [agent.id]: decorated } };
  const browser = projection.state(state);
  const visible = browser.agents[agent.id];
  assert.equal(isFloorState(browser), true);
  assert.equal(visible.work.activeRunIds?.[0], visible.work.latestOutcome?.runId);
  assert.equal(visible.session.key, agent.session.key);
  assert.equal(visible.session.sessionId, agent.session.sessionId);
  assert.equal(visible.work.status, 'running');
  assert.equal(visible.work.tool?.name, 'read_file');
  assert.equal(JSON.stringify(browser).includes(raw), false);
  assert.equal(JSON.stringify(browser).includes('call-private'), false);
  assert.equal(decorated.work.activeRunIds?.[0], raw);
  const patch = projection.update({ type: 'patch', schemaVersion: 1, epoch: 'epoch',
    baseRevision: 0, revision: 1, generatedAtMs: 101, upserts: [decorated], removeIds: [] });
  assert.equal(patch.type, 'patch');
  if (patch.type === 'patch') assert.deepEqual(patch.upserts[0], visible);
});
