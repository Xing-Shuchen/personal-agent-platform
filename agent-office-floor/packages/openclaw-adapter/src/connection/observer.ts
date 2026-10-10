import { GatewayClient, GatewaySessionMessageSubscriptionCoordinator,
  type GatewayClientOptions, type GatewaySessionMessageSubscription } from '@openclaw/gateway-client';
import { GATEWAY_CLIENT_CAPS, GATEWAY_CLIENT_MODES, GATEWAY_CLIENT_NAMES } from '@openclaw/gateway-protocol/client-info';
import type { FloorAgent, RunOutcome } from '@pap/floor-contract';
import { isReadOnlyGrant } from './grant.ts';
import { floorId, normalizeSessionRow, type DisplayBinding, type SessionRow } from '../normalization/session.ts';
import { linkSessionRelations } from '../normalization/relations.ts';
import { preferCandidateRow } from '../normalization/snapshot-order.ts';
import { newerRow, rowClock, type RowClock } from '../normalization/row-clock.ts';
import { canReadProgress, normalizeProgressCard, progressCardMatchesRequest, progressReadParams } from '../normalization/progress.ts';
import { ReadQuota } from './read-quota.ts';
import { advanceRunSequence, runReceipt } from './run-sequence.ts';
import { chatReceipt, chatTerminal } from './chat-lifecycle.ts';
import { compactReceipt, initialCompactionCapability } from '../normalization/operation.ts';
import { initialToolCapability, isReadTool, toolReceipt } from '../normalization/tool.ts';
import { FloorStore, withRunTerminal } from '../sessions/floor-store.ts';

type ListResult = { sessions?: unknown[]; nextOffset?: number | null; hasMore?: boolean };
type SubscribeResult = { subscribed?: boolean; list?: ListResult };
const READ_METHODS = new Set(['sessions.subscribe', 'sessions.list',
  'sessions.messages.subscribe', 'sessions.messages.unsubscribe', 'progressCard.get']);
export type ObserverConfig = Readonly<{
  gatewayId: string;
  gatewayUrl: string;
  token?: string;
  selectedAgentIds: readonly string[];
  bindings?: Readonly<Record<string, DisplayBinding>>;
  deviceAuth?: Pick<GatewayClientOptions, 'deviceIdentity' | 'hostDeps'> & { hasStoredToken: boolean };
}>;
const row = (v: unknown): v is SessionRow => v !== null && typeof v === 'object' && !Array.isArray(v) && typeof (v as Record<string, unknown>).key === 'string';

/** One upstream connection for all browser viewers. Only the allowlisted agent IDs are projected. */
export class GatewayObserver {
  private client: GatewayClient | null = null;
  private timer: NodeJS.Timeout | null = null;
  private scanBusyEpoch: number | null = null;
  private scanAgain = false;
  private bootstrapping = false;
  private bootstrapDirty = false;
  private invalidatedAt: number | null = null;
  private messageSubscriptionsEpoch: number | null = null;
  private messageSubscriptionsAgain = false;
  private messageSubscriptionUnsupported = false;
  private subscribed = false;
  private seenOnce = new Set<string>();
  private rowClocks = new Map<string, RowClock>();
  private rowOrder = 0;
  private runSequences = new Map<string, { id: string; sessionId: string; seq: number }>();
  private chatSequences = new Map<string, { id: string; sessionId: string; seq: number }>();
  private toolSequences = new Map<string, { id: string; sessionId: string; seq: number }>();
  private unmatchedRuns = new Map<string, 'seen' | 'terminal'>();
  private chatTerminals = new Map<string, { id: string; sessionId: string; outcome: RunOutcome | 'yielded';
    seq: number; observedAtMs: number; afterOrder: number; absentScans: number }>();
  private compactions = new Map<string, { sessionId: string; operationId: string; active: boolean; ts: number }>();
  private messageCoordinator: GatewaySessionMessageSubscriptionCoordinator | null = null;
  private messageLeases = new Map<string, { sessionId: string | null; lease: GatewaySessionMessageSubscription }>();
  private stopped = false;
  private connectionEpoch = 0;
  private authPaused = false;
  private reads = new ReadQuota();
  private progressSupported = false;
  private progressPending = new Map<string, Promise<boolean>>();
  private progressLastRead = new Map<string, number>();
  private progressViews = new Map<string, number>();
  private visibleViewer = false;
  constructor(private readonly config: ObserverConfig, private readonly store: FloorStore) {}

  setVisibleViewer(visible: boolean): void {
    if (this.visibleViewer === visible) return;
    this.visibleViewer = visible;
    if (visible && this.bootstrapping) { this.bootstrapDirty = true; return; }
    if (visible) this.queueScan(0);
    else if (!this.subscribed) this.queueScan(15000);
  }

