import { Container, Graphics, Sprite } from 'pixi.js';
import type { TiledMapRenderer } from './TiledMapRenderer.ts';

/** Adapted from MD DeskScreen. The theme must explicitly supply licensed GIDs. */
export class DeskScreen {
  readonly container = new Container();
  private readonly anim = new Graphics();
  private on = false;
  private t = 0;
  constructor(map: TiledMapRenderer, tile: { x: number; y: number }, onGids: ReadonlyArray<readonly [number, number, number]>) {
    if (!onGids.length) throw new Error('missing monitor art');
    for (const [gid, dx, dy] of onGids) {
      const texture = map.textureForGid(gid);
      if (!texture) throw new Error('invalid monitor art');
      const sprite = new Sprite(texture);
      sprite.position.set(dx * map.tileSize, dy * map.tileSize);
      this.container.addChild(sprite);
    }
    this.container.addChild(this.anim);
    this.container.position.set(tile.x * map.tileSize, tile.y * map.tileSize);
    this.container.zIndex = (tile.y + 1) * map.tileSize - 1;
    this.container.eventMode = 'none';
    this.container.visible = false;
  }
  setOn(on: boolean): void {
    if (on === this.on) return;
    this.on = on;
    this.container.visible = on;
    if (!on) { this.anim.clear(); this.t = 0; }
  }
  update(dt: number): void {
    if (!this.on) return;
    this.t += dt;
    this.anim.clear();
    const y = 4 + Math.floor((this.t * 3) % 6);
    this.anim.rect(3, y, 8, 1).fill({ color: 0xcfe6ff, alpha: .7 });
    if (Math.floor(this.t / .53) % 2 === 0) this.anim.rect(3, 11, 2, 1).fill(0xffffff);
  }
  destroy(): void { this.container.destroy({ children: true }); }
}
