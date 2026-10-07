import type { FloorHandoff, FloorState } from '@pap/floor-contract';

/** Admit only new, still-visible communication; initial and rebuilt scenes never replay history. */
export class HandoffLedger {
  private epoch: string | null = null;
  private readonly seen = new Set<string>();

  baseline(state: FloorState): void {
    this.epoch = state.epoch;
    for (const handoff of state.handoffs) this.seen.add(handoff.id);
  }

  take(state: FloorState, visibleIds: ReadonlySet<string>, nowMs: number): readonly FloorHandoff[] {
    if (this.epoch !== state.epoch) {
      this.baseline(state);
      return [];
    }
    const admitted: FloorHandoff[] = [];
    for (const handoff of state.handoffs) {
      if (this.seen.has(handoff.id)) continue;
      this.seen.add(handoff.id);
      if (state.connection.state !== 'live' ||
          !['available', 'partial'].includes(state.capabilities.handoff) ||
          !handoff.evidenceReference || handoff.observedAtMs > nowMs ||
          handoff.expiresAtMs <= nowMs || handoff.expiresAtMs - handoff.observedAtMs > 3000 ||
          handoff.fromId === handoff.toId ||
          !visibleIds.has(handoff.fromId) || !visibleIds.has(handoff.toId) ||
          state.agents[handoff.fromId]?.freshness !== 'fresh' ||
          state.agents[handoff.toId]?.freshness !== 'fresh') continue;
      admitted.push(handoff);
    }
    return admitted;
  }
}
