import assert from 'node:assert/strict';
import test from 'node:test';
import { emptyFloorState, type FloorHandoff } from '@pap/floor-contract';
import { normalizeSessionRow } from '@pap/openclaw-adapter';
import { HandoffLedger } from '../../packages/office-scene/src/stateMapping/handoffs.ts';

test('handoff effects need a new scoped event and never replay a baseline or duplicate', () => {
  const from = normalizeSessionRow({ key: 'from', agentId: 'a', sessionId: 's1' }, 'g', 100);
  const to = normalizeSessionRow({ key: 'to', agentId: 'b', sessionId: 's2' }, 'g', 100);
  const prior: FloorHandoff = { id: 'prior', fromId: from.id, toId: to.id, kind: 'request',
    observedAtMs: 100, expiresAtMs: 3100, evidenceReference: 'verified:prior' };
  const next: FloorHandoff = { ...prior, id: 'next', observedAtMs: 1000,
    expiresAtMs: 4000, evidenceReference: 'verified:next' };
  const base = { ...emptyFloorState('e', 1000), agents: { [from.id]: from, [to.id]: to },
    connection: { mode: 'subscription' as const, state: 'live' as const,
      lastConfirmedAtMs: 1000, reason: null },
    capabilities: { ...emptyFloorState('e').capabilities, handoff: 'partial' as const },
    handoffs: [prior] };
  const visible = new Set([from.id, to.id]);
  const ledger = new HandoffLedger();
  assert.deepEqual(ledger.take(base, visible, 1000), []);
  const updated = { ...base, handoffs: [prior, next] };
  assert.deepEqual(ledger.take(updated, visible, 1500), [next]);
  assert.deepEqual(ledger.take(updated, visible, 1600), []);
  const hidden: FloorHandoff = { ...next, id: 'hidden', evidenceReference: 'verified:hidden' };
  assert.deepEqual(ledger.take({ ...base, handoffs: [hidden] }, new Set([from.id]), 1700), []);
  assert.deepEqual(ledger.take({ ...base, handoffs: [hidden] }, visible, 1800), []);
  const revoked: FloorHandoff = { ...next, id: 'revoked', evidenceReference: 'verified:revoked' };
  assert.deepEqual(ledger.take({ ...base, connection: { ...base.connection, state: 'auth_required' as const },
    handoffs: [revoked] }, visible, 1800), []);
  assert.deepEqual(ledger.take({ ...base, handoffs: [revoked] }, visible, 1900), []);
  assert.deepEqual(ledger.take({ ...base, epoch: 'new', handoffs: [next] }, visible, 1900), []);
});
