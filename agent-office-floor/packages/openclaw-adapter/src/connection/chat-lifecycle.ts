import { createSessionProjection, reduceSessionProjectionRunEvent } from '@openclaw/gateway-client';
import type { RunOutcome } from '@pap/floor-contract';

export type ChatReceipt = Readonly<{
  runId: string; sessionKey: string; agentId: string | null; seq: number;
  state: 'status' | 'delta' | 'final' | 'error' | 'aborted';
  stopReason: string | null; errorKind: string | null; yielded: boolean;
}>;

/** Only address, sequence and lifecycle fields cross from a potentially private chat event. */
export function chatReceipt(payload: unknown): ChatReceipt | null {
  if (!payload || typeof payload !== 'object' || Array.isArray(payload)) return null;
  const value = payload as Record<string, unknown>;
  if (typeof value.runId !== 'string' || !value.runId ||
      typeof value.sessionKey !== 'string' || !value.sessionKey ||
      !Number.isSafeInteger(value.seq) || Number(value.seq) < 0 ||
      !['status','delta','final','error','aborted'].includes(String(value.state)) ||
      (value.agentId !== undefined && (typeof value.agentId !== 'string' || !value.agentId))) return null;
  return { runId: value.runId, sessionKey: value.sessionKey,
    agentId: typeof value.agentId === 'string' ? value.agentId : null,
    seq: value.seq as number,
    state: value.state as ChatReceipt['state'],
    stopReason: typeof value.stopReason === 'string' ? value.stopReason : null,
    errorKind: typeof value.errorKind === 'string' ? value.errorKind : null,
    yielded: value.yielded === true };
}

/** The pinned SDK owns final/error/yielded semantics; omit message and error text. */
export function chatTerminal(receipt: ChatReceipt, observedAtMs: number): RunOutcome | 'yielded' | null {
  if (receipt.state === 'status' || receipt.state === 'delta') return null;
  const transition = reduceSessionProjectionRunEvent(createSessionProjection(), {
    runId: receipt.runId, seq: receipt.seq, state: receipt.state,
    stopReason: receipt.stopReason, errorKind: receipt.errorKind, yielded: receipt.yielded
  });
  const status = transition?.currentRun?.status;
  if (status === 'yielded') return 'yielded';
  const result = status === 'completed' ? 'success' : status === 'error' ? 'error' :
    status === 'aborted' ? 'cancelled' : status === 'timeout' ? 'timeout' : null;
  return result ? { runId: receipt.runId, result, endedAtMs: observedAtMs, message: null } : null;
}
