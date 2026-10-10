import { emptyFloorState, isFloorState } from '@pap/floor-contract';
import type { FloorAgent, FloorConnection, FloorHandoff, FloorProgress, FloorState, FloorUpdate, RunOutcome } from '@pap/floor-contract';

type Listener = (update: FloorUpdate) => void;
function visibleHandoffs(handoffs: readonly FloorHandoff[], agents: Readonly<Record<string, FloorAgent>>): readonly FloorHandoff[] {
  return handoffs.filter(handoff => agents[handoff.fromId]?.freshness === 'fresh' &&
    agents[handoff.toId]?.freshness === 'fresh');
}
function uncertainAgent(agent: FloorAgent): FloorAgent {
  if (agent.freshness === 'stale' && agent.work.phase === null && agent.work.hasActiveRun === null &&
      agent.work.activeRunIds === null && agent.work.tool === null && agent.work.attention === null &&
      agent.work.compacting === null && agent.work.looping === null) return agent;
  return { ...agent, freshness: 'stale', work: { ...agent.work, phase: null, hasActiveRun: null,
    activeRunIds: null, tool: null, attention: null, compacting: null, looping: null } };
}
export function withRunTerminal(agent: FloorAgent, runId: string, outcome: RunOutcome | 'yielded', seq: number, observedAtMs: number): FloorAgent | null {
  if (!agent.work.activeRunIds?.includes(runId)) return null;
  const remaining = agent.work.activeRunIds.filter(active => active !== runId);
  return { ...agent, lastVerifiedAtMs: observedAtMs, work: { ...agent.work,
    activeRunIds: remaining, hasActiveRun: remaining.length > 0,
    status: remaining.length ? 'running' : outcome === 'yielded' ? 'idle' :
      outcome.result === 'success' ? 'completed' : outcome.result === 'cancelled' ? 'stopped' : 'error',
    phase: remaining.length ? 'executing' : null,
    tool: null, latestOutcome: outcome === 'yielded' ? null : outcome,
    evidence: [...agent.work.evidence.slice(-7), { source: 'run_event', reference: `${runId}:${seq}`,
      sourceAtMs: null, observedAtMs }]
  } };
}
export class FloorStore {
  private state: FloorState;
  private listeners = new Set<Listener>();
  constructor(epoch: string = crypto.randomUUID()) { this.state = emptyFloorState(epoch); }
  snapshot(): FloorState { return this.state; }
  /** Register first, then emit a synchronous baseline. No revision can be missed between the two. */
  observe(listener: Listener): () => void {
    this.listeners.add(listener);
    listener({ type: 'snapshot', state: this.state });
    return () => this.listeners.delete(listener);
  }
  private publish(update: FloorUpdate, state: FloorState): void {
    if (!isFloorState(state)) throw new Error('invalid server FloorState');
    this.state = state;
    for (const listener of this.listeners) listener(update);
  }
  resetEpoch(): void {
    const old = this.state;
    const generatedAtMs = Date.now();
    const agents = Object.fromEntries(Object.entries(old.agents).map(([id, agent]) => [id, {
      ...agent, freshness: 'stale' as const, progress: null, lastMessagePreview: null,
      work: { ...agent.work, phase: null, hasActiveRun: null, activeRunIds: null, tool: null, attention: null, compacting: null, looping: null }
    }]));
    const state: FloorState = { ...old, epoch: crypto.randomUUID(), revision: 0, generatedAtMs,
      connection: { mode: 'none', state: 'connecting', lastConfirmedAtMs: old.connection.lastConfirmedAtMs, reason: '正在建立新的 Gateway 基线' },
      agents, handoffs: [] };
    this.publish({ type: 'snapshot', state }, state);
  }
  replaceAgents(agents: readonly FloorAgent[], confirmed: boolean): void {
    const old = this.state;
    const nextAgents = { ...old.agents } as Record<string, FloorAgent>;
    const upserts: FloorAgent[] = [];
    const seen = new Set<string>();
    for (const agent of agents) {
      seen.add(agent.id);
      if (JSON.stringify(nextAgents[agent.id]) !== JSON.stringify(agent)) {
        nextAgents[agent.id] = agent;
        upserts.push(agent);
      }
    }
    const removeIds: string[] = [];
    if (confirmed) for (const id of Object.keys(nextAgents)) if (!seen.has(id)) {
      delete nextAgents[id];
      removeIds.push(id);
    }
    const handoffs = visibleHandoffs(old.handoffs, nextAgents);
    if (!upserts.length && !removeIds.length && handoffs.length === old.handoffs.length) return;
    const revision = old.revision + 1;
    const generatedAtMs = Date.now();
    this.publish({ type: 'patch', schemaVersion: 1, epoch: old.epoch, baseRevision: old.revision,
      revision, generatedAtMs, upserts, removeIds,
      ...(handoffs.length !== old.handoffs.length ? { handoffs } : {}) },
      { ...old, revision, generatedAtMs, agents: nextAgents, handoffs });
  }
  /** Admit one already visible session without asserting roster membership changes. */
  upsertAgent(agent: FloorAgent): void {
    const old = this.state;
    if (!old.agents[agent.id] || JSON.stringify(old.agents[agent.id]) === JSON.stringify(agent)) return;
    const revision = old.revision + 1, generatedAtMs = Date.now();
    const agents = { ...old.agents, [agent.id]: agent };
    const handoffs = visibleHandoffs(old.handoffs, agents);
    this.publish({ type: 'patch', schemaVersion: 1, epoch: old.epoch, baseRevision: old.revision,
      revision, generatedAtMs, upserts: [agent], removeIds: [],
      ...(handoffs.length !== old.handoffs.length ? { handoffs } : {}) },
      { ...old, revision, generatedAtMs, agents, handoffs });
  }
  /** A terminal event can remove only its verified run; concurrent runs remain active. */
  setRunTerminal(id: string, sessionId: string, runId: string, outcome: RunOutcome | 'yielded', seq: number, observedAtMs: number): boolean {
    const old = this.state;
    const agent = old.agents[id];
    if (!agent || agent.freshness !== 'fresh' || agent.session.sessionId !== sessionId) return false;
    const next = withRunTerminal(agent, runId, outcome, seq, observedAtMs);
    if (!next) return false;
    this.upsertAgent(next);
    return true;
  }
  setCompacting(id: string, sessionId: string, operationId: string, compacting: boolean,
    sourceAtMs: number, observedAtMs: number): boolean {
    const agent = this.state.agents[id];
    if (!agent || agent.freshness !== 'fresh' || agent.session.sessionId !== sessionId) return false;
    this.upsertAgent({ ...agent, work: { ...agent.work, compacting,
      evidence: [...agent.work.evidence.slice(-7), { source: 'operation_event',
        reference: `${operationId}:${compacting ? 'start' : 'end'}`, sourceAtMs, observedAtMs }] } });
    return true;
  }
  /** Ignore late card replies from a replaced or no longer visible session. */
  setProgress(id: string, sessionId: string | null, progress: FloorProgress | null): boolean {
    const old = this.state;
    const agent = old.agents[id];
    if (!agent || agent.session.sessionId !== sessionId || agent.freshness !== 'fresh') return false;
    if (JSON.stringify(agent.progress) === JSON.stringify(progress)) return true;
    const next = { ...agent, progress };
    const revision = old.revision + 1, generatedAtMs = Date.now();
    const agents = { ...old.agents, [id]: next };
    this.publish({ type: 'patch', schemaVersion: 1, epoch: old.epoch, baseRevision: old.revision,
      revision, generatedAtMs, upserts: [next], removeIds: [] }, { ...old, revision, generatedAtMs, agents });
    return true;
  }
  /** A progress-read permission denial removes every card from all browser projections. */
  revokeProgressAccess(): void {
    const old = this.state;
    const upserts = Object.values(old.agents).filter(agent => agent.progress !== null)
      .map(agent => ({ ...agent, progress: null }));
    if (!upserts.length && old.capabilities.progressCard === 'forbidden') return;
    const agents = { ...old.agents } as Record<string, FloorAgent>;
    for (const agent of upserts) agents[agent.id] = agent;
    const capabilities = { ...old.capabilities, progressCard: 'forbidden' as const };
    const revision = old.revision + 1, generatedAtMs = Date.now();
    this.publish({ type: 'patch', schemaVersion: 1, epoch: old.epoch, baseRevision: old.revision,
      revision, generatedAtMs, upserts, removeIds: [], capabilities },
    { ...old, revision, generatedAtMs, agents, capabilities });
  }
  markStale(): void {
    const old = this.state;
    const upserts = Object.values(old.agents).map(uncertainAgent).filter(agent => agent !== old.agents[agent.id]);
    if (!upserts.length && !old.handoffs.length) return;
    const agents = { ...old.agents } as Record<string, FloorAgent>;
    for (const agent of upserts) agents[agent.id] = agent;
    const revision = old.revision + 1;
    const generatedAtMs = Date.now();
    this.publish({ type: 'patch', schemaVersion: 1, epoch: old.epoch, baseRevision: old.revision,
      revision, generatedAtMs, upserts, removeIds: [], handoffs: [] },
      { ...old, revision, generatedAtMs, agents, handoffs: [] });
  }
  markAgentStale(id: string): void {
    const old = this.state;
    const agent = old.agents[id];
    if (!agent) return;
    const next = uncertainAgent(agent);
    const handoffs = old.handoffs.filter(handoff => handoff.fromId !== id && handoff.toId !== id);
    if (next === agent && handoffs.length === old.handoffs.length) return;
    const revision = old.revision + 1, generatedAtMs = Date.now();
    this.publish({ type: 'patch', schemaVersion: 1, epoch: old.epoch, baseRevision: old.revision,
      revision, generatedAtMs, upserts: next === agent ? [] : [next], removeIds: [],
      ...(handoffs.length !== old.handoffs.length ? { handoffs } : {}) },
      { ...old, revision, generatedAtMs, agents: { ...old.agents, [id]: next }, handoffs });
  }
  /** A denied observer read invalidates the entire projected view immediately. */
  revokeAccess(reason: string): void {
    const old = this.state;
    const connection: FloorConnection = { mode: 'none', state: 'auth_required',
      lastConfirmedAtMs: old.connection.lastConfirmedAtMs, reason };
    const capabilities = { ...old.capabilities, sessionList: 'forbidden' as const };
    const revision = old.revision + 1;
    const generatedAtMs = Date.now();
    this.publish({ type: 'patch', schemaVersion: 1, epoch: old.epoch, baseRevision: old.revision,
      revision, generatedAtMs, upserts: [], removeIds: Object.keys(old.agents), connection,
      capabilities, handoffs: [] }, { ...old, revision, generatedAtMs, agents: {}, handoffs: [], connection, capabilities });
  }
  setConnection(connection: FloorConnection): void {
    const old = this.state;
    const lost = connection.state === 'offline' || connection.state === 'auth_required';
    const clearEffects = connection.state !== 'live';
    const agents = lost
      ? Object.fromEntries(Object.entries(old.agents).map(([id, agent]) => [id, { ...agent, freshness: 'stale' as const,
        work: { ...agent.work, phase: null, hasActiveRun: null, activeRunIds: null,
          tool: null, attention: null, compacting: null, looping: null } }]))
      : old.agents;
    const upserts = Object.values(agents).filter(agent => agent !== old.agents[agent.id]);
    const revision = old.revision + 1;
    const generatedAtMs = Date.now();
    this.publish({ type: 'patch', schemaVersion: 1, epoch: old.epoch, baseRevision: old.revision,
      revision, generatedAtMs, upserts, removeIds: [], connection,
      ...(clearEffects ? { handoffs: [] } : {}) },
      { ...old, revision, generatedAtMs, agents, connection,
        handoffs: clearEffects ? [] : old.handoffs });
  }
  setCapability(name: keyof FloorState['capabilities'], value: FloorState['capabilities'][typeof name]): void {
    const old = this.state;
    if (old.capabilities[name] === value) return;
    const capabilities = { ...old.capabilities, [name]: value };
    const revision = old.revision + 1;
    const generatedAtMs = Date.now();
    this.publish({ type: 'patch', schemaVersion: 1, epoch: old.epoch, baseRevision: old.revision,
      revision, generatedAtMs, upserts: [], removeIds: [], capabilities },
      { ...old, revision, generatedAtMs, capabilities });
  }
}
