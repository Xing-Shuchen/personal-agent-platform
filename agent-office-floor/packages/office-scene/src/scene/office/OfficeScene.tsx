import { useEffect, useRef, useState } from 'react';
import { Application, Container, UPDATE_PRIORITY, type Texture } from 'pixi.js';
import type { FloorState } from '@pap/floor-contract';
import { visualState } from '../../stateMapping/index.ts';
import { SuccessLedger } from '../../stateMapping/success.ts';
import { sceneName } from '../../stateMapping/identity.ts';
import { HandoffLedger } from '../../stateMapping/handoffs.ts';
import { loadThemeWithFallback, ownedOffice, type ThemeManifest } from '../../themes/theme.ts';
import { Camera } from './Camera.ts';
import { Character } from './Character.ts';
import { DeskScreen } from './DeskScreen.ts';
import { MessageEnvelope } from './MessageEnvelope.ts';
import { SeatPool } from './SeatPool.ts';
import { TiledMapRenderer } from './TiledMapRenderer.ts';
import { installContextLossRecovery, planInitFailure } from './glRecovery.ts';
import { getCastFrames } from './cast.ts';
import { recipeFor } from './appearance.ts';

const WIDTH = 768, HEIGHT = 480;
type Item = { seat: string; character: Character; screen: DeskScreen; sessionId: string | null; avatarKey: string; success: SuccessLedger };
type Props = { state: FloorState; ids: readonly string[]; selectedId: string | null; onSelect: (id: string) => void;
  pageKey?: number; theme?: ThemeManifest; onFrame?: (atMs: number, workMs: number, sceneEpoch: string, sceneRevision: number) => void };

