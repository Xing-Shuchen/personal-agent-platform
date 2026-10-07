export type * from './types.ts';
import type { CapabilityName, CapabilityState, FloorAgent, FloorState, FloorUpdate } from './types.ts';

const capabilityNames: readonly CapabilityName[] = ['sessionList', 'sessionEvents', 'runEvents', 'toolEvents', 'blockingInput', 'progressCard', 'compaction', 'loopDetection', 'handoff'];
const capabilityStates: readonly CapabilityState[] = ['available', 'partial', 'unsupported', 'forbidden', 'unverified'];
const statuses = ['running', 'waiting_input', 'error', 'completed', 'idle', 'queued', 'stopped', 'unknown'];
const freshnesses = ['fresh', 'stale', 'unknown'];
const connectionModes = ['subscription', 'polling', 'none'];
const connectionStates = ['connecting', 'live', 'degraded', 'offline', 'auth_required'];
const isRecord = (v: unknown): v is Record<string, unknown> => v !== null && typeof v === 'object' && !Array.isArray(v) &&
  (Object.getPrototypeOf(v) === Object.prototype || Object.getPrototypeOf(v) === null);
const keysOnly = (v: Record<string, unknown>, keys: readonly string[]) =>
  Object.keys(v).every(key => keys.includes(key));
const finite = (v: unknown): v is number => typeof v === 'number' && Number.isFinite(v);
const nullableString = (v: unknown) => v === null || typeof v === 'string';
const nullableTime = (v: unknown) => v === null || finite(v);
const strings = (v: unknown): v is string[] => Array.isArray(v) && v.every(x => typeof x === 'string');
const nullableStrings = (v: unknown) => v === null || strings(v);
const encoder = new TextEncoder();
const withinBytes = (value: string, limit: number) => encoder.encode(value).length <= limit;
const boundedOptionalText = (value: unknown, limit: number) =>
  value === null || typeof value === 'string' && withinBytes(value, limit);
const safeToolName = (value: unknown): value is string => typeof value === 'string' && value.length > 0 && value.length <= 80 &&
  /^[A-Za-z_][A-Za-z0-9_.:-]*$/.test(value) && !value.includes('..');

