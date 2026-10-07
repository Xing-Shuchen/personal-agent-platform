import assert from 'node:assert/strict';
import test from 'node:test';
import { ReadQuota } from '../../packages/openclaw-adapter/src/connection/read-quota.ts';

test('shared read quota caps concurrent requests and starts per second', async () => {
  const quota = new ReadQuota();
  let active = 0, peak = 0;
  const starts: number[] = [];
  await Promise.all(Array.from({ length: 11 }, () => quota.run(async () => {
    active++; peak = Math.max(peak, active); starts.push(Date.now());
    await new Promise(resolve => setTimeout(resolve, 12));
    active--;
  })));
  assert.ok(peak <= 4);
  assert.ok(starts[10] - starts[0] >= 950);
  quota.close();
});

test('read budget survives a reconnect inside the same one-second window', async () => {
  const first = new ReadQuota();
  await Promise.all(Array.from({ length: 10 }, () => first.run(async () => {})));
  const recent = first.recentStarts();
  first.close();
  const next = new ReadQuota(recent);
  const started = Date.now();
  await next.run(async () => {});
  assert.ok(Date.now() - started >= 750);
  next.close();
});
