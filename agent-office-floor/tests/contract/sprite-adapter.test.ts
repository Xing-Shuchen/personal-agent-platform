import assert from 'node:assert/strict';
import test from 'node:test';
import { validateSpriteSheet, type SpriteSheetConfig } from '../../packages/office-scene/src/scene/office/SpriteAdapter.ts';

const config: SpriteSheetConfig = { source: 'example owned sheet', license: 'example license',
  frameWidth: 18, frameHeight: 32, walkRow: 1, framesPerDirection: 6, groups: { down: 3, up: 1, right: 0 } };
test('optional sheet requires provenance, distinct directions and full bounds', () => {
  assert.doesNotThrow(() => validateSpriteSheet(config, 432, 64));
  assert.throws(() => validateSpriteSheet({ ...config, license: '' }, 432, 64));
  assert.throws(() => validateSpriteSheet({ ...config, groups: { down: 0, up: 0, right: 1 } }, 432, 64));
  assert.throws(() => validateSpriteSheet(config, 400, 64));
  assert.throws(() => validateSpriteSheet(config, 432, 63));
});
