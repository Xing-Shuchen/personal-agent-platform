import type { SessionRow } from './session.ts';

const sampledAt = (row: SessionRow): number | null =>
  typeof row.snapshotAt === 'number' && Number.isFinite(row.snapshotAt) ? row.snapshotAt : null;

/** Later request wins ties or absent timestamps; older sampled rows never replace newer ones. */
export function preferCandidateRow(current: SessionRow, candidate: SessionRow): boolean {
  const oldTime = sampledAt(current), newTime = sampledAt(candidate);
  return oldTime === null || newTime === null || newTime >= oldTime;
}
