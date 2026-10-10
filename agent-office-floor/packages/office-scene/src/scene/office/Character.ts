import { Container, Graphics, Text, type Texture } from 'pixi.js';
import { CharacterSprite } from './CharacterSprite.ts';
import { ToolBubble } from './ToolBubble.ts';
import { ThoughtBubble } from './ThoughtBubble.ts';
import { findPath } from './pathfinding.ts';
import type { TiledMapRenderer } from './TiledMapRenderer.ts';
import type { VisualState } from '../../stateMapping/index.ts';

/** Browser-only adaptation of MD Character: identity and state are injected by the host. */
export class Character {
  readonly container = new Container();
  private readonly sprite: CharacterSprite;
  private readonly labels = new Container();
  private readonly effect = new Graphics();
  private readonly toolBubble = new ToolBubble();
  private readonly thoughtBubble = new ThoughtBubble();
  private toolName: string | null = null;
  private summary: string | null = null;
  private readonly map: TiledMapRenderer;
  private readonly seat: { x: number; y: number };
  private path: { x: number; y: number }[];
  private x: number;
  private y: number;
  private presentation: VisualState | null = null;
  private presentationKey = '';
  private successSeconds = 0;
  private stale = false;
  private reducedMotion = false;
  constructor(opts: { id: string; name: string; map: TiledMapRenderer; frames: Texture[][]; seat: { x: number; y: number }; entrance: { x: number; y: number }; startAtSeat?: boolean; onClick: (id: string) => void }) {
    this.map = opts.map; this.seat = opts.seat;
    const start = opts.startAtSeat ? opts.seat : opts.entrance;
    this.x = start.x * opts.map.tileSize + opts.map.tileSize / 2;
    this.y = start.y * opts.map.tileSize + opts.map.tileSize;
    this.path = opts.startAtSeat ? [] : findPath(opts.map, opts.entrance, opts.seat) ?? [];
    this.sprite = new CharacterSprite(opts.frames);
    this.container.addChild(this.sprite.container, this.labels, this.effect,
      this.toolBubble.container, this.thoughtBubble.container);
    this.container.eventMode = 'static'; this.container.cursor = 'pointer';
    this.container.on('pointertap', () => opts.onClick(opts.id));
    this.container.position.set(this.x, this.y);
    this.container.zIndex = this.y;
  }
  setPresentation(name: string, visual: VisualState, stale: boolean, selected: boolean): void {
    this.presentation = visual; this.stale = stale;
    this.sprite.setAlpha(stale ? .55 : 1);
    if (stale) this.resetTransient();
    this.sprite.setAnimation(stale ? 'idle' : this.path.length ? 'walk' : visual.animation,
      stale || this.path.length ? 'down' : visual.screenOn ? 'up' : 'down');
    this.sprite.setSeatedCrop(!this.path.length && visual.screenOn ? 8 : 0);
    const key = JSON.stringify([name, visual.label, visual.glyph, visual.color, stale, selected]);
    if (key === this.presentationKey) return;
    this.presentationKey = key;
    this.labels.removeChildren().forEach(child => child.destroy());
    if (selected) this.labels.addChild(new Graphics().roundRect(-21,-38,42,82,3).stroke({ color: 0x85d6bf, width: 1 }));
    if (visual.glyph) {
      const glyph = new Text({ text: visual.glyph, style: { fontFamily: 'system-ui,sans-serif', fontSize: 15, fill: '#ffffff', fontWeight: 'bold' } });
      glyph.anchor.set(.5); glyph.position.set(15,-43); this.labels.addChild(glyph);
    }
    const tag = new Text({ text: name, style: { fontFamily: 'system-ui,sans-serif', fontSize: 10,
      fill: '#e3edf3', fontWeight: 'bold', align: 'center', wordWrap: true,
      breakWords: true, wordWrapWidth: 84 } });
    tag.anchor.set(.5, 0); tag.position.set(0,4); this.labels.addChild(tag);
    const label = new Text({ text: visual.label, style: { fontFamily: 'system-ui,sans-serif', fontSize: 9, fill: `#${visual.color.toString(16).padStart(6,'0')}` } });
    label.anchor.set(.5); label.position.set(0, tag.y + tag.height + 6); this.labels.addChild(label);
  }
  setReducedMotion(reduced: boolean): void {
    if (this.reducedMotion === reduced) return;
    this.reducedMotion = reduced;
    this.sprite.setReducedMotion(reduced);
    this.toolBubble.setReducedMotion(reduced);
    this.thoughtBubble.setReducedMotion(reduced);
    if (reduced) {
      this.path = [];
      this.x = this.seat.x * this.map.tileSize + this.map.tileSize / 2;
      this.y = this.seat.y * this.map.tileSize + this.map.tileSize;
      this.container.position.set(this.x, this.y); this.container.zIndex = this.y;
      this.resetTransient();
    }
  }
  triggerSuccess(): void { if (!this.reducedMotion) this.successSeconds = .9; }
  setTool(name: string | null): void {
    if (this.toolName === name) return;
    this.toolName = name;
    if (name) {
      this.thoughtBubble.hide();
      this.toolBubble.showName(name);
      this.toolBubble.setPosition(0, 0);
      this.toolBubble.setReducedMotion(this.reducedMotion);
    } else {
      this.toolBubble.hide();
      this.showSummary();
    }
  }
  setSummary(summary: string | null): void {
    if (this.summary === summary) return;
    this.summary = summary;
    if (!this.toolName) this.showSummary();
  }
  private showSummary(): void {
    if (this.summary) {
      this.thoughtBubble.showSummary(this.summary);
      this.thoughtBubble.setPosition(0, 0);
      this.thoughtBubble.setReducedMotion(this.reducedMotion);
    } else this.thoughtBubble.hide();
  }
  resetTransient(): void { this.successSeconds = 0; this.effect.clear(); }
  update(dt: number): void {
    if (!this.reducedMotion) this.toolBubble.update(dt);
    if (!this.reducedMotion) this.thoughtBubble.update(dt);
    if (this.path.length && !this.stale) {
      const next = this.path[0], targetX = next.x * this.map.tileSize + this.map.tileSize / 2, targetY = next.y * this.map.tileSize + this.map.tileSize;
      const dx = targetX - this.x, dy = targetY - this.y, distance = Math.hypot(dx,dy), step = Math.max(0, Math.min(48 * dt, distance));
      if (distance > 0) { this.x += dx / distance * step; this.y += dy / distance * step; }
      if (distance <= step + .01) {
        this.x = targetX; this.y = targetY; this.path.shift();
        if (!this.path.length && this.presentation) {
          this.sprite.setAnimation(this.presentation.animation, this.presentation.screenOn ? 'up' : 'down');
          this.sprite.setSeatedCrop(this.presentation.screenOn ? 8 : 0);
        }
      }
      this.container.position.set(this.x, this.y); this.container.zIndex = this.y;
    }
    if (this.successSeconds > 0) {
      this.successSeconds = Math.max(0,this.successSeconds - dt);
      const alpha = this.successSeconds / .9;
      this.effect.clear().circle(0,-18,10 + (1-alpha)*12).stroke({ color: 0x72b1ef, alpha, width: 2 });
      if (!this.successSeconds) this.effect.clear();
    }
  }
  destroy(): void { this.container.destroy({ children: true }); }
}
