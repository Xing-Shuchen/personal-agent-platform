import type { FloorAgent } from '@pap/floor-contract';

/** Show each identity once before its next session, while keeping Feishu identities first. */
export function orderOfficeSessions(agents: readonly FloorAgent[], identityIds: readonly string[]): FloorAgent[] {
  const rank = new Map(identityIds.map((id, index) => [id, index]));
  const buckets = new Map<string, FloorAgent[]>();
  for (const agent of agents) {
    const owner = agent.session.agentId ?? '';
    const bucket = buckets.get(owner) ?? [];
    bucket.push(agent);
    buckets.set(owner, bucket);
  }
  for (const bucket of buckets.values()) bucket.sort((a, b) =>
    (b.lastActivityAtMs ?? 0) - (a.lastActivityAtMs ?? 0) || a.id.localeCompare(b.id));
  const owners = [...buckets.keys()].sort((a, b) =>
    (rank.get(a) ?? Number.MAX_SAFE_INTEGER) - (rank.get(b) ?? Number.MAX_SAFE_INTEGER) || a.localeCompare(b));
  const result: FloorAgent[] = [];
  for (let round = 0; result.length < agents.length; round++) {
    for (const owner of owners) {
      const agent = buckets.get(owner)?.[round];
      if (agent) result.push(agent);
    }
  }
  return result;
}
