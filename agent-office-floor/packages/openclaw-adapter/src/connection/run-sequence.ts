export type RunReceipt = Readonly<{ runId: string; seq: number }>;
export type RunSequenceResult = 'first' | 'next' | 'duplicate' | 'gap';

/** Agent payloads contain content as well as sequencing; retain only these two fields. */
export function runReceipt(payload: unknown): RunReceipt | null {
  if (!payload || typeof payload !== 'object' || Array.isArray(payload)) return null;
  const value = payload as Record<string, unknown>;
  return typeof value.runId === 'string' && value.runId.length > 0 &&
    typeof value.seq === 'number' && Number.isSafeInteger(value.seq) && value.seq >= 0
    ? { runId: value.runId, seq: value.seq } : null;
}

export function advanceRunSequence(previous: number | undefined, current: number): RunSequenceResult {
  if (previous === undefined) return 'first';
  if (current <= previous) return 'duplicate';
  return current === previous + 1 ? 'next' : 'gap';
}
