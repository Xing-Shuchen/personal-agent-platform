import type { FloorAgent } from '@pap/floor-contract';
import type { SessionRow } from './session.ts';

type Entry = Readonly<{ agent: FloorAgent; row: SessionRow }>;
const key = (value: unknown): string | null => typeof value === 'string' && value.length > 0 ? value : null;
const parentInstanceMatches = (child: Entry, parent: Entry): boolean =>
  !Object.hasOwn(child.row, 'parentSessionId') ||
  (typeof child.row.parentSessionId === 'string' && child.row.parentSessionId.length > 0 &&
    child.row.parentSessionId === parent.agent.session.sessionId);

/** Link only unambiguous visible rows. Relation state never changes direct activity. */
export function linkSessionRelations(entries: readonly Entry[]): FloorAgent[] {
  const byKey = new Map<string, Entry[]>();
  for (const entry of entries) {
    const same = byKey.get(entry.agent.session.key) ?? [];
    same.push(entry); byKey.set(entry.agent.session.key, same);
  }
  const unique = (rawKey: string | null, gatewayId: string): Entry | null => {
    if (!rawKey) return null;
    const matches = (byKey.get(rawKey) ?? []).filter(e => e.agent.session.gatewayId === gatewayId);
    return matches.length === 1 ? matches[0] : null;
  };
  const children = new Map<string, Set<string>>();
  const parents = new Map<string, string>();
  const explicit = new Set<string>();
  for (const parent of entries) {
    if (!Array.isArray(parent.row.childSessions) || !parent.row.childSessions.every(x => typeof x === 'string')) continue;
    explicit.add(parent.agent.id);
    const linked = children.get(parent.agent.id) ?? new Set<string>();
    for (const childKey of parent.row.childSessions) {
      const child = unique(childKey, parent.agent.session.gatewayId);
      if (!child || child.agent.id === parent.agent.id || !parentInstanceMatches(child, parent)) continue;
      const reverse = key(child.row.parentSessionKey);
      if (reverse && reverse !== parent.agent.session.key) continue;
      linked.add(child.agent.id);
    }
    children.set(parent.agent.id, linked);
  }
  const claims = new Map<string, Set<string>>();
  for (const [parentId, childIds] of children) for (const childId of childIds) {
    const owners = claims.get(childId) ?? new Set<string>();
    owners.add(parentId); claims.set(childId, owners);
  }
  for (const [childId, owners] of claims) {
    if (owners.size === 1) parents.set(childId, [...owners][0]);
    else for (const parentId of owners) children.get(parentId)?.delete(childId);
  }
  for (const child of entries) {
    const parent = unique(key(child.row.parentSessionKey), child.agent.session.gatewayId);
    if (!parent || parent.agent.id === child.agent.id || !parentInstanceMatches(child, parent)) continue;
    if (explicit.has(parent.agent.id) && !children.get(parent.agent.id)?.has(child.agent.id)) continue;
    if (claims.get(child.agent.id)?.size && parents.get(child.agent.id) !== parent.agent.id) continue;
    parents.set(child.agent.id, parent.agent.id);
    const linked = children.get(parent.agent.id) ?? new Set<string>();
    linked.add(child.agent.id); children.set(parent.agent.id, linked);
  }
  const byId = new Map(entries.map(e => [e.agent.id, e.agent]));
  return entries.map(({ agent }) => {
    const ids = children.get(agent.id);
    const childIds = ids ? [...ids].sort() : null;
    return { ...agent, relation: {
      parentId: parents.get(agent.id) ?? null,
      childIds,
      runningVisibleChildren: childIds?.filter(id => byId.get(id)?.work.status === 'running').length ?? null
    } };
  });
}
