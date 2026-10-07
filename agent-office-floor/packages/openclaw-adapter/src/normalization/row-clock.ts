import type { SessionRow } from './session.ts';

export type RowClock = Readonly<{ snapshotAt: number; requestOrder: number; sessionId: string }>;

/** An unclocked or unidentified event cannot replace an authoritative row. */
export function rowClock(row: SessionRow, requestOrder: number): RowClock | null {
  return typeof row.snapshotAt === 'number' && Number.isFinite(row.snapshotAt) &&
    typeof row.sessionId === 'string' && row.sessionId.length > 0
    ? { snapshotAt: row.snapshotAt, requestOrder, sessionId: row.sessionId } : null;
}

export function newerRow(current: RowClock | undefined, candidate: RowClock | null): boolean {
  if (!candidate) return false;
  if (!current || candidate.sessionId !== current.sessionId) return true;
  return candidate.snapshotAt > current.snapshotAt ||
    (candidate.snapshotAt === current.snapshotAt && candidate.requestOrder > current.requestOrder);
}
