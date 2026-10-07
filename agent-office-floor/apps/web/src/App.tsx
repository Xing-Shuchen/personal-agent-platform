import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { isFloorState } from '@pap/floor-contract';
import type { CapabilityState, FloorAgent, FloorState, FloorUpdate } from '@pap/floor-contract';
import { OfficeScene, opaqueSessionCues, visualState } from '@pap/office-scene';
import { admitHttpSnapshot, admitStreamUpdate } from './transport.ts';
import { PapTasks } from './PapTasks.tsx';
import { orderOfficeSessions } from './session-order.ts';
import { requireViewer } from './viewer-access.ts';
import { visibleEventReceiptAt } from './event-latency.ts';

type OfficeIdentity = { id: string; name: string; hasFeishuApp: boolean };
type SubscriptionCoverage = { target: number; leased: number; queuedReads: number; syncing: boolean; unsupported: boolean };
function isIdentityList(value: unknown): value is OfficeIdentity[] {
  return Array.isArray(value) && value.length <= 100 && value.every(x => x && typeof x === 'object' &&
    typeof x.id === 'string' && typeof x.name === 'string' && typeof x.hasFeishuApp === 'boolean');
}
function isSubscriptionCoverage(value: unknown): value is SubscriptionCoverage {
  if (!value || typeof value !== 'object') return false;
  const v = value as Record<string, unknown>;
  return Number.isSafeInteger(v.target) && Number(v.target) >= 0 &&
    Number.isSafeInteger(v.leased) && Number(v.leased) >= 0 && Number(v.leased) <= Number(v.target) &&
    Number.isSafeInteger(v.queuedReads) && Number(v.queuedReads) >= 0 &&
    typeof v.syncing === 'boolean' && typeof v.unsupported === 'boolean';
}

