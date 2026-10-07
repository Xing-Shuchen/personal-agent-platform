import assert from 'node:assert/strict';
import test from 'node:test';
import { sceneFrameBufs } from '../../packages/office-scene/src/scene/office/portraitArt.ts';

test('eight original specialist recipes render distinct opaque scene frames', () => {
  const names = ['analyst', 'archivist', 'curator', 'scout', 'engineer', 'editor', 'planner', 'researcher'] as const;
  const frames = names.map(name => sceneFrameBufs(name).front[0]);
  for (const frame of frames) {
    assert.equal(frame.length, 18 * 32 * 4);
    assert.ok(frame.some((value, index) => index % 4 === 3 && value === 255));
  }
  const signatures = frames.map(frame => Buffer.from(frame).toString('base64'));
  assert.equal(new Set(signatures).size, names.length);
});
