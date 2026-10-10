import { Texture } from 'pixi.js';
import type { TiledMap, TiledLayer, TiledObject } from '../scene/office/TiledMapRenderer.ts';
import { findPath } from '../scene/office/pathfinding.ts';

const GID_MASK = 0x1fffffff;
export type TilePoint = Readonly<{ x: number; y: number }>;
export type ThemeManifest = Readonly<{
  id: string;
  mapUrl: string;
  tilesets: readonly Readonly<{ url: string; width: number; height: number }>[];
  seats: readonly string[];
  monitor: Readonly<{ offGid: number; onGid: number; offsetX: number; offsetY: number }>;
}>;
export type ValidatedTheme = Readonly<{ manifest: ThemeManifest; map: TiledMap; seats: ReadonlyMap<string, TilePoint>; entrance: TilePoint; textures: readonly Texture[] }>;

export const ownedOffice: ThemeManifest = {
  id: 'owned-office', mapUrl: '/office/map.tmj',
  tilesets: [{ url: '/office/tiles.svg', width: 64, height: 32 }],
  seats: Array.from({ length: 12 }, (_, i) => `desk-${i}`),
  monitor: { offGid: 5, onGid: 6, offsetX: 0, offsetY: -2 }
};

const tileLayer = (map: TiledMap, name: string): TiledLayer | undefined => map.layers.find(l => l.name === name && l.type === 'tilelayer');
const objects = (map: TiledMap, name: string): readonly TiledObject[] | undefined => map.layers.find(l => l.name === name && l.type === 'objectgroup')?.objects;
const positiveInt = (v: unknown): v is number => Number.isInteger(v) && Number(v) > 0;

/** Cheap metadata gate before requesting any atlas. */
export function validateThemeMetadata(map: TiledMap, manifest: ThemeManifest): void {
  if (!map || !positiveInt(map.width) || !positiveInt(map.height) || !positiveInt(map.tilewidth) || map.tileheight !== map.tilewidth || map.width > 256 || map.height > 256) throw new Error('invalid map dimensions');
  if (!Array.isArray(map.layers) || !Array.isArray(map.tilesets) || map.tilesets.length !== manifest.tilesets.length || !map.tilesets.length) throw new Error('invalid tileset count');
  for (const name of ['floor','walls','furniture-below','furniture-above','collision']) {
    const layer = tileLayer(map,name);
    if (!layer || !Array.isArray(layer.data) || layer.data.length !== map.width * map.height) throw new Error(`invalid ${name} layer`);
  }
}
/** Validate loaded atlas geometry, GIDs and seat reachability before scene commit. */
export function validateTheme(map: TiledMap, manifest: ThemeManifest, imageSizes: readonly TilePoint[]): { seats: ReadonlyMap<string, TilePoint>; entrance: TilePoint } {
  validateThemeMetadata(map, manifest);
  if (imageSizes.length !== map.tilesets.length) throw new Error('invalid tileset count');
  const ranges: { start: number; end: number }[] = [];
  for (let i=0;i<map.tilesets.length;i++) {
    const ref = map.tilesets[i], declared = manifest.tilesets[i], size = imageSizes[i];
    if (!positiveInt(ref.firstgid) || !positiveInt(ref.columns) || !positiveInt(ref.tilecount) || ref.tilewidth !== map.tilewidth || ref.tileheight !== map.tileheight ||
      size.x !== declared.width || size.y !== declared.height || size.x % map.tilewidth || size.y % map.tileheight || ref.columns !== size.x / map.tilewidth || ref.tilecount > (size.x / map.tilewidth) * (size.y / map.tileheight)) throw new Error('invalid tileset geometry');
    const range = { start: ref.firstgid, end: ref.firstgid + ref.tilecount - 1 };
    if (ranges.some(r => range.start <= r.end && range.end >= r.start)) throw new Error('overlapping tileset gids');
    ranges.push(range);
  }
  for (const name of ['floor','walls','furniture-below','furniture-above','collision']) {
    const layer = tileLayer(map,name);
    if (!layer || !Array.isArray(layer.data) || layer.data.length !== map.width * map.height || !layer.data.every(v => Number.isInteger(v) && v >= 0)) throw new Error(`invalid ${name} layer`);
    if (!layer.data.every(v => { const gid = v & GID_MASK; return gid === 0 || ranges.some(r => gid >= r.start && gid <= r.end); })) throw new Error(`out-of-range gid in ${name}`);
  }
  const entries = objects(map, 'spawn-points');
  if (!entries) throw new Error('missing spawn points');
  const points = new Map<string, TilePoint>();
  for (const item of entries) {
    if (!item.name || points.has(item.name) || !Number.isInteger(item.x) || !Number.isInteger(item.y) || item.x % map.tilewidth || item.y % map.tileheight) throw new Error('invalid or duplicate spawn point');
    const point = { x: item.x / map.tilewidth, y: item.y / map.tileheight };
    if (point.x < 0 || point.y < 0 || point.x >= map.width || point.y >= map.height) throw new Error('spawn point outside map');
    points.set(item.name, point);
  }
  const entrance = points.get('entrance');
  if (!entrance) throw new Error('missing entrance');
  if (!manifest.seats.length || new Set(manifest.seats).size !== manifest.seats.length) throw new Error('invalid seat manifest');
  const collision = tileLayer(map, 'collision')!.data!;
  const walkable = { width: map.width, height: map.height, isWalkable: (x: number,y: number) => x >= 0 && y >= 0 && x < map.width && y < map.height && (collision[y*map.width+x] & GID_MASK) === 0 };
  if (!walkable.isWalkable(entrance.x, entrance.y)) throw new Error('blocked entrance');
  const seats = new Map<string, TilePoint>();
  const positions = new Set<string>();
  const furniture = tileLayer(map, 'furniture-below')!.data!;
  if (!ranges.some(r => manifest.monitor.onGid >= r.start && manifest.monitor.onGid <= r.end)) throw new Error('invalid monitor on gid');
  for (const name of manifest.seats) {
    const point = points.get(name);
    if (!point) throw new Error(`missing seat ${name}`);
    const position = `${point.x},${point.y}`;
    if (positions.has(position) || !walkable.isWalkable(point.x, point.y) || findPath(walkable, entrance, point) === null) throw new Error(`unreachable or duplicate seat ${name}`);
    positions.add(position);
    const mx = point.x + manifest.monitor.offsetX, my = point.y + manifest.monitor.offsetY;
    if (mx < 0 || my < 0 || mx >= map.width || my >= map.height || (furniture[my*map.width+mx] & GID_MASK) !== manifest.monitor.offGid) throw new Error(`missing monitor for ${name}`);
    seats.set(name, point);
  }
  return { seats, entrance };
}

