import { applyFloorUpdate } from '@pap/floor-contract';
import type { FloorState, FloorUpdate } from '@pap/floor-contract';

/** Keep a late HTTP response from rolling back a newer SSE or poll result. */
export function admitHttpSnapshot(current: FloorState | null, candidate: FloorState,
  requestEpoch: string | null): FloorState | null {
  if (!current) return requestEpoch === null ? candidate : current;
  if (candidate.epoch === current.epoch) return candidate.revision >= current.revision ? candidate : current;
  return current.epoch === requestEpoch ? candidate : current;
}

export function admitStreamUpdate(current: FloorState | null, update: FloorUpdate): FloorState {
  const candidate = applyFloorUpdate(current, update);
  return update.type === 'snapshot' && current && candidate.epoch === current.epoch &&
    candidate.revision < current.revision ? current : candidate;
}
