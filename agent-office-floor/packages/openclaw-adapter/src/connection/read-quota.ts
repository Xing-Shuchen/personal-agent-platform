type Queued = { start: () => void; cancel: () => void };

/** One observer's shared RPC budget: ten starts per second, four in flight. */
export class ReadQuota {
  private queue: Queued[] = [];
  private starts: number[] = [];
  private active = 0;
  private timer: ReturnType<typeof setTimeout> | null = null;
  private closed = false;
  constructor(recentStarts: readonly number[] = []) {
    this.starts = recentStarts.filter(start => Date.now() - start < 1000);
  }

  recentStarts(): readonly number[] { return [...this.starts]; }
  queuedCount(): number { return this.queue.length; }

  run<T>(work: () => Promise<T>): Promise<T> {
    return new Promise<T>((resolve, reject) => {
      if (this.closed) { reject(new Error('read quota closed')); return; }
      this.queue.push({
        start: () => {
          this.active++;
          this.starts.push(Date.now());
          void Promise.resolve().then(() => {
            if (this.closed) throw new Error('read quota closed');
            return work();
          }).then(resolve, reject).finally(() => {
            this.active--; this.pump();
          });
        },
        cancel: () => reject(new Error('read quota closed'))
      });
      this.pump();
    });
  }

  close(): void {
    if (this.closed) return;
    this.closed = true;
    if (this.timer) clearTimeout(this.timer);
    for (const item of this.queue.splice(0)) item.cancel();
  }

  private pump(): void {
    if (this.closed) return;
    if (this.timer) { clearTimeout(this.timer); this.timer = null; }
    const now = Date.now();
    this.starts = this.starts.filter(start => now - start < 1000);
    while (this.queue.length && this.active < 4 && this.starts.length < 10) {
      this.queue.shift()!.start();
    }
    if (this.queue.length && this.active < 4 && this.starts.length >= 10) {
      const delay = Math.max(1, 1000 - (Date.now() - this.starts[0]) + 1);
      this.timer = setTimeout(() => { this.timer = null; this.pump(); }, delay);
    }
  }
}