export function isFloorAgent(v: unknown): v is FloorAgent {
  if (!isRecord(v) || !keysOnly(v, ['id','session','name','kind','avatarKey','relation','work','model','usage','progress','lastMessagePreview','metadataUpdatedAtMs','lastActivityAtMs','lastInteractionAtMs','lastVerifiedAtMs','freshness']) ||
      typeof v.id !== 'string' || !isRecord(v.session) || !isRecord(v.work) ||
      !isRecord(v.relation) || !isRecord(v.model) || !isRecord(v.usage)) return false;
  const { session: s, work: w, relation: r, model: m, usage: u } = v;
  return keysOnly(s, ['gatewayId','key','agentId','sessionId']) &&
    keysOnly(r, ['parentId','childIds','runningVisibleChildren']) &&
    keysOnly(w, ['status','phase','hasActiveRun','activeRunIds','tool','attention','compacting','looping','latestOutcome','summary','summarySource','evidence']) &&
    keysOnly(m, ['selected','selectedProvider','active','activeProvider']) &&
    keysOnly(u, ['inputTokens','outputTokens','totalTokens','totalTokensFresh','contextTokens']) &&
    typeof s.gatewayId === 'string' && typeof s.key === 'string' && nullableString(s.agentId) && nullableString(s.sessionId) &&
    typeof v.name === 'string' && nullableString(v.kind) && typeof v.avatarKey === 'string' &&
    nullableString(r.parentId) && nullableStrings(r.childIds) && (r.runningVisibleChildren === null || finite(r.runningVisibleChildren)) &&
    statuses.includes(String(w.status)) && (w.phase === null || ['executing','reading','thinking','finishing','waiting_child'].includes(String(w.phase))) &&
    (w.hasActiveRun === null || typeof w.hasActiveRun === 'boolean') && nullableStrings(w.activeRunIds) &&
    (w.tool === null || (isRecord(w.tool) && keysOnly(w.tool, ['name','callId','phase']) && safeToolName(w.tool.name) && nullableString(w.tool.callId) && ['start','update','end'].includes(String(w.tool.phase)))) &&
    (w.attention === null || (Array.isArray(w.attention) && w.attention.every(a => isRecord(a) && keysOnly(a, ['id','kind','runId','blocking','label']) && typeof a.id === 'string' && ['question','approval'].includes(String(a.kind)) && nullableString(a.runId) && (a.blocking === null || typeof a.blocking === 'boolean') && typeof a.label === 'string' && withinBytes(a.label, 256)))) &&
    (w.compacting === null || typeof w.compacting === 'boolean') && (w.looping === null || typeof w.looping === 'boolean') &&
    (w.latestOutcome === null || (isRecord(w.latestOutcome) && keysOnly(w.latestOutcome, ['runId','result','endedAtMs','message']) && nullableString(w.latestOutcome.runId) && ['success','error','cancelled','timeout'].includes(String(w.latestOutcome.result)) && nullableTime(w.latestOutcome.endedAtMs) && boundedOptionalText(w.latestOutcome.message, 256))) &&
    boundedOptionalText(w.summary, 512) && (w.summary === null) === (w.summarySource === null) &&
    (w.summarySource === null || ['tool','narration','progress_card','visible_message'].includes(String(w.summarySource))) &&
    Array.isArray(w.evidence) && w.evidence.every(e => isRecord(e) && keysOnly(e, ['source','reference','sourceAtMs','observedAtMs']) && ['session_snapshot','session_delta','run_event','tool_event','input_event','operation_event','progress_card'].includes(String(e.source)) && typeof e.reference === 'string' && nullableTime(e.sourceAtMs) && finite(e.observedAtMs)) &&
    ['selected','selectedProvider','active','activeProvider'].every(k => nullableString(m[k])) &&
    ['inputTokens','outputTokens','totalTokens','contextTokens'].every(k => u[k] === null || finite(u[k])) &&
    (u.totalTokensFresh === null || typeof u.totalTokensFresh === 'boolean') &&
    (v.progress === null || (isRecord(v.progress) && keysOnly(v.progress, ['revision','updatedAtMs','markdown','steps']) &&
      Number.isSafeInteger(v.progress.revision) && Number(v.progress.revision) >= 1 && Number.isSafeInteger(v.progress.updatedAtMs) &&
      (v.progress.markdown === null || (typeof v.progress.markdown === 'string' && withinBytes(v.progress.markdown, 8192))) &&
      (v.progress.steps === null || (Array.isArray(v.progress.steps) && v.progress.steps.length <= 50 &&
        v.progress.steps.filter(p => isRecord(p) && p.status === 'in_progress').length <= 1 &&
        v.progress.steps.every(p => isRecord(p) && keysOnly(p, ['text','status']) && typeof p.text === 'string' &&
          p.text.length > 0 && withinBytes(p.text, 512) && ['pending','in_progress','completed'].includes(String(p.status))))))) &&
    boundedOptionalText(v.lastMessagePreview, 512) && nullableTime(v.metadataUpdatedAtMs) && nullableTime(v.lastActivityAtMs) && nullableTime(v.lastInteractionAtMs) && nullableTime(v.lastVerifiedAtMs) && freshnesses.includes(String(v.freshness));
}

