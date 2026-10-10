import assert from 'node:assert/strict';
import test from 'node:test';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { App } from '../../apps/web/src/App.tsx';
import { GatewayObserver } from '../../packages/openclaw-adapter/src/connection/observer.ts';
import { normalizeSessionRow } from '../../packages/openclaw-adapter/src/normalization/session.ts';
import { FloorStore } from '../../packages/openclaw-adapter/src/sessions/floor-store.ts';

test('one completed parallel run leaves the office figure working on the other run', () => {
  const store = new FloorStore('fixture');
  const agent = normalizeSessionRow({ key: 'fixture-key', agentId: 'fixture-agent',
    sessionId: 'fixture-instance', status: 'running', hasActiveRun: true,
    activeRunIds: ['r1', 'r2'] }, 'fixture', 100);
  store.replaceAgents([agent], true);
  const html = () => renderToStaticMarkup(React.createElement(App as React.ComponentType<{
    initialState: ReturnType<FloorStore['snapshot']>; transportDisabled: boolean;
  }>, { initialState: store.snapshot(), transportDisabled: true }));
  assert.match(html(), /运行中 · 2 个运行/);

  const observer = new GatewayObserver({ gatewayId: 'fixture', gatewayUrl: 'ws://127.0.0.1:1',
    selectedAgentIds: ['fixture-agent'] }, store);
  const admit = observer as unknown as { observeChatLifecycle(value: unknown): void };
  admit.observeChatLifecycle({ runId: 'r1', sessionKey: 'fixture-key', agentId: 'fixture-agent',
    seq: 0, state: 'final' });
  const current = store.snapshot().agents[agent.id];
  assert.deepEqual(current.work.activeRunIds, ['r2']);
  assert.equal(current.work.status, 'running');
  assert.equal(current.work.latestOutcome?.result, 'success');
  const after = html();
  assert.match(after, /运行中/);
  assert.doesNotMatch(after, /2 个运行/);
  assert.doesNotMatch(after, /<em>本轮已完成<\/em>/);
  observer.stop();
});
