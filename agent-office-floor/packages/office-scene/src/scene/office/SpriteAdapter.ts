import { Rectangle, Texture } from 'pixi.js';

/** Optional adapter for a separately supplied, licensed character sheet. */
export interface SpriteSheetConfig {
  readonly source: string;
  readonly license: string;
  readonly frameWidth: number;
  readonly frameHeight: number;
  readonly walkRow: number;
  readonly framesPerDirection: number;
  readonly groups: Readonly<{ down: number; up: number; right: number }>;
}

function nonnegativeInteger(value: number): boolean { return Number.isInteger(value) && value >= 0; }

/** Fail before making partial textures or accepting an unproven sheet layout. */
export function validateSpriteSheet(config: SpriteSheetConfig, width: number, height: number): void {
  if (!config.source.trim() || !config.license.trim()) throw new Error('sprite source and license required');
  if (![config.frameWidth, config.frameHeight, config.framesPerDirection, width, height].every(v => Number.isInteger(v) && v > 0) ||
      !nonnegativeInteger(config.walkRow) ||
      !Object.values(config.groups).every(nonnegativeInteger)) throw new Error('invalid sprite sheet geometry');
  if (config.framesPerDirection < 3) throw new Error('sprite sheet needs three walk frames per direction');
  const used = Object.values(config.groups);
  if (new Set(used).size !== 3) throw new Error('direction groups must be distinct');
  if ((Math.max(...used) + 1) * config.framesPerDirection * config.frameWidth > width ||
      (config.walkRow + 1) * config.frameHeight > height) throw new Error('sprite frames exceed sheet bounds');
}

/** Returns down/up/right rows of seven frames for CharacterSprite; caller owns them. */
export class SpriteAdapter {
  static extractFrames(sheet: Texture, config: SpriteSheetConfig): Texture[][] {
    const frame = sheet.frame;
    validateSpriteSheet(config, frame.width, frame.height);
    return (['down', 'up', 'right'] as const).map(direction => {
      const start = config.groups[direction] * config.framesPerDirection;
      const walk = [0, 1, 2].map(i => new Texture({ source: sheet.source,
        frame: new Rectangle(frame.x + (start + i) * config.frameWidth,
          frame.y + config.walkRow * config.frameHeight, config.frameWidth, config.frameHeight) }));
      return [...walk, walk[0], walk[0], walk[0], walk[0]];
    });
  }
}
