import assert from 'node:assert/strict';
import test from 'node:test';
import { splitOccurrences, type Occurrence } from '../../apps/web/src/PapTasks.tsx';

test('a cached PAP forecast tracks the viewer clock and keeps every column ordered', () => {
  const now = Date.parse('2026-10-04T08:00:00Z');
  const occurrence = (key: string, minutes: number, enabled: boolean): Occurrence => ({
    key, agentId: 'agent', name: key, timezone: 'UTC', enabled,
    nominalAt: new Date(now + minutes * 60000).toISOString(),
    dispatchAt: new Date(now + minutes * 60000).toISOString()
  });
  const cached = [occurrence('later', 61, true), occurrence('disabled2', 90, false),
    occurrence('soon2', 60, true), occurrence('past', -1, true),
    occurrence('disabled1', 30, false), occurrence('soon1', 10, true)];
  const first = splitOccurrences(cached, now);
  assert.deepEqual(first.soon.map(item => item.key), ['soon1', 'soon2']);
  assert.deepEqual(first.later.map(item => item.key), ['later']);
  assert.deepEqual(first.disabled.map(item => item.key), ['disabled1', 'disabled2']);
  const advanced = splitOccurrences(cached, now + 31 * 60000);
  assert.deepEqual(advanced.soon.map(item => item.key), ['soon2', 'later']);
  assert.deepEqual(advanced.disabled.map(item => item.key), ['disabled2']);
});
