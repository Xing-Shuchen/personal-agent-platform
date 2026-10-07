import type { FloorState, FloorUpdate } from '@pap/floor-contract';
import { visualState } from '@pap/office-scene';

/** Earliest new structured receipt changing a status label on the current scene page. */
export function visibleEventReceiptAt(before: FloorState | null,
  update: FloorUpdate, visibleIds: ReadonlySet<string>): number | null {
  if (!before || update.type !== 'patch' || !visibleIds.size) return null;
  let earliest: number | null = null;
  for (const next of update.upserts) {
    if (!visibleIds.has(next.id)) continue;
    const previous = before.agents[next.id];
    if (!previous || visualState(previous).label === visualState(next).label) continue;
    const prior = new Set(previous.work.evidence.map(e => `${e.source}:${e.reference}:${e.observedAtMs}`));
    for (const evidence of next.work.evidence) {
      if (!['run_event', 'tool_event', 'operation_event'].includes(evidence.source) ||
        prior.has(`${evidence.source}:${evidence.reference}:${evidence.observedAtMs}`) ||
        evidence.observedAtMs <= 0 || evidence.observedAtMs > update.generatedAtMs) continue;
      earliest = earliest === null ? evidence.observedAtMs : Math.min(earliest, evidence.observedAtMs);
    }
  }
  return earliest;
}