function date(ms: number | null): string { return ms === null ? '未提供' : new Date(ms).toLocaleString('zh-CN'); }
function status(agent: FloorAgent): string {
  const base = visualState(agent).label;
  const active = agent.work.activeRunIds?.length;
  const direct = active && active > 1 ? `${base} · ${active} 个运行` : base;
  const children = agent.relation.runningVisibleChildren;
  return agent.freshness === 'fresh' && children && children > 0 ? `${direct} · ${children} 个子会话运行中` : direct;
}
function capability(state: CapabilityState | undefined): string {
  return state === 'available' ? '已验证' : state === 'partial' ? '覆盖不完整' :
    state === 'forbidden' ? '无读取权限' : state === 'unsupported' ? '不支持' : '尚未验证';
}
const capabilityLabels = {
  sessionList: '会话列表', sessionEvents: '会话订阅', runEvents: '运行事件',
  toolEvents: '工具事件', blockingInput: '等待输入', progressCard: '进度卡',
  compaction: '上下文整理', loopDetection: '循环告警', handoff: '会话通信'
} as const;
function ProgressDetail({ agent, coverage }: { agent: FloorAgent; coverage: CapabilityState | undefined }) {
  const card = agent.progress;
  if (!card) return <>{coverage === 'available' ? '当前未提供' : capability(coverage)}</>;
  return <div className="progress-detail">
    <span>{card.steps ? `${card.steps.filter(step => step.status === 'completed').length}/${card.steps.length} 步` : '无步骤'} · {date(card.updatedAtMs)}</span>
    {card.steps?.length ? <ol>{card.steps.map((step, i) => <li key={i}>{step.status === 'completed' ? '✓' : step.status === 'in_progress' ? '◐' : '○'} {step.text}</li>)}</ol> : null}
    {card.markdown ? <p className="progress-note">{card.markdown}</p> : null}
  </div>;
}
export function App({ initialState = null, transportDisabled = false, onSceneFrame }: {
  initialState?: FloorState | null; transportDisabled?: boolean; onSceneFrame?: (atMs: number, workMs: number) => void;
} = {}) {
  const measure = typeof window !== 'undefined' && new URLSearchParams(window.location.search).get('measure') === '1';
  const [state, setState] = useState<FloorState | null>(initialState);
  const stateRef = useRef<FloorState | null>(initialState);
  const [transport, setTransport] = useState<'sse'|'polling'|'offline'>(transportDisabled ? 'sse' : 'offline');
  const [selectedId, select] = useState<string | null>(null);
  const sceneIdsRef = useRef<ReadonlySet<string>>(new Set());
  const [page, setPage] = useState(0);
  const [rosterQuery, setRosterQuery] = useState('');
  const [rosterPage, setRosterPage] = useState(0);
  const [identities, setIdentities] = useState<OfficeIdentity[]>([]);
  const [subscriptionCoverage, setSubscriptionCoverage] = useState<SubscriptionCoverage | null>(null);
  const pendingLatency = useRef<{ epoch: string; revision: number; generatedAtMs: number; receivedAtMs: number } | null>(null);
  const pendingSceneEvent = useRef<{ epoch: string; revision: number; receivedAtMs: number } | null>(null);
  const latencySamples = useRef<{ total: number; transit: number; render: number }[]>([]);
  const eventLatencySamples = useRef<number[]>([]);
  const [sceneEventLatency, setSceneEventLatency] = useState<{ p95Ms: number; count: number } | null>(null);
  const [acceptedPatches, setAcceptedPatches] = useState(0);
  const sampledPatches = useRef(0);
  const sceneFrameSample = useRef({ startedAtMs: 0, measuredAtMs: 0, frames: 0, workMs: 0, finished: false });
  const [sceneFrameResult, setSceneFrameResult] = useState<{ fps: number; averageWorkMs: number; seconds: number } | null>(null);
  const observeSceneFrame = useCallback((atMs: number, workMs: number, sceneEpoch: string, sceneRevision: number) => {
    if (!measure) return;
    const event = pendingSceneEvent.current;
    if (document.hidden) pendingSceneEvent.current = null;
    else if (event && event.epoch === sceneEpoch && event.revision === sceneRevision) {
      pendingSceneEvent.current = null;
      const elapsed = Date.now() - event.receivedAtMs;
      if (elapsed >= 0 && elapsed <= 10000) {
        const samples = eventLatencySamples.current;
        samples.push(elapsed);
        if (samples.length > 100) samples.shift();
        const ordered = [...samples].sort((a, b) => a - b);
        setSceneEventLatency({ p95Ms: ordered[Math.ceil(ordered.length * .95) - 1], count: samples.length });
      }
    } else if (event && (event.epoch !== sceneEpoch || sceneRevision > event.revision))
      pendingSceneEvent.current = null;
    const sample = sceneFrameSample.current;
    if (sample.finished) return;
    if (document.hidden) {
      sample.startedAtMs = 0; sample.measuredAtMs = 0; sample.frames = 0; sample.workMs = 0;
      return;
    }
    if (!sample.startedAtMs) sample.startedAtMs = atMs;
    if (atMs - sample.startedAtMs < 3000) return;
    if (!sample.measuredAtMs) sample.measuredAtMs = atMs;
    sample.frames++;
    sample.workMs += workMs;
    if (atMs - sample.measuredAtMs >= 30000) {
      sample.finished = true;
      setSceneFrameResult({ fps: sample.frames * 1000 / (atMs - sample.measuredAtMs),
        averageWorkMs: sample.workMs / sample.frames, seconds: (atMs - sample.measuredAtMs) / 1000 });
    }
  }, [measure]);
  const [latency, setLatency] = useState<{ p95Ms: number; transitP95Ms: number; renderP95Ms: number;
    count: number; totalCount: number } | null>(null);
  useEffect(() => {
    if (!measure) return;
    const visibility = () => {
      if (!document.hidden) return;
      const sample = sceneFrameSample.current;
      if (!sample.finished) {
        sample.startedAtMs = 0; sample.measuredAtMs = 0; sample.frames = 0; sample.workMs = 0;
      }
      pendingLatency.current = null;
      pendingSceneEvent.current = null;
    };
    document.addEventListener('visibilitychange', visibility);
    return () => document.removeEventListener('visibilitychange', visibility);
  }, [measure]);
  useEffect(() => {
    if (!measure || !state || document.hidden) return;
    const pending = pendingLatency.current;
    if (!pending || pending.epoch !== state.epoch || pending.revision !== state.revision) return;
    pendingLatency.current = null;
    const frame = requestAnimationFrame(() => {
      if (document.hidden) return;
      const frameCallbackAtMs = Date.now();
      const elapsed = frameCallbackAtMs - pending.generatedAtMs;
      if (elapsed < 0 || elapsed > 10000 || pending.receivedAtMs < pending.generatedAtMs) return;
      const samples = latencySamples.current;
      samples.push({ total: elapsed, transit: pending.receivedAtMs - pending.generatedAtMs,
        render: frameCallbackAtMs - pending.receivedAtMs });
      sampledPatches.current++;
      if (samples.length > 100) samples.shift();
      const p95 = (field: 'total' | 'transit' | 'render') =>
        [...samples].map(sample => sample[field]).sort((a, b) => a - b)[Math.ceil(samples.length * .95) - 1];
      setLatency({ p95Ms: p95('total'), transitP95Ms: p95('transit'),
        renderP95Ms: p95('render'), count: samples.length, totalCount: sampledPatches.current });
    });
    return () => cancelAnimationFrame(frame);
  }, [measure, state?.epoch, state?.revision]);
  useEffect(() => {
    if (transportDisabled) return;
    const controller = new AbortController();
    void fetch('/api/floor/identities', { cache: 'no-store', signal: controller.signal })
      .then(response => requireViewer(response).ok ? response.json() : null)
      .then((value: unknown) => { if (!controller.signal.aborted && isIdentityList(value)) setIdentities(value); })
      .catch(() => {});
    return () => controller.abort();
  }, [transportDisabled]);
  useEffect(() => {
    if (transportDisabled) return;
    let disposed = false, timer: number | null = null;
    let requestId = 0;
    const refresh = async () => {
      const current = ++requestId;
      try {
        const response = await fetch('/api/floor/coverage', { cache: 'no-store' });
        const value: unknown = requireViewer(response).ok ? await response.json() : null;
        if (!disposed && current === requestId) setSubscriptionCoverage(isSubscriptionCoverage(value) ? value : null);
      } catch { if (!disposed && current === requestId) setSubscriptionCoverage(null); }
      if (!disposed && current === requestId) timer = window.setTimeout(refresh, document.hidden ? 15000 : 5000);
    };
    const visibility = () => {
      if (timer !== null) clearTimeout(timer);
      timer = null;
      if (!document.hidden) void refresh();
      else { ++requestId; timer = window.setTimeout(refresh, 15000); }
    };
    document.addEventListener('visibilitychange', visibility);
    void refresh();
    return () => { disposed = true; ++requestId; if (timer !== null) clearTimeout(timer);
      document.removeEventListener('visibilitychange', visibility); };
  }, [transportDisabled]);
  useEffect(() => {
    if (transportDisabled) return;
    const id = crypto.randomUUID();
    const report = (visible: boolean) => {
      void fetch('/api/floor/view', { method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id, visible }), keepalive: true }).then(requireViewer).catch(() => {});
    };
    const visibility = () => report(!document.hidden);
    const leave = () => report(false);
    report(!document.hidden);
    document.addEventListener('visibilitychange', visibility);
    window.addEventListener('pagehide', leave);
    const heartbeat = window.setInterval(() => { if (!document.hidden) report(true); }, 15000);
    return () => { clearInterval(heartbeat); document.removeEventListener('visibilitychange', visibility);
      window.removeEventListener('pagehide', leave); report(false); };
  }, [transportDisabled]);
  useEffect(() => {
    if (transportDisabled) return;
    let disposed = false, source: EventSource | null = null, timer: number | null = null,
      watchdog: number | null = null, reconnectTimer: number | null = null;
    let failures = 0, lastPulse = Date.now(), polling = false, streamLive = false, streamSerial = 0;
    let snapshotPending: Promise<void> | null = null, snapshotAgain = false;
    const update = (raw: unknown) => {
      if (!raw || typeof raw !== 'object' || !('type' in raw)) return;
      try {
        const next = admitStreamUpdate(stateRef.current, raw as FloorUpdate);
        if (measure && !document.hidden && (raw as FloorUpdate).type === 'patch') {
          const patch = raw as Extract<FloorUpdate, { type: 'patch' }>;
          const eventReceivedAtMs = visibleEventReceiptAt(stateRef.current, patch, sceneIdsRef.current);
          pendingLatency.current = {
            epoch: next.epoch, revision: next.revision,
            generatedAtMs: patch.generatedAtMs,
            receivedAtMs: Date.now()
          };
          if (eventReceivedAtMs !== null)
            pendingSceneEvent.current = { epoch: next.epoch, revision: next.revision, receivedAtMs: eventReceivedAtMs };
          setAcceptedPatches(count => count + 1);
        }
        stateRef.current = next;
        setState(next);
      } catch { void fetchSnapshot(); }
    };
    const fetchSnapshot = (): Promise<void> => {
      if (snapshotPending) { snapshotAgain = true; return snapshotPending; }
      snapshotPending = (async () => {
        const requestEpoch = stateRef.current?.epoch ?? null;
        try {
          const response = await fetch('/api/floor/state', { cache: 'no-store' });
          requireViewer(response);
          const value: unknown = await response.json();
          if (!disposed && response.ok && isFloorState(value)) {
            if (!polling && source && stateRef.current?.epoch === requestEpoch && value.epoch !== requestEpoch)
              restartStream();
            const next = admitHttpSnapshot(stateRef.current, value, requestEpoch);
            stateRef.current = next;
            setState(next);
            if (polling) setTransport('polling');
          }
          else if (!disposed && !streamLive) setTransport('offline');
        } catch { if (!disposed && !streamLive) setTransport('offline'); }
      })().finally(() => {
        snapshotPending = null;
        if (snapshotAgain && !disposed) { snapshotAgain = false; void fetchSnapshot(); }
      });
      return snapshotPending;
    };
    const pollTick = () => {
      void fetchSnapshot();
      timer = window.setTimeout(pollTick, document.hidden ? 15000 : 2000);
    };
    const poll = () => {
      if (polling) return;
      polling = true;
      streamLive = false;
      streamSerial++;
      if (watchdog !== null) { clearInterval(watchdog); watchdog = null; }
      source?.close(); source = null; setTransport('polling');
      pollTick();
    };
    const connect = () => {
      const serial = ++streamSerial;
      source = new EventSource('/api/floor/events');
      source.addEventListener('floor', event => {
        if (disposed || serial !== streamSerial) return;
        try { update(JSON.parse((event as MessageEvent).data)); lastPulse = Date.now(); streamLive = true;
          failures = 0; setTransport('sse'); }
        catch { void fetchSnapshot(); }
      });
      source.addEventListener('heartbeat', () => { if (serial === streamSerial) {
        lastPulse = Date.now(); streamLive = true; if (stateRef.current) setTransport('sse');
      } });
      source.onerror = () => {
        if (disposed || serial !== streamSerial || !source) return;
        failures++;
        streamLive = false;
        setTransport('offline');
        if (failures === 1 && stateRef.current) void fetchSnapshot();
        source?.close(); source = null;
        if (watchdog !== null) { clearInterval(watchdog); watchdog = null; }
        if (failures >= 3) poll();
        else reconnectTimer = window.setTimeout(() => {
          reconnectTimer = null;
          if (!disposed && serial === streamSerial) connect();
        }, 1000 * failures);
      };
      watchdog = window.setInterval(() => {
        if (serial !== streamSerial) return;
        if (Date.now() - lastPulse > 45000) { setTransport('offline'); source?.close(); poll(); }
      }, 5000);
    };
    const restartStream = () => {
      if (disposed || polling) return;
      source?.close();
      if (watchdog !== null) clearInterval(watchdog);
      if (reconnectTimer !== null) { clearTimeout(reconnectTimer); reconnectTimer = null; }
      source = null; watchdog = null; failures = 0; lastPulse = Date.now();
      streamLive = false;
      connect();
    };
    const visibility = () => {
      if (disposed) return;
      if (document.hidden) {
        if (polling && timer !== null) {
          clearTimeout(timer);
          timer = window.setTimeout(pollTick, 15000);
        }
        return;
      }
      if (polling) {
        polling = false;
        if (timer !== null) { clearTimeout(timer); timer = null; }
        if (reconnectTimer !== null) { clearTimeout(reconnectTimer); reconnectTimer = null; }
        failures = 0; lastPulse = Date.now();
        streamLive = false;
        connect();
      }
      void fetchSnapshot();
    };
    document.addEventListener('visibilitychange', visibility);
    connect();
    void fetchSnapshot();
    return () => { disposed = true; streamSerial++; document.removeEventListener('visibilitychange', visibility);
      source?.close(); if (timer !== null) clearTimeout(timer); if (watchdog !== null) clearInterval(watchdog);
      if (reconnectTimer !== null) clearTimeout(reconnectTimer); };
  }, [transportDisabled, measure]);
  const displayState = useMemo(() => state && transport === 'offline' ? { ...state, agents: Object.fromEntries(Object.entries(state.agents).map(([id,a]) => [id, { ...a, freshness: 'stale' as const }])) } : state, [state, transport]);
  const agents = useMemo(() => orderOfficeSessions(Object.values(displayState?.agents ?? {}),
    identities.map(identity => identity.id)), [displayState, identities]);
  const sessionCues = useMemo(() => opaqueSessionCues(agents), [agents]);
  const activeAgents = useMemo(() => agents.filter(agent => agent.freshness === 'fresh' &&
    ['running', 'waiting_input', 'queued'].includes(agent.work.status)), [agents]);
  const recentOutcomes = useMemo(() => agents.filter(agent => agent.freshness === 'fresh' &&
    agent.work.latestOutcome && ['completed', 'error', 'stopped'].includes(agent.work.status) &&
    (agent.metadataUpdatedAtMs !== null || agent.lastActivityAtMs !== null))
    .sort((a, b) => (b.metadataUpdatedAtMs ?? b.lastActivityAtMs ?? 0) -
      (a.metadataUpdatedAtMs ?? a.lastActivityAtMs ?? 0)).slice(0, 8), [agents]);
  const matchingAgents = useMemo(() => {
    const needle = rosterQuery.trim().toLocaleLowerCase();
    return needle ? agents.filter(agent =>
      [agent.name, agent.session.agentId, sessionCues.get(agent.id)].some(value =>
        value?.toLocaleLowerCase().includes(needle))) : agents;
  }, [agents, rosterQuery, sessionCues]);
  const rosterPages = Math.max(1, Math.ceil(matchingAgents.length / 50));
  const activeRosterPage = Math.min(rosterPage, rosterPages - 1);
  const rosterAgents = matchingAgents.slice(activeRosterPage * 50, (activeRosterPage + 1) * 50);
  const pages = Math.max(1, Math.ceil(agents.length / 12));
  const activePage = Math.min(page, pages - 1);
  const ids = agents.slice(activePage * 12, (activePage + 1) * 12).map(a => a.id);
  sceneIdsRef.current = new Set(ids);
  const selectAgent = (id: string) => {
    select(id);
    const index = agents.findIndex(agent => agent.id === id);
    if (index >= 0) setPage(Math.floor(index / 12));
    const rosterIndex = matchingAgents.findIndex(agent => agent.id === id);
    if (rosterIndex >= 0) setRosterPage(Math.floor(rosterIndex / 50));
  };
  const selected = selectedId ? displayState?.agents[selectedId] ?? null : null;
  useEffect(() => {
    if (transportDisabled || !selected || state?.capabilities.progressCard === 'unsupported') return;
    let disposed = false, timer: number | null = null;
    const refresh = () => {
      if (disposed) return;
      if (timer !== null) clearTimeout(timer);
      void fetch(`/api/floor/progress?id=${encodeURIComponent(selected.id)}`, { cache: 'no-store' }).then(requireViewer).catch(() => {});
      timer = window.setTimeout(refresh, document.hidden ? 15000 : 5000);
    };
    const visibility = () => {
      if (timer !== null) clearTimeout(timer);
      timer = null;
      if (document.hidden) timer = window.setTimeout(refresh, 15000);
      else refresh();
    };
    document.addEventListener('visibilitychange', visibility);
    refresh();
    return () => { disposed = true; document.removeEventListener('visibilitychange', visibility);
      if (timer !== null) clearTimeout(timer); };
  }, [selected?.id, selected?.session.sessionId, state?.capabilities.progressCard, transportDisabled]);
  const connection = state?.connection;
  return <main className="office-app">
    <header><div><span className="eyebrow">OPENCLAW · OBSERVER</span><h1>专员办公室</h1><p>只读会话观察面</p></div><div className="connection"><strong>{connection?.state === 'auth_required' ? '需要授权' : connection?.state === 'offline' ? 'Gateway 离线' : connection?.state === 'degraded' ? '状态受限' : connection?.state === 'live' ? connection.mode === 'polling' ? '轮询模式' : '实时订阅' : '正在连接'}</strong><span>页面传输：{transport === 'sse' ? 'SSE' : transport === 'polling' ? '快照轮询' : '未连接'}</span>{connection?.reason && <span>{connection.reason}</span>}<a href="#pap-tasks">查看 PAP 运行与计划 ↓</a></div></header>
    <section className="layout"><div className="scene-panel"><div className="panel-head"><h2>办公室</h2><span>{agents.length} 个会话 · 第 {activePage + 1}/{pages} 页</span></div>{state ? <OfficeScene state={displayState!} ids={ids} selectedId={selectedId} onSelect={selectAgent} pageKey={activePage} onFrame={onSceneFrame ?? (measure ? observeSceneFrame : undefined)} /> : <div className="loading">正在连接…</div>}<div className="pager"><button disabled={activePage === 0} onClick={() => setPage(activePage - 1)}>上一页</button><span>每页最多 12 个工位</span><button disabled={activePage >= pages - 1} onClick={() => setPage(activePage + 1)}>下一页</button></div></div>
    <aside className="sidebar"><div className="panel-head"><h2>OpenClaw 专员身份</h2><span>{identities.length}</span></div>{identities.length ? <ul className="identity-roster">{identities.map(identity => { const sessions = agents.filter(agent => agent.session.agentId === identity.id); return <li key={identity.id}><span><strong>{identity.name}</strong><small>{identity.id}</small></span><span className="identity-meta">{identity.hasFeishuApp ? <b>飞书 App</b> : null}{sessions.length ? `${sessions.length} 个会话` : '暂无会话'}</span></li>; })}</ul> : <p className="empty">{transportDisabled ? '测试画面' : '正在读取专员身份…'}</p>}
    <section className="active-sessions" aria-label="OpenClaw 活动会话"><div className="panel-head"><h2>OpenClaw 活动会话</h2><span>{activeAgents.length}</span></div>{activeAgents.length ? <ul className="roster">{activeAgents.map(a => <li key={a.id}><button className={a.id === selectedId ? 'selected' : ''} onClick={() => selectAgent(a.id)}><span className="dot" data-status={a.work.status} /><span><strong>{a.name}</strong><small>会话 · {sessionCues.get(a.id)}</small></span><em>{status(a)}</em></button></li>)}</ul> : <p className="empty">当前没有已确认的运行、等待或排队会话。</p>}</section>
    <section className="recent-outcomes" aria-label="OpenClaw 最新结束状态"><div className="panel-head"><h2>最新结束状态</h2><span>最近更新的 {recentOutcomes.length} 条</span></div>{recentOutcomes.length ? <ul className="roster">{recentOutcomes.map(a => <li key={a.id}><button className={a.id === selectedId ? 'selected' : ''} onClick={() => selectAgent(a.id)}><span className="dot" data-status={a.work.status} /><span><strong>{a.name}</strong><small>记录更新 · {date(a.metadataUpdatedAtMs ?? a.lastActivityAtMs)}</small></span><em>{status(a)}</em></button></li>)}</ul> : <p className="empty">没有可排序的已确认结束状态。</p>}</section>
    <div className="panel-head"><h2>会话列表</h2><span>{agents.length}</span></div><div className="roster-filter"><input aria-label="搜索会话" placeholder="搜索专员或会话" value={rosterQuery} onChange={event => { setRosterQuery(event.target.value); setRosterPage(0); }} /></div>{rosterAgents.length ? <ul className="roster">{rosterAgents.map(a => <li key={a.id}><button className={a.id === selectedId ? 'selected' : ''} onClick={() => selectAgent(a.id)}><span className="dot" data-status={a.freshness === 'fresh' ? a.work.status : 'stale'} /><span><strong>{a.name}</strong><small>会话 · {sessionCues.get(a.id)}</small></span><em>{status(a)}</em></button></li>)}</ul> : <p className="empty">{agents.length ? '没有匹配的会话。' : state ? '当前没有获准展示的会话。' : '等待状态快照…'}</p>}{matchingAgents.length > 50 ? <div className="roster-pager"><button disabled={activeRosterPage === 0} onClick={() => setRosterPage(activeRosterPage - 1)}>上一组</button><span>{matchingAgents.length} 条 · {activeRosterPage + 1}/{rosterPages}</span><button disabled={activeRosterPage >= rosterPages - 1} onClick={() => setRosterPage(activeRosterPage + 1)}>下一组</button></div> : null}
    <div className="detail"><h2>会话详情</h2>{selected ? <dl><dt>状态</dt><dd>{status(selected)}</dd><dt>数据新鲜度</dt><dd>{selected.freshness === 'fresh' ? '已确认' : selected.freshness === 'stale' ? '过期' : '未知'}</dd><dt>活动运行 ID</dt><dd>{selected.work.activeRunIds === null ? '不可用' : selected.work.activeRunIds.length ? selected.work.activeRunIds.join('、') : '无'}</dd><dt>父会话</dt><dd>{selected.relation.parentId ? displayState?.agents[selected.relation.parentId]?.name ?? '不可见' : '未确认'}</dd><dt>可见子会话</dt><dd>{selected.relation.childIds === null ? '未确认' : selected.relation.childIds.length}</dd><dt>等待输入覆盖</dt><dd>{capability(state?.capabilities.blockingInput)}</dd><dt>模型</dt><dd>{selected.model.active ?? selected.model.selected ?? '未提供'}</dd><dt>当前工具</dt><dd>{selected.work.tool ? `${selected.work.tool.name} · ${selected.work.tool.phase === 'start' ? '开始' : '更新'}` : '未确认'}</dd><dt>Token 用量</dt><dd>{selected.usage.totalTokens ?? '未提供'}</dd><dt>最近活动</dt><dd>{date(selected.lastActivityAtMs)}</dd><dt>最后确认</dt><dd>{date(selected.lastVerifiedAtMs)}</dd><dt>工作摘要</dt><dd>{selected.work.summary ?? '未提供'}</dd><dt>进度卡</dt><dd><ProgressDetail agent={selected} coverage={state?.capabilities.progressCard} /></dd></dl> : <p className="empty">选择专员查看详情。</p>}</div><section className="capabilities" aria-label="观测能力"><h2>观测能力</h2><dl>{Object.entries(capabilityLabels).map(([key, label]) => <div key={key}><dt>{label}</dt><dd data-coverage={state?.capabilities[key as keyof typeof capabilityLabels] ?? 'unverified'}>{capability(state?.capabilities[key as keyof typeof capabilityLabels])}</dd></div>)}</dl>{state?.capabilities.blockingInput === 'forbidden' && <p className="pap-note">当前只读授权无法确认等待中的问题或审批；办公室不会从消息文本推断等待状态。</p>}<p className="subscription-coverage">逐会话消息订阅：{subscriptionCoverage ? subscriptionCoverage.unsupported ? '不支持' : `${subscriptionCoverage.leased}/${subscriptionCoverage.target} 已建立${subscriptionCoverage.syncing ? ' · 同步中' : ''}${subscriptionCoverage.queuedReads ? ` · ${subscriptionCoverage.queuedReads} 个读取请求排队` : ''}` : '统计暂不可用'}。仅表示已建立订阅，运行事件覆盖仍以能力状态为准。</p></section></aside></section>
    <PapTasks />
    <footer>办公室状态依据来自 Gateway 可读事件和快照；PAP 任务依据来自本地配置及运行记录。“本轮已完成”仅表示最近一轮运行结束。{measure && <output className="latency-meter" data-scene-fps={sceneFrameResult?.fps ?? ''} data-scene-frame-work-ms={sceneFrameResult?.averageWorkMs ?? ''} data-scene-frame-seconds={sceneFrameResult?.seconds ?? ''} data-latency-p95-ms={latency?.p95Ms ?? ''} data-latency-transit-p95-ms={latency?.transitP95Ms ?? ''} data-latency-render-p95-ms={latency?.renderP95Ms ?? ''} data-latency-event-p95-ms={sceneEventLatency?.p95Ms ?? ''} data-latency-event-samples={sceneEventLatency?.count ?? 0} data-latency-samples={latency?.count ?? 0} data-latency-sampled-total={latency?.totalCount ?? 0} data-latency-accepted={acceptedPatches}>Pixi 完成帧：{sceneFrameResult ? `${sceneFrameResult.fps.toFixed(1)} FPS（${sceneFrameResult.seconds.toFixed(1)} 秒，平均帧工作 ${sceneFrameResult.averageWorkMs.toFixed(1)} ms）${sceneFrameResult.fps < 30 ? '，低于 30 FPS 目标' : ''}` : '预热 3 秒后测量 30 秒'}。本地 SSE 至下一帧回调 P95：{latency ? `${latency.p95Ms} ms（到达浏览器 ${latency.transitP95Ms}，等待帧 ${latency.renderP95Ms}；有效样本 ${latency.totalCount}/${acceptedPatches}，最近 ${latency.count} 个样本）` : `采样中（已接收 ${acceptedPatches} 次）`}{acceptedPatches > 20 && (latency?.totalCount ?? 0) / acceptedPatches < .9 ? '；帧样本覆盖不足，不能用于延迟验收' : ''}。本页专员的结构化事件接收到场景完成帧：{sceneEventLatency ? `${sceneEventLatency.p95Ms} ms P95（${sceneEventLatency.count} 个状态标签变化）` : '等待有效样本'}。实际像素绘制及前台状态未由此验证。</output>}</footer>
  </main>;
}
