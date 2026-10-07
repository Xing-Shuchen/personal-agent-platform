import type { FloorAgent, FloorProgress } from '@pap/floor-contract';

const record = (value: unknown): value is Record<string, unknown> =>
  value !== null && typeof value === 'object' && !Array.isArray(value);
const integer = (value: unknown): value is number => Number.isSafeInteger(value) && Number(value) >= 0;
const stepStatus = (value: unknown): value is 'pending'|'in_progress'|'completed' =>
  value === 'pending' || value === 'in_progress' || value === 'completed';

/** The response's agent-qualified display key is intentionally discarded. */
export function normalizeProgressCard(reply: unknown): FloorProgress | null {
  if (!record(reply) || !Object.hasOwn(reply, 'card')) throw new Error('invalid progress card response');
  const card = reply.card;
  if (card === null) return null;
  if (!record(card) || !integer(card.revision) || card.revision < 1 || !integer(card.updatedAt) ||
      typeof card.sessionKey !== 'string' || !card.sessionKey) throw new Error('invalid progress card');
  const markdown = card.markdown === undefined ? null : card.markdown;
  if (markdown !== null && (typeof markdown !== 'string' || Buffer.byteLength(markdown, 'utf8') > 8192))
    throw new Error('invalid progress markdown');
  const steps = card.steps === undefined ? null : card.steps;
  if (steps !== null && (!Array.isArray(steps) || steps.length > 50 || !steps.every(step =>
      record(step) && typeof step.step === 'string' && step.step.length > 0 &&
      Buffer.byteLength(step.step, 'utf8') <= 512 && stepStatus(step.status)) ||
      steps.filter(step => step.status === 'in_progress').length > 1)) throw new Error('invalid progress steps');
  return { revision: card.revision, updatedAtMs: card.updatedAt,
    markdown, steps: steps === null ? null : steps.map(step => ({ text: step.step, status: step.status })) };
}

/** Independently upgraded clients must not send an owner unless Gateway declares this contract. */
export function canReadProgress(features: { methods: readonly string[]; capabilities?: readonly string[] }): boolean {
  return features.methods.includes('progressCard.get') &&
    (features.capabilities ?? []).includes('progress-card-agent-scope-v1');
}

export function progressReadParams(agent: FloorAgent, supported: boolean): { sessionKey: string; agentId: string } | null {
  if (!supported || !agent.session.key || !agent.session.agentId) return null;
  return { sessionKey: agent.session.key, agentId: agent.session.agentId };
}

/** A card must be scoped to the exact owner and session requested. Aliases that
 * the Gateway resolves to a different key fail closed until their mapping is verified. */
export function progressCardMatchesRequest(reply: unknown, params: { sessionKey: string; agentId: string }): boolean {
  if (!record(reply) || !Object.hasOwn(reply, 'card')) return false;
  if (reply.card === null) return true;
  if (!record(reply.card) || typeof reply.card.sessionKey !== 'string') return false;
  const prefix = `agent:${params.agentId}:`;
  const expected = params.sessionKey.startsWith('agent:') ? params.sessionKey : `${prefix}${params.sessionKey}`;
  return expected.startsWith(prefix) && reply.card.sessionKey === expected;
}