  start(): void {
    if (this.client || this.stopped) return;
    if (!this.config.selectedAgentIds.length) {
      this.store.setConnection({ mode: 'none', state: 'degraded', lastConfirmedAtMs: null, reason: '尚未选择要展示的专员' });
      return;
    }
    if (!this.config.token && !this.config.deviceAuth) {
      this.store.setConnection({ mode: 'none', state: 'auth_required', lastConfirmedAtMs: null, reason: '缺少本地 Gateway 观察凭据' });
      return;
    }
    this.client = new GatewayClient({
      url: this.config.gatewayUrl, token: this.config.token,
      deviceIdentity: this.config.deviceAuth?.deviceIdentity,
      hostDeps: this.config.deviceAuth?.hostDeps,
      role: 'operator', scopes: ['operator.read'],
      caps: [GATEWAY_CLIENT_CAPS.TOOL_EVENTS],
      clientName: GATEWAY_CLIENT_NAMES.GATEWAY_CLIENT, mode: GATEWAY_CLIENT_MODES.BACKEND,
      clientVersion: '0.1.0', platform: process.platform,
      requestTimeoutMs: 5000,
      onHelloOk: hello => {
        if (!isReadOnlyGrant(hello.auth)) {
          this.authPaused = true;
          this.store.revokeAccess('Gateway 未授予严格只读观察权限');
          this.client?.stop();
          return;
        }
        this.connectionEpoch++; this.authPaused = false; this.subscribed = false;
        if (this.timer) clearTimeout(this.timer);
        this.timer = null; this.invalidatedAt = null;
        this.scanBusyEpoch = null; this.scanAgain = false;
        this.bootstrapping = true; this.bootstrapDirty = false;
        this.messageCoordinator?.reset(); this.messageLeases.clear();
        this.messageCoordinator = new GatewaySessionMessageSubscriptionCoordinator({
          request: <T>(method: string, params: Record<string, unknown>): Promise<T> =>
            method === 'sessions.messages.subscribe' || method === 'sessions.messages.unsubscribe'
              ? this.requestRead<T>(method, params) : Promise.reject(new Error('observer RPC not allowed'))
        });
        this.messageSubscriptionsEpoch = null;
        this.messageSubscriptionsAgain = false;
        this.messageSubscriptionUnsupported = false;
        this.rowClocks.clear(); this.rowOrder = 0;
        this.runSequences.clear();
        this.chatSequences.clear();
        this.toolSequences.clear();
        this.unmatchedRuns.clear();
        this.chatTerminals.clear();
        this.compactions.clear();
        const recentStarts = this.reads.recentStarts();
        this.reads.close(); this.reads = new ReadQuota(recentStarts);
        this.progressSupported = canReadProgress(hello.features);
        this.progressLastRead.clear(); this.progressViews.clear(); this.progressPending.clear();
        this.store.resetEpoch(); void this.bootstrap(this.connectionEpoch);
        this.store.setCapability('progressCard', this.progressSupported ? 'unverified' :
          hello.features.methods.includes('progressCard.get') ? 'partial' : 'unsupported');
        this.store.setCapability('compaction', initialCompactionCapability(hello.features.events));
        this.store.setCapability('toolEvents', initialToolCapability(hello.features.events));
        this.store.setCapability('blockingInput', 'forbidden');
      },
      onEvent: event => {
        if (this.authPaused || this.stopped) return;
        if (event.event === 'sessions.changed' || event.event === 'session.message') this.admitHeldRow(event.payload);
        if (event.event === 'agent') this.observeAgent(event.payload);
        else if (event.event === 'chat') this.observeChatLifecycle(event.payload);
        else if (event.event === 'session.operation') this.observeOperation(event.payload);
        else if (event.event === 'session.tool') this.observeTool(event.payload);
        else if (event.event === 'sessions.changed' || event.event === 'session.message') this.invalidate();
        if (event.event === 'progressCard.changed') {
          this.progressLastRead.clear();
          for (const [id, viewedAt] of this.progressViews) if (Date.now() - viewedAt < 30000) void this.refreshProgress(id, true);
        }
      },
      onClose: () => { this.connectionEpoch++; this.bootstrapping = false;
        if (this.timer) clearTimeout(this.timer); this.timer = null;
        this.compactions.clear();
        this.messageCoordinator?.reset(); this.messageCoordinator = null;
        this.messageLeases.clear(); this.reads.close(); if (!this.authPaused) this.offline('Gateway 连接已断开'); },
      onGap: () => {
        if (this.authPaused || this.stopped) return;
        this.compactions.clear();
        if (this.store.snapshot().capabilities.compaction !== 'unsupported')
          this.store.setCapability('compaction', 'partial');
        this.store.markStale();
        this.store.setConnection({ mode: this.subscribed ? 'subscription' : 'polling', state: 'degraded', lastConfirmedAtMs: this.store.snapshot().connection.lastConfirmedAtMs, reason: '事件序列缺口；正在校准' });
        if (this.bootstrapping) this.bootstrapDirty = true;
        else this.queueScan(0);
      },
      onConnectError: error => this.handleConnectError(error)
    });
    this.client.start();
  }
  stop(): void {
    this.stopped = true;
    this.bootstrapping = false;
    if (this.timer) clearTimeout(this.timer);
    this.reads.close();
    this.messageCoordinator?.reset(); this.messageCoordinator = null; this.messageLeases.clear();
    this.client?.stop(); this.client = null;
  }
  private handleConnectError(error: Error): void {
    if (this.authPaused || this.stopped) return;
    this.connectionEpoch++;
    this.bootstrapping = false;
    if (this.timer) clearTimeout(this.timer); this.timer = null;
    const auth = /forbidden|unauthorized|permission|scope|pairing|auth/i.test(error.message);
    if (auth) this.authPaused = true;
    if (auth) this.store.revokeAccess('Gateway 需要授权');
    else this.offline('Gateway 连接失败');
    if (auth) this.client?.stop();
  }
  /** Aggregate transport coverage; never includes session keys or other Gateway data. */
  subscriptionCoverage(): { target: number; leased: number; queuedReads: number; syncing: boolean; unsupported: boolean } {
    const agents = this.store.snapshot().agents;
    let leased = 0;
    for (const [id, subscription] of this.messageLeases) {
      if (agents[id]?.session.sessionId === subscription.sessionId) leased++;
    }
    return { target: Object.keys(agents).length, leased, queuedReads: this.reads.queuedCount(),
      syncing: this.messageSubscriptionsEpoch === this.connectionEpoch,
      unsupported: this.messageSubscriptionUnsupported };
  }
  /** Only the authenticated local view's opaque ID may request an existing card. */
  refreshProgress(id: string, force = false): Promise<boolean> {
    const agent = this.store.snapshot().agents[id];
    const params = agent ? progressReadParams(agent, this.progressSupported) : null;
    if (!this.client?.connected || !agent || !params || agent.freshness !== 'fresh' ||
      this.store.snapshot().capabilities.progressCard === 'forbidden') return Promise.resolve(false);
    this.progressViews.set(id, Date.now());
    const pending = this.progressPending.get(id);
    if (pending) return pending;
    if (!force && Date.now() - (this.progressLastRead.get(id) ?? 0) < 5000) return Promise.resolve(true);
    const epoch = this.connectionEpoch, sessionId = agent.session.sessionId;
    const task = this.requestRead<unknown>('progressCard.get', params).then(reply => {
      if (epoch !== this.connectionEpoch || this.stopped || !this.progressSupported) return false;
      if (!progressCardMatchesRequest(reply, params)) {
        this.store.setProgress(id, sessionId, null);
        throw new Error('progress card target mismatch');
      }
      const progress = normalizeProgressCard(reply);
      const applied = this.store.setProgress(id, sessionId, progress);
      if (applied) { this.progressLastRead.set(id, Date.now()); this.store.setCapability('progressCard', 'available'); }
      return applied;
    }).catch(error => {
      if (epoch === this.connectionEpoch && !this.stopped) {
        if (error instanceof Error && /forbidden|unauthorized|permission|scope/i.test(error.message)) {
          this.progressSupported = false;
          this.progressViews.clear();
          this.progressLastRead.clear();
          this.store.revokeProgressAccess();
        } else this.store.setCapability('progressCard', 'partial');
      }
      return false;
    }).finally(() => { if (this.progressPending.get(id) === task) this.progressPending.delete(id); });
    this.progressPending.set(id, task);
    return task;
  }
  private requestRead<T>(method: 'sessions.subscribe'|'sessions.list'|'sessions.messages.subscribe'|'sessions.messages.unsubscribe'|'progressCard.get', params: object): Promise<T> {
    if (!READ_METHODS.has(method)) return Promise.reject(new Error('observer RPC not allowed'));
    const client = this.client;
    if (!client?.connected) return Promise.reject(new Error('Gateway disconnected'));
    return this.reads.run(() => client.request<T>(method, params));
  }
  private offline(reason: string): void {
    if (this.stopped) return;
    const auth = reason.includes('授权');
    this.store.setConnection({ mode: this.subscribed ? 'subscription' : 'none', state: auth ? 'auth_required' : 'offline', lastConfirmedAtMs: this.store.snapshot().connection.lastConfirmedAtMs, reason });
  }
  private invalidate(): void {
    if (this.bootstrapping) { this.bootstrapDirty = true; return; }
    const now = Date.now();
    this.invalidatedAt ??= now;
    this.queueScan(Math.max(0, Math.min(250, this.invalidatedAt + 1000 - now)));
  }
  private admitHeldRow(payload: unknown): void {
    if (!payload || typeof payload !== 'object' || Array.isArray(payload)) return;
    const candidate = (payload as Record<string, unknown>).session;
    if (!row(candidate) || typeof candidate.agentId !== 'string' ||
      !this.config.selectedAgentIds.includes(candidate.agentId)) return;
    const id = floorId(this.config.gatewayId, candidate.agentId, candidate.key);
    const previous = this.store.snapshot().agents[id];
    if (!previous || previous.freshness !== 'fresh' || !previous.session.sessionId ||
      candidate.sessionId !== previous.session.sessionId) return;
    const clock = rowClock(candidate, ++this.rowOrder);
    if (!newerRow(this.rowClocks.get(id), clock)) return;
    const event = payload as Record<string, unknown>;
    const projected = { ...candidate };
    if (!Object.hasOwn(projected, 'activeRunIds') && Object.hasOwn(event, 'activeRunIds'))
      projected.activeRunIds = event.activeRunIds;
    if (!Object.hasOwn(projected, 'hasActiveRun') && Object.hasOwn(event, 'hasActiveRun'))
      projected.hasActiveRun = event.hasActiveRun;
    let agent = normalizeSessionRow(projected, this.config.gatewayId, Date.now(),
      this.config.bindings?.[candidate.agentId] ?? {}, previous, false);
    for (const [runId, terminal] of this.chatTerminals) {
      if (terminal.id !== id || terminal.sessionId !== agent.session.sessionId) continue;
      const fenced = withRunTerminal(agent, runId, terminal.outcome, terminal.seq, terminal.observedAtMs);
      if (fenced) agent = { ...fenced, freshness: 'stale' };
      else if (agent.work.activeRunIds === null || !agent.work.activeRunIds.includes(runId))
        agent = { ...agent, freshness: 'stale', work: previous.work };
    }
    const operation = this.compactions.get(id);
    if (operation?.sessionId === agent.session.sessionId)
      agent = { ...agent, work: { ...agent.work, compacting: operation.active } };
    this.rowClocks.set(id, clock!);
    this.store.upsertAgent({ ...agent, relation: previous.relation });
  }
  private observeRunSequence(payload: unknown): void {
    const receipt = runReceipt(payload);
    if (!receipt) { this.invalidate(); return; }
    const matches = Object.values(this.store.snapshot().agents).filter(agent =>
      agent.freshness === 'fresh' && agent.session.sessionId &&
      (agent.work.activeRunIds?.includes(receipt.runId) ||
        this.matchesUnlistedActiveRun(agent, payload)));
    if (matches.length !== 1) { this.invalidateUnmatchedRun(receipt.runId); return; }
    const agent = matches[0];
    const previous = this.runSequences.get(receipt.runId);
    const same = previous?.id === agent.id && previous.sessionId === agent.session.sessionId;
    if (previous && !same) {
      this.store.markAgentStale(agent.id);
      this.queueScan(0);
      return;
    }
    const result = advanceRunSequence(same ? previous.seq : undefined, receipt.seq);
    if (result === 'duplicate') return;
    this.runSequences.set(receipt.runId, { id: agent.id, sessionId: agent.session.sessionId!, seq: receipt.seq });
    if (result === 'gap') {
      this.store.markAgentStale(agent.id);
      this.queueScan(0);
    }
  }
  private observeAgent(payload: unknown): void {
    this.observeRunSequence(payload);
    // The pinned Gateway can deliver hidden runs' tool stream through the
    // selected session-message lease as an agent event with a session snapshot.
    // Other agent events are not enough to establish tool ownership.
    if (payload && typeof payload === 'object' && !Array.isArray(payload)) {
      const value = payload as Record<string, unknown>;
      if (value.stream === 'tool' && value.session && typeof value.session === 'object' &&
          !Array.isArray(value.session)) this.observeTool(payload);
    }
  }
  private observeTool(payload: unknown): void {
    const receipt = toolReceipt(payload);
    if (!receipt) { this.invalidate(); return; }
    const matches = Object.values(this.store.snapshot().agents).filter(agent =>
      agent.freshness === 'fresh' && agent.session.key === receipt.sessionKey &&
      agent.session.sessionId === receipt.sessionId && agent.session.agentId === receipt.agentId &&
      (agent.work.activeRunIds?.includes(receipt.runId) ||
        this.matchesUnlistedActiveRun(agent, payload)));
    if (matches.length !== 1) { this.invalidateUnmatchedRun(receipt.runId); return; }
    const agent = matches[0];
    const previous = this.toolSequences.get(receipt.runId);
    if (previous && (previous.id !== agent.id || previous.sessionId !== receipt.sessionId)) {
      this.store.markAgentStale(agent.id);
      this.queueScan(0);
      return;
    }
    if (previous && receipt.seq <= previous.seq) return;
    this.toolSequences.set(receipt.runId, { id: agent.id, sessionId: receipt.sessionId, seq: receipt.seq });
    if (this.toolSequences.size > 1000) this.toolSequences.delete(this.toolSequences.keys().next().value!);
    const current = agent.work.tool;
    if (receipt.phase !== 'start' && (current?.callId !== receipt.callId || current.name !== receipt.name)) {
      this.invalidate();
      return;
    }
    const observedAtMs = Date.now();
    this.store.upsertAgent({ ...agent, lastVerifiedAtMs: observedAtMs, work: { ...agent.work,
      phase: receipt.phase !== 'end' && isReadTool(receipt.name) ? 'reading' : 'executing',
      tool: receipt.phase === 'end' ? null : { name: receipt.name, callId: receipt.callId, phase: receipt.phase },
      evidence: [...agent.work.evidence.slice(-7), { source: 'tool_event', reference: `${receipt.runId}:${receipt.seq}`,
        sourceAtMs: null, observedAtMs }]
    } });
    this.store.setCapability('toolEvents', 'partial');
  }
  private matchesUnlistedActiveRun(agent: FloorAgent, payload: unknown): boolean {
    if (agent.work.activeRunIds !== null || agent.work.hasActiveRun !== true ||
        !agent.session.sessionId || !agent.session.agentId ||
        !payload || typeof payload !== 'object' || Array.isArray(payload)) return false;
    const event = payload as Record<string, unknown>;
    if (!event.session || typeof event.session !== 'object' || Array.isArray(event.session)) return false;
    const session = event.session as Record<string, unknown>;
    return event.sessionKey === agent.session.key && event.agentId === agent.session.agentId &&
      event.sessionId === agent.session.sessionId && session.key === agent.session.key &&
      session.agentId === agent.session.agentId && session.sessionId === agent.session.sessionId &&
      session.status === 'running';
  }
  private invalidateUnmatchedRun(runId: string, terminal = false): void {
    const previous = this.unmatchedRuns.get(runId);
    if (previous === 'terminal' || (previous === 'seen' && !terminal)) return;
    this.unmatchedRuns.set(runId, terminal ? 'terminal' : 'seen');
    if (this.unmatchedRuns.size > 1000) this.unmatchedRuns.delete(this.unmatchedRuns.keys().next().value!);
    this.invalidate();
  }
  private observeChatLifecycle(payload: unknown): void {
    const receipt = chatReceipt(payload);
    if (!receipt) { this.invalidate(); return; }
    const matches = Object.values(this.store.snapshot().agents).filter(agent =>
      agent.freshness === 'fresh' && agent.session.sessionId &&
      agent.session.key === receipt.sessionKey &&
      (receipt.agentId === null || receipt.agentId === agent.session.agentId) &&
      agent.work.activeRunIds?.includes(receipt.runId));
    if (matches.length !== 1) {
      this.invalidateUnmatchedRun(receipt.runId, receipt.state === 'final' || receipt.state === 'error' || receipt.state === 'aborted');
      return;
    }
    const agent = matches[0];
    const previous = this.chatSequences.get(receipt.runId);
    const same = previous?.id === agent.id && previous.sessionId === agent.session.sessionId;
    if (previous && !same) {
      this.store.markAgentStale(agent.id);
      this.queueScan(0);
      return;
    }
    const order = advanceRunSequence(same ? previous.seq : undefined, receipt.seq);
    if (order === 'duplicate') return;
    this.chatSequences.set(receipt.runId, { id: agent.id, sessionId: agent.session.sessionId!, seq: receipt.seq });
    if (this.chatSequences.size > 1000) this.chatSequences.delete(this.chatSequences.keys().next().value!);
    if (order === 'gap') {
      this.store.markAgentStale(agent.id);
      this.queueScan(0);
      return;
    }
    const observedAtMs = Date.now();
    const terminal = chatTerminal(receipt, observedAtMs);
    if (terminal && this.store.setRunTerminal(agent.id, agent.session.sessionId!, receipt.runId, terminal, receipt.seq, observedAtMs)) {
      this.chatTerminals.set(receipt.runId, { id: agent.id, sessionId: agent.session.sessionId!, outcome: terminal,
        seq: receipt.seq, observedAtMs, afterOrder: this.rowOrder, absentScans: 0 });
      if (this.chatTerminals.size > 1000) this.chatTerminals.delete(this.chatTerminals.keys().next().value!);
      this.invalidate();
    }
  }
  private observeOperation(payload: unknown): void {
    const receipt = compactReceipt(payload);
    if (!receipt) { this.invalidate(); return; }
    const matches = Object.values(this.store.snapshot().agents).filter(agent =>
      agent.freshness === 'fresh' && agent.session.sessionId &&
      agent.session.key === receipt.sessionKey &&
      (receipt.agentId === null || receipt.agentId === agent.session.agentId));
    if (matches.length !== 1) { this.invalidate(); return; }
    const agent = matches[0];
    const previous = this.compactions.get(agent.id);
    if (receipt.phase === 'start') {
      // An old event for a reused key cannot describe a newer row instance.
      if (agent.metadataUpdatedAtMs === null || receipt.ts < agent.metadataUpdatedAtMs ||
        previous?.sessionId === agent.session.sessionId && previous.active && previous.operationId !== receipt.operationId) {
        this.store.markAgentStale(agent.id); this.invalidate(); return;
      }
      if (previous?.sessionId === agent.session.sessionId && previous.operationId === receipt.operationId) return;
      if (!this.store.setCompacting(agent.id, agent.session.sessionId!, receipt.operationId, true, receipt.ts, Date.now())) return;
      this.compactions.set(agent.id, { sessionId: agent.session.sessionId!, operationId: receipt.operationId, active: true, ts: receipt.ts });
      this.store.setCapability('compaction', 'partial');
      return;
    }
    if (!previous || previous.sessionId !== agent.session.sessionId || previous.operationId !== receipt.operationId ||
      !previous.active || receipt.ts < previous.ts) { this.invalidate(); return; }
    if (!this.store.setCompacting(agent.id, agent.session.sessionId!, receipt.operationId, false, receipt.ts, Date.now())) return;
    this.compactions.set(agent.id, { ...previous, active: false, ts: receipt.ts });
    this.store.setCapability('compaction', 'available');
  }
  private queueScan(ms: number): void {
    if (this.stopped || !this.client?.connected) return;
    if (this.timer) clearTimeout(this.timer);
    this.timer = setTimeout(() => { this.timer = null; this.invalidatedAt = null; void this.scan(); }, ms);
  }
  private async bootstrap(epoch: number): Promise<void> {
    if (this.stopped || !this.client) return;
    try {
      const first = await this.requestRead<SubscribeResult>('sessions.subscribe', { limit: 100, includeLastMessage: false });
      if (epoch !== this.connectionEpoch || this.stopped) return;
      if (!first.subscribed || !first.list) throw new Error('subscription unavailable');
      this.subscribed = true;
      this.store.setCapability('sessionEvents', 'available');
      await this.scan(first.list, epoch);
    } catch (error) {
      if (epoch !== this.connectionEpoch || this.stopped) return;
      this.subscribed = false;
      const reason = error instanceof Error ? error.message : '';
      this.store.setCapability('sessionEvents', /unsupported|unknown method|method not found|unimplemented|subscription unavailable/i.test(reason)
        ? 'unsupported' : /forbidden|unauthorized|permission|scope/i.test(reason) ? 'forbidden' : 'partial');
      await this.scan(undefined, epoch);
    } finally {
      if (epoch === this.connectionEpoch && !this.stopped) {
        this.bootstrapping = false;
        const dirty = this.bootstrapDirty;
        this.bootstrapDirty = false;
        if (dirty) this.queueScan(0);
        else if (this.subscribed) this.queueScan(250); // Tail calibration covers changes during bootstrap.
      }
    }
  }
  private async scan(first?: ListResult, epoch = this.connectionEpoch): Promise<void> {
    if (this.stopped || epoch !== this.connectionEpoch || !this.client?.connected) return;
    if (this.scanBusyEpoch === epoch) { this.scanAgain = true; return; }
    this.scanBusyEpoch = epoch;
    try {
      const scanOrder = ++this.rowOrder;
      const observedAtMs = Date.now();
      const list: ListResult[] = [];
      let page = first ?? await this.requestRead<ListResult>('sessions.list', { limit: 100, includeLastMessage: false });
      list.push(page);
      let pages = 0;
      while (page.hasMore && typeof page.nextOffset === 'number' && pages < 100) {
        page = await this.requestRead<ListResult>('sessions.list', { limit: 100, offset: page.nextOffset, includeLastMessage: false });
        list.push(page); pages++;
      }
      if (epoch !== this.connectionEpoch || this.stopped) return;
      if (page.hasMore || list.some(p => !Array.isArray(p.sessions))) throw new Error('incomplete session scan');
      const selected = new Set(this.config.selectedAgentIds);
      const agents = new Map<string, FloorAgent>();
      const entriesById = new Map<string, { agent: FloorAgent; row: SessionRow; heldNewer: boolean }>();
      for (const item of list.flatMap(p => p.sessions ?? [])) {
        if (!row(item) || typeof item.agentId !== 'string' || !selected.has(item.agentId)) continue;
        const binding = this.config.bindings?.[item.agentId] ?? {};
        const id = floorId(this.config.gatewayId, item.agentId, item.key);
        const held = this.store.snapshot().agents[id];
        const clock = rowClock(item, scanOrder);
        const newerHeld = !!held && held.session.sessionId === clock?.sessionId &&
          newerRow(clock ?? undefined, this.rowClocks.get(id) ?? null);
        const agent = newerHeld ? held : normalizeSessionRow(item, this.config.gatewayId, observedAtMs, binding, held);
        const previous = entriesById.get(agent.id);
        if (previous && !preferCandidateRow(previous.row, item)) continue;
        agents.set(agent.id, agent);
        entriesById.set(agent.id, { agent, row: item, heldNewer: newerHeld });
        if (!newerHeld && clock) this.rowClocks.set(id, clock);
      }
      for (const entry of entriesById.values()) {
        let current = entry.agent;
        for (const [runId, terminal] of this.chatTerminals) {
          if (terminal.id !== current.id || terminal.sessionId !== current.session.sessionId) continue;
          if (Array.isArray(entry.row.activeRunIds) && !entry.row.activeRunIds.includes(runId)) {
            const confirmed = entry.row.lastRunId === runId &&
              (['done','failed','interrupted','killed','timeout'].includes(String(entry.row.status)) ||
                terminal.outcome === 'yielded' && entry.row.hasActiveRun === false);
            const postEvent = scanOrder > terminal.afterOrder && !entry.heldNewer;
            if (postEvent) terminal.absentScans++;
            if (postEvent && (confirmed || terminal.absentScans >= 2)) this.chatTerminals.delete(runId);
            else {
              const held = this.store.snapshot().agents[current.id];
              current = { ...current, freshness: 'stale',
                work: held?.session.sessionId === terminal.sessionId ? held.work : current.work };
            }
            continue;
          }
          terminal.absentScans = 0;
          const fenced = withRunTerminal(current, runId, terminal.outcome, terminal.seq, terminal.observedAtMs);
          if (fenced) current = { ...fenced, freshness: 'stale' };
          else if (current.work.activeRunIds === null) {
            const held = this.store.snapshot().agents[current.id];
            if (held?.session.sessionId === terminal.sessionId && held.work.activeRunIds?.includes(runId) === false)
              current = { ...current, freshness: 'stale', work: held.work };
          }
        }
        const operation = this.compactions.get(current.id);
        if (operation?.sessionId === current.session.sessionId)
          current = { ...current, work: { ...current.work, compacting: operation.active } };
        entry.agent = current;
        agents.set(current.id, current);
      }
      for (const terminal of this.chatTerminals.values()) {
        const entry = entriesById.get(terminal.id);
        if (!entry || entry.agent.session.sessionId !== terminal.sessionId) terminal.absentScans = 0;
      }
      for (const agent of linkSessionRelations([...entriesById.values()])) agents.set(agent.id, agent);
      // Two complete scans must agree on ordinary absence before deletion.
      const ids = new Set(agents.keys());
      const deleteConfirmed = [...Object.keys(this.store.snapshot().agents)].every(id => ids.has(id) || !this.seenOnce.has(id));
      this.store.replaceAgents([...agents.values()], deleteConfirmed);
      const uncertainRows = Object.values(this.store.snapshot().agents).some(agent => agent.freshness === 'stale') ||
        (this.bootstrapping && this.bootstrapDirty);
      for (const id of this.rowClocks.keys()) if (!this.store.snapshot().agents[id]) this.rowClocks.delete(id);
      for (const [runId, sequence] of this.runSequences) {
        const agent = this.store.snapshot().agents[sequence.id];
        if (!agent || agent.session.sessionId !== sequence.sessionId || !agent.work.activeRunIds?.includes(runId))
          this.runSequences.delete(runId);
      }
      for (const [id, operation] of this.compactions) {
        const agent = this.store.snapshot().agents[id];
        if (!agent || agent.session.sessionId !== operation.sessionId) this.compactions.delete(id);
      }
      this.seenOnce = ids;
      this.store.setCapability('sessionList', 'available');
      this.store.setCapability('runEvents', 'partial');
      this.store.setCapability('blockingInput', 'forbidden');
      const anyActive = [...agents.values()].some(a => a.work.status === 'running' || a.work.status === 'queued');
      this.store.setConnection({ mode: this.subscribed ? 'subscription' : 'polling',
        state: uncertainRows ? 'degraded' : 'live', lastConfirmedAtMs: observedAtMs,
        reason: this.bootstrapping && this.bootstrapDirty ? '订阅初始化期间收到变更；正在校准' :
          uncertainRows ? '会话快照早于已观察事件；正在重新校准' :
          this.subscribed ? null : `会话订阅不可用；每 ${anyActive ? 2 : 5} 秒轮询` });
      // Session subscriptions can take many quota slots. Do not make their tail
      // postpone the next authoritative roster scan.
      this.scheduleMessageSubscriptions(Object.values(this.store.snapshot().agents), epoch);
      if (this.invalidatedAt === null) this.queueScan(uncertainRows ? 250 : this.subscribed ? 30000 :
        !this.visibleViewer ? 15000 : anyActive ? 2000 : 5000);
    } catch (error) {
      if (epoch !== this.connectionEpoch || this.stopped) return;
      if (error instanceof Error && /forbidden|unauthorized|permission|scope/i.test(error.message)) {
        this.authPaused = true;
        this.store.revokeAccess('Gateway 会话读取权限已撤销');
        this.client?.stop();
        return;
      }
      const last = this.store.snapshot().connection.lastConfirmedAtMs;
      if (last === null || Date.now() - last > 60000) this.store.markStale();
      this.store.setConnection({ mode: this.subscribed ? 'subscription' : 'polling', state: 'degraded', lastConfirmedAtMs: this.store.snapshot().connection.lastConfirmedAtMs, reason: '会话校准失败；保留上次确认状态' });
      this.queueScan(5000);
    } finally {
      if (this.scanBusyEpoch === epoch) {
        this.scanBusyEpoch = null;
        if (this.scanAgain) {
          this.scanAgain = false;
          if (this.bootstrapping) this.bootstrapDirty = true;
          else this.queueScan(0);
        }
      }
    }
  }
  private scheduleMessageSubscriptions(agents: readonly FloorAgent[], epoch: number): void {
    if (this.messageSubscriptionUnsupported) return;
    if (this.messageSubscriptionsEpoch === epoch) {
      this.messageSubscriptionsAgain = true;
      return;
    }
    this.messageSubscriptionsEpoch = epoch;
    void this.subscribeMessages(agents, epoch).finally(() => {
      if (this.messageSubscriptionsEpoch !== epoch) return;
      this.messageSubscriptionsEpoch = null;
      if (this.messageSubscriptionsAgain && epoch === this.connectionEpoch && !this.stopped) {
        this.messageSubscriptionsAgain = false;
        this.scheduleMessageSubscriptions(Object.values(this.store.snapshot().agents), epoch);
      }
    });
  }
  private async subscribeMessages(agents: readonly FloorAgent[], epoch: number): Promise<void> {
    const coordinator = this.messageCoordinator;
    if (!coordinator || this.messageSubscriptionUnsupported) return;
    const current = new Map(agents.map(agent => [agent.id, agent]));
    for (const [id, subscription] of this.messageLeases) {
      if (epoch !== this.connectionEpoch || this.stopped) return;
      if (current.get(id)?.session.sessionId === subscription.sessionId) continue;
      this.messageLeases.delete(id);
      try { await coordinator.release(subscription.lease); }
      catch { this.queueScan(0); }
    }
    for (const agent of agents) {
      if (epoch !== this.connectionEpoch || this.stopped) return;
      if (this.messageLeases.get(agent.id)?.sessionId === agent.session.sessionId) continue;
      try {
        const lease = await coordinator.acquire(agent.session.key, { agentId: agent.session.agentId });
        if (epoch !== this.connectionEpoch || this.stopped) {
          await coordinator.release(lease);
          return;
        }
        if (this.store.snapshot().agents[agent.id]?.session.sessionId !== agent.session.sessionId) {
          await coordinator.release(lease);
          continue;
        }
        this.messageLeases.set(agent.id, { sessionId: agent.session.sessionId, lease });
      } catch (error) {
        const reason = error instanceof Error ? error.message : '';
        if (/unsupported|unknown method|method not found|unimplemented/i.test(reason)) {
          this.messageSubscriptionUnsupported = true;
          return;
        }
        // A row may be visible without message-subscription authority.
      }
    }
  }
}