/** Business data enters only through FloorState. Pixi owns graphics, not a Gateway connection. */
export function OfficeScene({ state, ids, selectedId, onSelect, pageKey = 0, theme = ownedOffice, onFrame }: Props) {
  const host = useRef<HTMLDivElement>(null);
  const app = useRef<Application | null>(null);
  const map = useRef<TiledMapRenderer | null>(null);
  const camera = useRef<Camera | null>(null);
  const seats = useRef<ReadonlyMap<string, { x: number; y: number }>>(new Map());
  const entrance = useRef({ x: 24, y: 5 });
  const pool = useRef(new SeatPool(ownedOffice.seats));
  const activeTheme = useRef<ThemeManifest>(ownedOffice);
  const roster = useRef(new Map<string, Item>());
  const handoffLedger = useRef(new HandoffLedger());
  const envelopes = useRef(new Map<string, { effect: MessageEnvelope; expiresAtMs: number;
    fromId: string; toId: string }>());
  const textures = useRef<readonly Texture[]>([]);
  const initialSyncDone = useRef(false);
  const latest = useRef({ state, ids, selectedId, onSelect, onFrame, pageKey });
  latest.current = { state, ids, selectedId, onSelect, onFrame, pageKey };
  const lastPageKey = useRef(pageKey);
  const lastSyncedState = useRef({ epoch: state.epoch, revision: -1 });
  const [error, setError] = useState<string | null>(null);
  const [generation, setGeneration] = useState(0);
  const recoveryBudget = useRef({ used: 0 });
  const reducedMotion = useRef(false);

  const removeEnvelope = (id: string) => {
    const active = envelopes.current.get(id);
    if (!active) return;
    map.current?.getCharacterContainer().removeChild(active.effect.container);
    active.effect.destroy();
    envelopes.current.delete(id);
  };
  const clearEnvelopes = () => {
    for (const id of [...envelopes.current.keys()]) removeEnvelope(id);
  };

  const sync = () => {
    const renderer = map.current;
    if (!renderer) return;
    const layer = renderer.getCharacterContainer();
    const { state: current, ids: visibleIds, selectedId: selected, pageKey: currentPageKey } = latest.current;
    const pageChanged = currentPageKey !== lastPageKey.current;
    const visibleAgents = visibleIds.map(id => current.agents[id]).filter((a): a is NonNullable<typeof a> => !!a);
    const visible = new Set(visibleAgents.map(a => a.id));
    for (const [id, item] of roster.current) if (!visible.has(id) || item.avatarKey !== current.agents[id]?.avatarKey) {
      layer.removeChild(item.character.container, item.screen.container);
      item.character.destroy(); item.screen.destroy(); pool.current.release(item.seat); roster.current.delete(id);
    }
    for (const id of visible) {
      const agent = current.agents[id];
      let item = roster.current.get(id);
      if (!item) {
        const seat = pool.current.reserveNext();
        if (!seat) continue;
        const point = seats.current.get(seat);
        if (!point) { pool.current.release(seat); continue; }
        const character = new Character({ id, name: agent.name, map: renderer,
          frames: getFrames(agent.avatarKey), seat: point, entrance: entrance.current,
          startAtSeat: reducedMotion.current || !initialSyncDone.current || pageChanged,
          onClick: clicked => latest.current.onSelect(clicked) });
        const screen = new DeskScreen(renderer,
          { x: point.x + activeTheme.current.monitor.offsetX, y: point.y + activeTheme.current.monitor.offsetY },
          [[activeTheme.current.monitor.onGid, 0, 0]]);
        layer.addChild(screen.container, character.container);
        item = { seat, character, screen, sessionId: agent.session.sessionId, avatarKey: agent.avatarKey, success: new SuccessLedger() };
        roster.current.set(id, item);
      }
      if (item.sessionId !== agent.session.sessionId) {
        item.character.resetTransient(); item.sessionId = agent.session.sessionId;
      }
      const visual = visualState(agent);
      item.character.setReducedMotion(reducedMotion.current);
      item.character.setPresentation(sceneName(agent, visibleAgents),
        reducedMotion.current && agent.work.status === 'completed' ? { ...visual, glyph: '✓' } : visual,
        agent.freshness !== 'fresh', id === selected);
      item.character.setTool(agent.freshness === 'fresh' && agent.work.status === 'running' ? agent.work.tool?.name ?? null : null);
      item.character.setSummary(agent.freshness === 'fresh' && agent.work.status === 'running' &&
        agent.work.summarySource ? agent.work.summary : null);
      item.screen.setOn(visual.screenOn);
      if (item.success.observe(agent)) item.character.triggerSuccess();
    }
    for (const [id, active] of envelopes.current) if (reducedMotion.current ||
      current.connection.state !== 'live' || !visible.has(active.fromId) || !visible.has(active.toId)) removeEnvelope(id);
    const arrivals = handoffLedger.current.take(current, visible, Date.now());
    if (!reducedMotion.current) for (const handoff of arrivals) {
      const from = roster.current.get(handoff.fromId)?.character.container;
      const to = roster.current.get(handoff.toId)?.character.container;
      if (!from || !to) continue;
      const effect = new MessageEnvelope({ x: from.x, y: from.y }, { x: to.x, y: to.y }, handoff.kind);
      layer.addChild(effect.container);
      envelopes.current.set(handoff.id, { effect, expiresAtMs: handoff.expiresAtMs,
        fromId: handoff.fromId, toId: handoff.toId });
    }
    initialSyncDone.current = true;
    lastPageKey.current = currentPageKey;
    const selectedSeat = selected ? roster.current.get(selected)?.seat : null;
    const selectedPoint = selectedSeat ? seats.current.get(selectedSeat) : null;
    if (selectedPoint) camera.current?.focusOn(selectedPoint.x * renderer.tileSize, selectedPoint.y * renderer.tileSize, 1.5);
    else camera.current?.fitToScreen();
    if (reducedMotion.current) camera.current?.snapToTarget();
    lastSyncedState.current = { epoch: current.epoch, revision: current.revision };
  };

  useEffect(() => {
    const element = host.current;
    if (!element) return;
    let disposed = false;
    let uninstallRecovery: (() => void) | null = null;
    let retryTimer: ReturnType<typeof setTimeout> | null = null;
    const motion = window.matchMedia?.('(prefers-reduced-motion: reduce)');
    reducedMotion.current = motion?.matches ?? false;
    const motionChange = () => { reducedMotion.current = motion?.matches ?? false; sync(); };
    motion?.addEventListener('change', motionChange);
    const instance = new Application();
    const start = async () => {
      try {
        const loaded = await loadThemeWithFallback(theme);
        if (disposed) { loaded.textures.forEach(t => t.destroy()); return; }
        textures.current = loaded.textures;
        await instance.init({ width: WIDTH, height: HEIGHT, background: '#172a38', antialias: false, preference: 'webgl' });
        // Effect cleanup already owns the loaded textures when init settles late.
        if (disposed) { instance.destroy(true); return; }
        app.current = instance;
        instance.canvas.style.width = '100%'; instance.canvas.style.height = 'auto';
        element.appendChild(instance.canvas);
        uninstallRecovery = installContextLossRecovery(instance.canvas, {
          budget: recoveryBudget.current, maxRebuilds: 3, delayMs: 1500,
          onRebuild: () => setGeneration(value => value + 1),
          onGiveUp: () => setError('图形恢复次数已耗尽'), log: () => {}
        });
        const world = new Container(); instance.stage.addChild(world);
        map.current = new TiledMapRenderer(loaded.map, [...loaded.textures]);
        world.addChild(map.current.getContainer());
        activeTheme.current = loaded.manifest;
        pool.current = new SeatPool(loaded.manifest.seats);
        seats.current = loaded.seats; entrance.current = loaded.entrance;
        camera.current = new Camera(world);
        camera.current.setMapSize(loaded.map.width * loaded.map.tilewidth, loaded.map.height * loaded.map.tileheight);
        camera.current.setViewSize(WIDTH, HEIGHT);
        const measuring = !!latest.current.onFrame;
        let frameStartedAt = 0;
        instance.ticker.add(ticker => {
          if (measuring) frameStartedAt = performance.now();
          if (reducedMotion.current) return;
          const dt = ticker.deltaMS / 1000;
          camera.current?.update(dt);
          for (const item of roster.current.values()) { item.character.update(dt); item.screen.update(dt); }
          for (const [id, active] of envelopes.current) if (Date.now() >= active.expiresAtMs || active.effect.update(dt)) removeEnvelope(id);
        });
        if (measuring) instance.ticker.add(() => latest.current.onFrame?.(performance.now(), performance.now() - frameStartedAt,
          lastSyncedState.current.epoch, lastSyncedState.current.revision),
          undefined, UPDATE_PRIORITY.UTILITY);
        if (document.hidden) instance.ticker.stop();
        handoffLedger.current.baseline(latest.current.state);
        sync();
      } catch (cause) {
        if (disposed) return;
        const plan = planInitFailure(cause, recoveryBudget.current.used, { maxRetries: 3, delayMs: 1500 });
        if (plan.action === 'retry') {
          recoveryBudget.current.used = plan.attempt;
          retryTimer = setTimeout(() => { if (!disposed) setGeneration(value => value + 1); }, plan.delayMs);
        } else {
          if (import.meta.env.DEV) console.error('Office scene initialization failed', cause);
          setError(plan.action === 'give-up' ? '图形恢复次数已耗尽' : '地图、图集或图形资源不可用');
        }
      }
    };
    void start();
    const visibility = () => { if (app.current) document.hidden ? app.current.ticker.stop() : app.current.ticker.start(); };
    document.addEventListener('visibilitychange', visibility);
    return () => {
      disposed = true; document.removeEventListener('visibilitychange', visibility);
      motion?.removeEventListener('change', motionChange);
      uninstallRecovery?.(); if (retryTimer) clearTimeout(retryTimer);
      clearEnvelopes();
      roster.current.clear(); pool.current = new SeatPool(ownedOffice.seats); activeTheme.current = ownedOffice; initialSyncDone.current = false;
      map.current = null; camera.current = null; seats.current = new Map();
      if (app.current === instance) app.current = null;
      try { instance.destroy(true, { children: true }); } catch { /* init may not have completed */ }
      textures.current.forEach(t => t.destroy()); textures.current = [];
    };
  }, [generation, theme]);
  useEffect(sync, [state, ids, selectedId, pageKey]);
  const retry = () => { recoveryBudget.current.used = 0; setError(null); setGeneration(value => value + 1); };
  return <div><div ref={host} className="office-canvas" aria-label="专员办公室像素场景" hidden={!!error} />{error && <div role="alert" className="scene-error">{error}。专员列表仍可查看状态。<button onClick={retry}>重试图形</button></div>}</div>;
}

function getFrames(avatarKey: string) {
  return getCastFrames(recipeFor(avatarKey));
}
