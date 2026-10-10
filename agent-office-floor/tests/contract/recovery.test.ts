import assert from 'node:assert/strict';
import test from 'node:test';
import { installContextLossRecovery, planInitFailure } from '../../packages/office-scene/src/scene/office/glRecovery.ts';
test('one graphics lifetime has a shared three-rebuild budget', () => {
  const budget = { used: 0 };
  let rebuilds = 0, gaveUp = 0;
  const scheduled: (() => void)[] = [];
  for (let i=0;i<4;i++) {
    const canvas = new EventTarget();
    const remove = installContextLossRecovery(canvas, { budget, onRebuild: () => rebuilds++, onGiveUp: () => gaveUp++, schedule: fn => { scheduled.push(fn); }, log: () => {} });
    const event = new Event('webglcontextlost', { cancelable: true });
    canvas.dispatchEvent(event);
    assert.equal(event.defaultPrevented, true);
    scheduled.shift()?.();
    remove();
  }
  assert.equal(rebuilds,3);
  assert.equal(gaveUp,1);
  assert.equal(budget.used,3);
});
test('context creation failures share the same budget', () => {
  const failure = new Error('Failed to create WebGL context');
  assert.deepEqual(planInitFailure(failure,2), { action:'retry', delayMs:1500, attempt:3 });
  assert.deepEqual(planInitFailure(failure,3), { action:'give-up' });
  assert.deepEqual(planInitFailure(new Error('missing atlas'),0), { action:'report' });
});
test('one lost context schedules only one rebuild despite repeated events', () => {
  const canvas = new EventTarget();
  const budget = { used: 0 };
  const scheduled: (() => void)[] = [];
  let rebuilds = 0;
  const remove = installContextLossRecovery(canvas, { budget, onRebuild: () => rebuilds++, schedule: fn => { scheduled.push(fn); }, log: () => {} });
  canvas.dispatchEvent(new Event('webglcontextlost', { cancelable: true }));
  canvas.dispatchEvent(new Event('webglcontextlost', { cancelable: true }));
  assert.equal(scheduled.length, 1);
  assert.equal(budget.used, 1);
  scheduled[0]();
  assert.equal(rebuilds, 1);
  remove();
});
