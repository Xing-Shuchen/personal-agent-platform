export type CompactReceipt = Readonly<{
  operationId: string; sessionKey: string; agentId: string | null;
  phase: 'start' | 'end'; ts: number;
}>;

export function initialCompactionCapability(events: readonly string[]): 'unverified' | 'unsupported' {
  return events.includes('session.operation') ? 'unverified' : 'unsupported';
}

/** The protocol event may also contain a free-form reason; it is never retained. */
export function compactReceipt(payload: unknown): CompactReceipt | null {
  if (!payload || typeof payload !== 'object' || Array.isArray(payload)) return null;
  const value = payload as Record<string, unknown>;
  if (value.operation !== 'compact' ||
    typeof value.operationId !== 'string' || !value.operationId ||
    typeof value.sessionKey !== 'string' || !value.sessionKey ||
    (value.agentId !== undefined && (typeof value.agentId !== 'string' || !value.agentId)) ||
    (value.phase !== 'start' && value.phase !== 'end') ||
    !Number.isSafeInteger(value.ts) || Number(value.ts) < 0) return null;
  return { operationId: value.operationId, sessionKey: value.sessionKey,
    agentId: typeof value.agentId === 'string' ? value.agentId : null,
    phase: value.phase, ts: value.ts as number };
}
