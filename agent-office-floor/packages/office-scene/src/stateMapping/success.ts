import type { FloorAgent } from '@pap/floor-contract';
/** Transient success belongs to one session instance and one verified run. */
export class SuccessLedger {
  private initialized = false;
  private instanceId: string | null = null;
  private seen = new Set<string>();
  observe(agent: FloorAgent): boolean {
    const instance = agent.session.sessionId;
    const run = agent.work.latestOutcome?.result === 'success' ? agent.work.latestOutcome.runId : null;
    const key = instance && run ? `${instance}:${run}` : null;
    if (!this.initialized || this.instanceId !== instance) {
      this.initialized = true; this.instanceId = instance; this.seen.clear();
      if (key) this.seen.add(key);
      return false;
    }
    if (!key || this.seen.has(key)) return false;
    // A terminal row can arrive before the direct activity set has cleared.
    // Keep that outcome pending until it is safe to celebrate.
    if (agent.freshness !== 'fresh') { this.seen.add(key); return false; }
    if (agent.work.status !== 'completed' || agent.work.activeRunIds?.length !== 0 ||
        agent.work.hasActiveRun === true) return false;
    this.seen.add(key);
    return true;
  }
}
