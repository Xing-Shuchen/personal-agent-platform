import assert from 'node:assert/strict';
import test from 'node:test';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import type { FloorState } from '@pap/floor-contract';
import { App } from '../../apps/web/src/App.tsx';
import { syntheticState } from '../../apps/web/src/synthetic.ts';

const RenderApp: React.ComponentType<{ initialState?: FloorState | null; transportDisabled?: boolean }> = App;

test('offline and revoked states clear current highlights without inventing a terminal result', () => {
  const initial: FloorState = syntheticState;
  const before = renderToStaticMarkup(React.createElement(RenderApp,
    { initialState: initial, transportDisabled: true }));
  assert.match(before, /OpenClaw 活动会话/);
  assert.match(before, /最新结束状态/);
  assert.match(before, /测试专员 1/);

  const stale: FloorState = { ...initial,
    connection: { ...initial.connection, state: 'offline', reason: 'test disconnect' },
    agents: Object.fromEntries(Object.entries(initial.agents).map(([id, agent]) =>
      [id, { ...agent, freshness: 'stale' as const }])) };
  const offline = renderToStaticMarkup(React.createElement(RenderApp,
    { initialState: stale, transportDisabled: true }));
  assert.match(offline, /测试专员 1/);
  assert.match(offline, /当前没有已确认的运行、等待或排队会话/);
  assert.match(offline, /没有可排序的已确认结束状态/);

  const revoked: FloorState = { ...initial, revision: initial.revision + 1,
    agents: {}, connection: { ...initial.connection, state: 'auth_required' as const,
      reason: 'test revocation' },
    capabilities: { ...initial.capabilities, sessionList: 'forbidden' as const } };
  const after = renderToStaticMarkup(React.createElement(RenderApp,
    { initialState: revoked, transportDisabled: true }));
  assert.match(after, /需要授权/);
  assert.doesNotMatch(after, /测试专员/);
  assert.match(after, /当前没有已确认的运行、等待或排队会话/);
  assert.match(after, /没有可排序的已确认结束状态/);
});
