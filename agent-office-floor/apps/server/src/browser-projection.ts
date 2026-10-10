import { createHmac, randomBytes } from 'node:crypto';
import type { FloorAgent, FloorHandoff, FloorState, FloorUpdate } from '@pap/floor-contract';

/** Keep composite run and event identifiers on the server while preserving FloorState session identity. */
export class BrowserProjection {
  constructor(private readonly secret: Buffer = randomBytes(32)) {}

  private opaque(kind: string, value: string): string {
    return `${kind}_${createHmac('sha256', this.secret).update(kind).update('\0').update(value).digest('base64url').slice(0, 22)}`;
  }

  private optional(kind: string, value: string | null): string | null {
    return value === null ? null : this.opaque(kind, value);
  }

  agent(agent: FloorAgent): FloorAgent {
    const work = agent.work;
    return { ...agent,
      work: { ...work,
        activeRunIds: work.activeRunIds?.map(id => this.opaque('run', id)) ?? null,
        latestOutcome: work.latestOutcome ? { ...work.latestOutcome,
          runId: this.optional('run', work.latestOutcome.runId) } : null,
        tool: work.tool ? { ...work.tool, callId: this.optional('call', work.tool.callId) } : null,
        attention: work.attention?.map(item => ({ ...item,
          id: this.opaque('attention', item.id), runId: this.optional('run', item.runId) })) ?? null,
        evidence: work.evidence.map(item => ({ ...item,
          reference: this.opaque('evidence', item.reference) }))
      }
    };
  }

  private handoff(handoff: FloorHandoff): FloorHandoff {
    return { ...handoff, id: this.opaque('handoff', handoff.id),
      evidenceReference: this.opaque('evidence', handoff.evidenceReference) };
  }

  state(state: FloorState): FloorState {
    return { ...state,
      agents: Object.fromEntries(Object.entries(state.agents).map(([id, agent]) => [id, this.agent(agent)])),
      handoffs: state.handoffs.map(item => this.handoff(item)) };
  }

  update(update: FloorUpdate): FloorUpdate {
    return update.type === 'snapshot' ? { type: 'snapshot', state: this.state(update.state) } :
      { ...update, upserts: update.upserts.map(agent => this.agent(agent)),
        ...(update.handoffs ? { handoffs: update.handoffs.map(item => this.handoff(item)) } : {}) };
  }
}
