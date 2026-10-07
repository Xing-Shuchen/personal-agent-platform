import { createHash } from 'node:crypto';
import type { FloorAgent, FloorStatus, ObservationEvidence, RunOutcome } from '@pap/floor-contract';

/** The published row schema has optional fields; live-only fields are checked before use. */
export type SessionRow = Record<string, unknown> & { key: string };
export type DisplayBinding = Readonly<{ name?: string; avatarKey?: string }>;
const string = (v: unknown): string | null => typeof v === 'string' ? v : null;
const number = (v: unknown): number | null => typeof v === 'number' && Number.isFinite(v) ? v : null;
const bool = (v: unknown): boolean | null => typeof v === 'boolean' ? v : null;
const short = (s: string) => s.length > 48 ? `${s.slice(0, 47)}…` : s;

export function floorId(gatewayId: string, ownerId: string | null, key: string): string {
  const raw = JSON.stringify([gatewayId, ownerId, key]);
  return `session_${createHash('sha256').update(raw).digest('base64url').slice(0, 22)}`;
}

function outcome(row: SessionRow): RunOutcome | null {
  const status = string(row.status);
  const runId = string(row.lastRunId);
  if (!runId || !string(row.sessionId)) return null;
  const result = status === 'done' ? 'success' : status === 'failed' ? 'error' :
    status === 'interrupted' || status === 'killed' ? 'cancelled' : status === 'timeout' ? 'timeout' : null;
  if (!result) return null;
  // A row terminal status is authoritative only for this current session instance.
  // Gateway error text is unconstrained and may contain private request or provider details.
  return { runId, result, endedAtMs: null, message: null };
}

function status(row: SessionRow, active: readonly string[] | null, hasActive: boolean | null, latest: RunOutcome | null): FloorStatus {
  if (active?.length || hasActive === true || (active === null && hasActive === null && row.status === 'running')) return 'running';
  if (row.status === 'queued') return 'queued';
  if (latest?.result === 'success') return 'completed';
  if (latest?.result === 'error' || latest?.result === 'timeout') return 'error';
  if (latest?.result === 'cancelled') return 'stopped';
  if (active?.length === 0 || hasActive === false) return 'idle';
  return 'unknown';
}

/** Produce only whitelisted metadata. Raw messages, paths, tool arguments and tokens never cross this boundary. */
export function normalizeSessionRow(row: SessionRow, gatewayId: string, observedAtMs: number,
  binding: DisplayBinding = {}, previous?: FloorAgent, complete = true): FloorAgent {
  if (!row.key || !gatewayId) throw new Error('session key and gateway ID required');
  const owner = string(row.agentId);
  const id = floorId(gatewayId, owner, row.key);
  const sessionId = string(row.sessionId);
  const sameInstance = sessionId !== null && previous?.session.sessionId === sessionId && previous?.id === id;
  const active = Object.hasOwn(row, 'activeRunIds')
    ? Array.isArray(row.activeRunIds) && row.activeRunIds.every(x => typeof x === 'string') ? [...row.activeRunIds] : null
    : complete ? null : sameInstance ? previous!.work.activeRunIds : null;
  const hasActive = Object.hasOwn(row, 'hasActiveRun') ? bool(row.hasActiveRun) :
    complete ? null : sameInstance ? previous!.work.hasActiveRun : null;
  const latest = outcome(row) ?? (complete || !sameInstance ? null : previous!.work.latestOutcome);
  const nextStatus = status(row, active, hasActive, latest);
  const evidence: ObservationEvidence[] = [{ source: complete ? 'session_snapshot' : 'session_delta', reference: `${id}:${observedAtMs}`, sourceAtMs: number(row.snapshotAt) ?? number(row.updatedAt), observedAtMs }];
  return {
    id, session: { gatewayId, key: row.key, agentId: owner, sessionId },
    name: short(binding.name ?? string(row.label) ?? string(row.autoLabel) ?? `会话 · ${id.slice(-8)}`),
    kind: string(row.kind), avatarKey: binding.avatarKey ?? id,
    relation: { parentId: null, childIds: null, runningVisibleChildren: null },
    work: {
      status: nextStatus, phase: nextStatus === 'running' ? 'executing' : null,
      hasActiveRun: hasActive, activeRunIds: active, tool: null, attention: null,
      compacting: null, looping: null, latestOutcome: latest, summary: null, summarySource: null,
      evidence
    },
    model: { selected: string(row.model), selectedProvider: string(row.modelProvider), active: string(row.activeModel), activeProvider: string(row.activeModelProvider) },
    usage: { inputTokens: number(row.inputTokens), outputTokens: number(row.outputTokens), totalTokens: number(row.totalTokens), totalTokensFresh: bool(row.totalTokensFresh), contextTokens: number(row.contextTokens) },
    progress: sameInstance ? previous!.progress : null, lastMessagePreview: null,
    metadataUpdatedAtMs: number(row.updatedAt), lastActivityAtMs: number(row.lastActivityAt),
    lastInteractionAtMs: number(row.lastInteractionAt), lastVerifiedAtMs: observedAtMs, freshness: 'fresh'
  };
}