function loadImage(url: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const image = new Image();
    image.onload = () => resolve(image);
    image.onerror = () => reject(new Error('theme atlas unavailable'));
    image.src = url;
  });
}

/** Fetch, validate and load all resources as one transaction. Caller owns the returned textures. */
export async function loadTheme(manifest: ThemeManifest): Promise<ValidatedTheme> {
  const response = await fetch(manifest.mapUrl, { cache: 'no-store' });
  if (!response.ok) throw new Error('theme map unavailable');
  const map = await response.json() as TiledMap;
  validateThemeMetadata(map, manifest);
  const images = await Promise.all(manifest.tilesets.map(t => loadImage(t.url)));
  const checked = validateTheme(map, manifest, images.map(img => ({ x: img.naturalWidth, y: img.naturalHeight })));
  const textures: Texture[] = [];
  try {
    for (const image of images) {
      const canvas = document.createElement('canvas');
      canvas.width = image.naturalWidth; canvas.height = image.naturalHeight;
      const context = canvas.getContext('2d');
      if (!context) throw new Error('theme atlas rasterizer unavailable');
      context.drawImage(image, 0, 0);
      const texture = Texture.from(canvas);
      texture.source.scaleMode = 'nearest';
      textures.push(texture);
    }
  } catch (error) {
    textures.forEach(texture => texture.destroy());
    throw error;
  }
  return { manifest, map, textures, ...checked };
}

/** One authorized built-in fallback; the caller reports failure if it also fails. */
export async function loadThemeWithFallback(
  primary: ThemeManifest,
  fallback: ThemeManifest = ownedOffice,
  loader: (manifest: ThemeManifest) => Promise<ValidatedTheme> = loadTheme
): Promise<ValidatedTheme> {
  if (primary === fallback) return loader(primary);
  try { return await loader(primary); }
  catch { return loader(fallback); }
}
