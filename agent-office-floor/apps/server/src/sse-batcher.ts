import type { FloorAgent, FloorUpdate } from '@pap/floor-contract';

type Patch = Extract<FloorUpdate, { type: 'patch' }>;

/** Collapse a burst of consecutive patches without changing the client's final state. */
export class SseBatcher {
  private pending: Patch | null = null;
  private timer: ReturnType<typeof setTimeout> | null = null;
  constructor(private readonly emit: (update: FloorUpdate) => void,
    private readonly delayMs = 100) {}

  push(update: FloorUpdate): void {
    if (update.type === 'snapshot') {
      this.clear();
      this.emit(update);
      return;
    }
    // Terminal, waiting, failure, lost access, and explicit removals bypass
    // ordinary row batching; a preceding patch must retain revision order.
    if (urgent(update)) {
      if (this.pending && this.pending.epoch === update.epoch &&
        this.pending.revision === update.baseRevision) {
        const merged = merge(this.pending, update);
        this.clear();
        this.emit(merged);
        return;
      }
      this.flush();
      this.emit(update);
      return;
    }
    if (this.pending && (this.pending.epoch !== update.epoch ||
      this.pending.revision !== update.baseRevision)) this.flush();
    this.pending = this.pending ? merge(this.pending, update) : update;
    if (!this.timer) this.timer = setTimeout(() => this.flush(), this.delayMs);
  }

  flush(): void {
    if (!this.pending) return;
    const update = this.pending;
    this.pending = null;
    if (this.timer) clearTimeout(this.timer);
    this.timer = null;
    this.emit(update);
  }

  close(): void { this.clear(); }

  private clear(): void {
    if (this.timer) clearTimeout(this.timer);
    this.timer = null;
    this.pending = null;
  }
}

function urgent(update: Patch): boolean {
  return update.removeIds.length > 0 ||
    update.connection?.state === 'auth_required' || update.connection?.state === 'offline' ||
    update.connection?.state === 'degraded' ||
    update.upserts.some(agent => agent.freshness === 'stale' ||
      ['waiting_input', 'error', 'completed', 'stopped'].includes(agent.work.status));
}

function merge(first: Patch, next: Patch): Patch {
  const changes = new Map<string, FloorAgent | null>();
  for (const agent of first.upserts) changes.set(agent.id, agent);
  for (const id of first.removeIds) changes.set(id, null);
  for (const agent of next.upserts) changes.set(agent.id, agent);
  for (const id of next.removeIds) changes.set(id, null);
  return { type: 'patch', schemaVersion: 1, epoch: next.epoch,
    baseRevision: first.baseRevision, revision: next.revision,
    generatedAtMs: next.generatedAtMs,
    upserts: [...changes.values()].filter((agent): agent is FloorAgent => agent !== null),
    removeIds: [...changes].filter(([, agent]) => agent === null).map(([id]) => id),
    connection: next.connection ?? first.connection,
    capabilities: next.capabilities ?? first.capabilities,
    handoffs: next.handoffs ?? first.handoffs };
}
