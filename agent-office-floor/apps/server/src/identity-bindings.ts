import { execFileSync } from 'node:child_process';
import type { DisplayBinding } from '@pap/openclaw-adapter';

function text(value: unknown, max: number): string | null {
  return typeof value === 'string' && value.length > 0 && value.length <= max &&
    !/[\u0000-\u001f\u007f]/u.test(value) ? value : null;
}
function agentId(value: unknown): string | null {
  const id = text(value, 128);
  return id && /^[a-zA-Z0-9][a-zA-Z0-9_-]*$/.test(id) &&
    !['constructor', 'prototype', '__proto__'].includes(id) ? id : null;
}

/** Project identities for selected IDs only; CLI workspace paths and routes are discarded. */
export function projectSelectedIdentities(raw: unknown, selectedAgentIds: readonly string[]): Record<string, DisplayBinding> {
  const selected = new Set(selectedAgentIds);
  const rows = Array.isArray(raw) ? raw : raw && typeof raw === 'object' &&
    Array.isArray((raw as Record<string, unknown>).agents) ? (raw as { agents: unknown[] }).agents : [];
  const result: Record<string, DisplayBinding> = {};
  for (const row of rows) {
    if (!row || typeof row !== 'object' || Array.isArray(row)) continue;
    const value = row as Record<string, unknown>;
    const id = agentId(value.id ?? value.agentId);
    if (!id || !selected.has(id)) continue;
    const name = text(value.identityName, 48) ?? text(value.name, 48);
    result[id] = { ...(name ? { name } : {}), avatarKey: id };
  }
  return result;
}

export function selectedIdentityBindings(selectedAgentIds: readonly string[], manual: unknown,
  readList: () => string = () => execFileSync('openclaw', ['agents', 'list', '--json'],
    { encoding: 'utf8', timeout: 5000, maxBuffer: 1024 * 1024 })): Record<string, DisplayBinding> {
  if (!selectedAgentIds.length) return {};
  let discovered: Record<string, DisplayBinding> = {};
  try { discovered = projectSelectedIdentities(JSON.parse(readList()), selectedAgentIds); }
  catch { process.stderr.write('OpenClaw identities unavailable; using session labels\n'); }
  const input = manual && typeof manual === 'object' && !Array.isArray(manual)
    ? manual as Record<string, unknown> : {};
  const result: Record<string, DisplayBinding> = {};
  for (const id of selectedAgentIds) {
    if (!agentId(id)) continue;
    const item = input[id];
    const binding = item && typeof item === 'object' && !Array.isArray(item)
      ? item as Record<string, unknown> : {};
    const name = text(binding.name, 48) ?? discovered[id]?.name;
    const avatarKey = text(binding.avatarKey, 128) ?? discovered[id]?.avatarKey;
    result[id] = { ...(name ? { name } : {}), ...(avatarKey ? { avatarKey } : {}) };
  }
  return result;
}

export type OfficeIdentity = Readonly<{ id: string; name: string; hasFeishuApp: boolean }>;

/** Public display data only. App routes, account IDs, paths and credentials stay local. */
export function selectedIdentityRoster(selectedAgentIds: readonly string[], bindings: Readonly<Record<string, DisplayBinding>>,
  feishuAgentIds: unknown): OfficeIdentity[] {
  const feishu = new Set(Array.isArray(feishuAgentIds) ? feishuAgentIds.filter(x => typeof x === 'string') : []);
  return [...new Set(selectedAgentIds)].filter(id => agentId(id)).map(id => ({
    id, name: bindings[id]?.name ?? id, hasFeishuApp: feishu.has(id)
  })).sort((a, b) => Number(b.hasFeishuApp) - Number(a.hasFeishuApp) ||
    a.name.localeCompare(b.name, 'zh-CN') || a.id.localeCompare(b.id));
}
