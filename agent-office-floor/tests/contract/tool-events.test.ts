import assert from 'node:assert/strict';
import test from 'node:test';
import { GatewayObserver } from '../../packages/openclaw-adapter/src/connection/observer.ts';
import { initialToolCapability, isReadTool, toolReceipt } from '../../packages/openclaw-adapter/src/normalization/tool.ts';
import { normalizeSessionRow } from '../../packages/openclaw-adapter/src/normalization/session.ts';
import { FloorStore } from '../../packages/openclaw-adapter/src/sessions/floor-store.ts';
import { visualState } from '../../packages/office-scene/src/stateMapping/index.ts';

const event = (seq: number, phase: string, sessionId = 's1') => ({
  stream: 'tool', runId: 'run', seq, sessionKey: 'key', agentId: 'agent',
  session: { key: 'key', sessionId, privatePath: '/private/source' },
  data: { phase, name: 'read_file', toolCallId: 'call', args: { secret: 'private argument' },
    result: { secret: 'private result' }, isError: true }
});

test('session.tool parser retains identity and phase but no arguments or result', () => {
  assert.equal(isReadTool('read_file'), true);
  assert.equal(isReadTool('write_file'), false);
  assert.equal(isReadTool('read_file_and_write'), false);
  assert.equal(initialToolCapability(['session.tool']), 'unverified');
  assert.equal(initialToolCapability(['agent']), 'unsupported');
  assert.deepEqual(toolReceipt(event(2, 'start')), { runId: 'run', seq: 2,
    sessionKey: 'key', sessionId: 's1', agentId: 'agent', callId: 'call', name: 'read_file', phase: 'start' });
  assert.equal(JSON.stringify(toolReceipt(event(3, 'result'))).includes('private'), false);
  assert.equal(toolReceipt({ ...event(2, 'start'), sessionKey: 'another' }), null);
  assert.equal(toolReceipt({ ...event(2, 'start'), data: { ...event(2, 'start').data, name: 'private text here' } }), null);
  for (const name of ['/private/source', '../private', 'data/tenant/file', 'C:/Data/private', 'foo..bar'])
    assert.equal(toolReceipt({ ...event(2, 'start'), data: { ...event(2, 'start').data, name } }), null);
  assert.equal(toolReceipt({ ...event(2, 'start'), data: { ...event(2, 'start').data,
    name: 'mcp__server.tool-name' } })?.name, 'mcp__server.tool-name');
  assert.equal(toolReceipt(event(2, 'unknown')), null);
});

test('tool start, update and result stay with one confirmed active session', () => {
  const store = new FloorStore('fixture');
  const agent = normalizeSessionRow({ key: 'key', agentId: 'agent', sessionId: 's1',
    activeRunIds: ['run'], hasActiveRun: true, status: 'running' }, 'gateway', 100);
  store.replaceAgents([agent], true);
  const observer = new GatewayObserver({ gatewayId: 'gateway', gatewayUrl: 'ws://127.0.0.1:1',
    selectedAgentIds: ['agent'] }, store);
  const internal = observer as unknown as { observeTool(value: unknown): void };
  internal.observeTool(event(2, 'start'));
  assert.deepEqual(store.snapshot().agents[agent.id].work.tool,
    { name: 'read_file', callId: 'call', phase: 'start' });
  assert.equal(store.snapshot().agents[agent.id].work.phase, 'reading');
  assert.equal(visualState(store.snapshot().agents[agent.id]).label, '读取中');
  assert.equal(store.snapshot().capabilities.toolEvents, 'partial');
  internal.observeTool(event(4, 'update'));
  assert.equal(store.snapshot().agents[agent.id].work.tool?.phase, 'update');
  internal.observeTool(event(3, 'result'));
  assert.equal(store.snapshot().agents[agent.id].work.tool?.phase, 'update');
  internal.observeTool(event(5, 'result'));
  assert.equal(store.snapshot().agents[agent.id].work.tool, null);
  assert.equal(store.snapshot().agents[agent.id].work.phase, 'executing');
  assert.equal(store.snapshot().agents[agent.id].work.status, 'running');
  assert.equal(JSON.stringify(store.snapshot()).includes('private'), false);
  internal.observeTool({ ...event(6, 'start'), data: { ...event(6, 'start').data, name: 'write_file' } });
  assert.equal(store.snapshot().agents[agent.id].work.phase, 'executing');
  assert.equal(visualState(store.snapshot().agents[agent.id]).label, '工具 write_file');
  internal.observeTool(event(7, 'start', 'replacement'));
  assert.equal(store.snapshot().agents[agent.id].work.tool?.name, 'write_file');
  observer.stop();
});

test('scoped tool payloads in agent events use the same read-only tool projection', () => {
  const store = new FloorStore('fixture');
  const agent = normalizeSessionRow({ key: 'key', agentId: 'agent', sessionId: 's1',
    activeRunIds: ['run'], hasActiveRun: true, status: 'running' }, 'gateway', 100);
  store.replaceAgents([agent], true);
  const observer = new GatewayObserver({ gatewayId: 'gateway', gatewayUrl: 'ws://127.0.0.1:1',
    selectedAgentIds: ['agent'] }, store);
  const internal = observer as unknown as { observeAgent(value: unknown): void };
  internal.observeAgent(event(2, 'start'));
  assert.deepEqual(store.snapshot().agents[agent.id].work.tool,
    { name: 'read_file', callId: 'call', phase: 'start' });
  internal.observeAgent({ ...event(3, 'result'), session: undefined });
  assert.equal(store.snapshot().agents[agent.id].work.tool?.phase, 'start');
  internal.observeAgent(event(4, 'result'));
  assert.equal(store.snapshot().agents[agent.id].work.tool, null);
  assert.equal(JSON.stringify(store.snapshot()).includes('private'), false);
  observer.stop();
});

test('live scoped tool events map a running session when the list omits active run IDs', () => {
  const store = new FloorStore('fixture');
  const agent = normalizeSessionRow({ key: 'key', agentId: 'agent', sessionId: 's1',
    hasActiveRun: true, status: 'running' }, 'gateway', 100);
  assert.equal(agent.work.activeRunIds, null);
  store.replaceAgents([agent], true);
  const observer = new GatewayObserver({ gatewayId: 'gateway', gatewayUrl: 'ws://127.0.0.1:1',
    selectedAgentIds: ['agent'] }, store);
  const internal = observer as unknown as { observeAgent(value: unknown): void };
  const scoped = { ...event(2, 'start'), sessionId: 's1',
    session: { key: 'key', sessionId: 's1', agentId: 'agent', status: 'running' } };
  internal.observeAgent(scoped);
  assert.equal(store.snapshot().agents[agent.id].work.tool?.name, 'read_file');
  assert.equal(store.snapshot().agents[agent.id].freshness, 'fresh');
  internal.observeAgent({ ...event(3, 'result'), sessionId: 's1',
    session: { key: 'key', sessionId: 'replacement', agentId: 'agent', status: 'running' } });
  assert.equal(store.snapshot().agents[agent.id].work.tool?.phase, 'start');
  internal.observeAgent({ ...event(3, 'result'), sessionId: 's1',
    session: { key: 'key', sessionId: 's1', agentId: 'agent', status: 'running' } });
  assert.equal(store.snapshot().agents[agent.id].work.tool, null);
  observer.stop();
});
