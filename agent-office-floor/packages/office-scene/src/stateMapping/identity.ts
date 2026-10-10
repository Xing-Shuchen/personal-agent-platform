import type { FloorAgent } from '@pap/floor-contract';
/** Stable, opaque cues for a displayed set. Floor IDs are hashes, never raw session keys. */
export function opaqueSessionCues(agents: readonly FloorAgent[]): Map<string, string> {
  const ids = agents.map(agent => agent.id);
  let length = 6;
  while (length < 30 && new Set(ids.map(id => id.slice(-length))).size !== ids.length) length++;
  return new Map(ids.map(id => [id, id.slice(-length)]));
}
function nameplateBase(name: string, limit: number): string {
  const characters = Array.from(name);
  return characters.length <= limit ? name : `${characters.slice(0, limit - 1).join('')}…`;
}
/** Add a short stable session cue only when one owner occupies multiple seats. */
export function sceneName(agent: FloorAgent, visible: readonly FloorAgent[]): string {
  if (!agent.session.agentId) return nameplateBase(agent.name, 32);
  const siblings = visible.filter(a => a.session.agentId === agent.session.agentId);
  if (siblings.length < 2) return nameplateBase(agent.name, 32);
  const cue = opaqueSessionCues(siblings).get(agent.id);
  if (cue && cue.length <= 8) return `${nameplateBase(agent.name, 23)}·${cue}`;
  // Preserve a visible identity and a unique cue when opaque suffixes collide.
  const ordinal = ([...siblings].sort((a, b) => a.id.localeCompare(b.id)).findIndex(a => a.id === agent.id) + 1).toString(36).toUpperCase();
  return `${nameplateBase(agent.name, 23)}·${ordinal}`;
}
