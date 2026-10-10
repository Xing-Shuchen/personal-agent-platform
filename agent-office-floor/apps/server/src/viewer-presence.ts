/** Ephemeral browser visibility hints. Absence and expired hints mean no visible page. */
export class ViewerPresence {
  private viewers = new Map<string, number>();
  constructor(private readonly onChange: (visible: boolean) => void, private readonly ttlMs = 45000) {}
  report(id: string, visible: boolean, now = Date.now()): void {
    const before = this.visible;
    if (visible) this.viewers.set(id, now + this.ttlMs);
    else this.viewers.delete(id);
    if (before !== this.visible) this.onChange(this.visible);
  }
  expire(now = Date.now()): void {
    const before = this.visible;
    for (const [id, until] of this.viewers) if (until <= now) this.viewers.delete(id);
    if (before !== this.visible) this.onChange(this.visible);
  }
  get visible(): boolean { return this.viewers.size > 0; }
}