export function isFloorState(v: unknown): v is FloorState {
  if (!isRecord(v) || !keysOnly(v, ['schemaVersion','epoch','revision','generatedAtMs','connection','capabilities','agents','handoffs']) ||
      v.schemaVersion !== 1 || typeof v.epoch !== 'string' || !Number.isSafeInteger(v.revision) || !finite(v.generatedAtMs) || !isRecord(v.connection) || !isRecord(v.capabilities) || !isRecord(v.agents) || !Array.isArray(v.handoffs)) return false;
  const c = v.connection;
  const caps = v.capabilities;
  const agents = v.agents as Record<string, unknown>;
  return keysOnly(c, ['mode','state','lastConfirmedAtMs','reason']) && keysOnly(caps, capabilityNames) &&
    connectionModes.includes(String(c.mode)) && connectionStates.includes(String(c.state)) && nullableTime(c.lastConfirmedAtMs) && nullableString(c.reason) &&
    capabilityNames.every(k => capabilityStates.includes(caps[k] as CapabilityState)) &&
    Object.entries(agents).every(([id,a]) => isFloorAgent(a) && a.id === id) &&
    v.handoffs.length <= 100 && new Set(v.handoffs.map(h => isRecord(h) ? h.id : null)).size === v.handoffs.length &&
    v.handoffs.every(h => isRecord(h) && keysOnly(h, ['id','fromId','toId','kind','observedAtMs','expiresAtMs','evidenceReference']) &&
      typeof h.id === 'string' && h.id.length > 0 && h.id.length <= 128 &&
      typeof h.fromId === 'string' && typeof h.toId === 'string' && h.fromId !== h.toId &&
      Object.hasOwn(agents, h.fromId) && Object.hasOwn(agents, h.toId) &&
      ['request','result','message'].includes(String(h.kind)) &&
      finite(h.observedAtMs) && finite(h.expiresAtMs) && h.expiresAtMs > h.observedAtMs &&
      h.expiresAtMs - h.observedAtMs <= 3000 &&
      typeof h.evidenceReference === 'string' && h.evidenceReference.length > 0 &&
      h.evidenceReference.length <= 128 && /^[A-Za-z0-9:_-]+$/.test(h.evidenceReference));
}

export function applyFloorUpdate(current: FloorState | null, update: FloorUpdate): FloorState {
  if (update.type === 'snapshot') {
    if (!isRecord(update) || !keysOnly(update, ['type','state'])) throw new Error('invalid FloorState snapshot envelope');
    if (!isFloorState(update.state)) throw new Error('invalid FloorState snapshot');
    return update.state;
  }
  if (!isRecord(update) || update.type !== 'patch' || !keysOnly(update, ['type','schemaVersion','epoch','baseRevision','revision','generatedAtMs','upserts','removeIds','connection','capabilities','handoffs'])) throw new Error('invalid FloorState patch envelope');
  if (!current || !isFloorState(current) || update.schemaVersion !== 1 || update.epoch !== current.epoch || update.baseRevision !== current.revision || update.revision <= update.baseRevision || !Number.isSafeInteger(update.revision)) throw new Error('FloorState revision gap; reload snapshot');
  if (!finite(update.generatedAtMs) || !Array.isArray(update.upserts) || !update.upserts.every(isFloorAgent) || !strings(update.removeIds)) throw new Error('invalid FloorState patch');
  const upsertIds = update.upserts.map(agent => agent.id);
  if (new Set(upsertIds).size !== upsertIds.length || new Set(update.removeIds).size !== update.removeIds.length ||
      update.removeIds.some(id => upsertIds.includes(id))) throw new Error('conflicting FloorState patch IDs');
  const agents = Object.assign(Object.create(null) as Record<string, FloorAgent>, current.agents);
  for (const id of update.removeIds) delete agents[id];
  for (const agent of update.upserts) agents[agent.id] = agent;
  const next: FloorState = { ...current, revision: update.revision, generatedAtMs: update.generatedAtMs, agents, connection: update.connection ?? current.connection, capabilities: update.capabilities ?? current.capabilities, handoffs: update.handoffs ?? current.handoffs };
  if (!isFloorState(next)) throw new Error('invalid patched FloorState');
  return next;
}

export function emptyFloorState(epoch: string, now = Date.now()): FloorState {
  const capabilities = Object.fromEntries(capabilityNames.map(name => [name, 'unverified'])) as FloorState['capabilities'];
  return { schemaVersion: 1, epoch, revision: 0, generatedAtMs: now, connection: { mode: 'none', state: 'connecting', lastConfirmedAtMs: null, reason: null }, capabilities, agents: {}, handoffs: [] };
}
