import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import type { TiledMap } from '../../packages/office-scene/src/scene/office/TiledMapRenderer.ts';
import { loadThemeWithFallback, ownedOffice, validateTheme } from '../../packages/office-scene/src/themes/theme.ts';
const map = JSON.parse(readFileSync(new URL('../../assets/owned/office/map.tmj', import.meta.url), 'utf8')) as TiledMap;
const sizes = [{ x: 64, y: 32 }];
const copy = (): TiledMap => structuredClone(map);

test('owned office atlas, collision, monitors and twelve reachable seats validate', () => {
  const result = validateTheme(copy(), ownedOffice, sizes);
  assert.equal(result.seats.size, 12);
  assert.deepEqual(result.entrance, { x: 24, y: 5 });
});
test('theme transaction rejects missing art, bad gid, duplicate and unreachable seats', () => {
  assert.throws(() => validateTheme(copy(), ownedOffice, [{ x: 32, y: 32 }]), /tileset geometry/);
  const gid = copy(); gid.layers[0].data![0] = 999;
  assert.throws(() => validateTheme(gid, ownedOffice, sizes), /out-of-range gid/);
  const duplicate = copy(); duplicate.layers.find(l => l.name === 'spawn-points')!.objects![1].name = 'entrance';
  assert.throws(() => validateTheme(duplicate, ownedOffice, sizes), /duplicate spawn/);
  const blocked = copy(); const collision = blocked.layers.find(l => l.name === 'collision')!.data!; collision[9*48+6] = 1;
  assert.throws(() => validateTheme(blocked, ownedOffice, sizes), /unreachable or duplicate seat/);
});

test('custom theme failure tries the owned theme once; owned failure does not loop', async () => {
  const custom = { ...ownedOffice, id: 'custom', mapUrl: '/custom/map.tmj' };
  const seen: string[] = [];
  const checked = validateTheme(copy(), ownedOffice, sizes);
  const loaded = { manifest: ownedOffice, map, textures: [], ...checked };
  const result = await loadThemeWithFallback(custom, ownedOffice, async manifest => {
    seen.push(manifest.id);
    if (manifest === custom) throw new Error('broken custom map');
    return loaded;
  });
  assert.equal(result, loaded);
  assert.deepEqual(seen, ['custom', 'owned-office']);
  seen.length = 0;
  await assert.rejects(loadThemeWithFallback(ownedOffice, ownedOffice, async manifest => {
    seen.push(manifest.id); throw new Error('missing default atlas');
  }), /missing default atlas/);
  assert.deepEqual(seen, ['owned-office']);
});
