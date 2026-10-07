import assert from 'node:assert/strict';
import test from 'node:test';
import { normalizeSessionRow } from '../../packages/openclaw-adapter/src/normalization/session.ts';
import { orderOfficeSessions } from '../../apps/web/src/session-order.ts';

test('office pages show distinct Feishu identities before repeating their sessions', () => {
  const rows = [
    normalizeSessionRow({ key: 'agent:a:old', agentId: 'a', lastActivityAt: 1 }, 'g', 3),
    normalizeSessionRow({ key: 'agent:a:new', agentId: 'a', lastActivityAt: 2 }, 'g', 3),
    normalizeSessionRow({ key: 'agent:b:one', agentId: 'b', lastActivityAt: 1 }, 'g', 3),
    normalizeSessionRow({ key: 'agent:c:one', agentId: 'c', lastActivityAt: 1 }, 'g', 3)
  ];
  assert.deepEqual(orderOfficeSessions(rows, ['b','a','c']).map(x => x.session.key),
    ['agent:b:one','agent:a:new','agent:c:one','agent:a:old']);
});
