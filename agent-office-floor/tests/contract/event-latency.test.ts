import assert from 'node:assert/strict';
import test from 'node:test';
import { FloorStore, normalizeSessionRow } from '@pap/openclaw-adapter';
import type { FloorAgent, FloorUpdate } from '@pap/floor-contract';
import { visibleEventReceiptAt } from '../../apps/web/src/event-latency.ts';

test('scene-page event timing uses only new structured evidence that changes a visible label', () => {
  const store = new FloorStore('g');
  const agent = normalizeSessionRow({ key: 'k', agentId: 'a', sessionId: 's',
    status: 'running', hasActiveRun: true, activeRunIds: ['r'] }, 'g', 100);
  store.replaceAgents([agent], true);
  const before = store.snapshot();
  const event = { source: 'tool_event' as const, reference: 'r:1', sourceAtMs: null, observedAtMs: 850 };
  const withTool: FloorAgent = { ...agent, work: { ...agent.work,
    tool: { name: 'read_file', callId: 'c', phase: 'start' }, evidence: [...agent.work.evidence, event] } };
  const patch: FloorUpdate = { type: 'patch', schemaVersion: 1, epoch: before.epoch,
    baseRevision: before.revision, revision: before.revision + 1, generatedAtMs: 900,
    upserts: [withTool], removeIds: [] };
  assert.equal(visibleEventReceiptAt(before, patch, new Set([agent.id])), 850);
  assert.equal(visibleEventReceiptAt(before, patch, new Set()), null);
  assert.equal(visibleEventReceiptAt(before, patch, new Set(['another'])), null);
  assert.equal(visibleEventReceiptAt(before, { ...patch, upserts: [{ ...withTool,
    work: { ...withTool.work, tool: null } }] }, new Set([agent.id])), null);
  assert.equal(visibleEventReceiptAt(before, { ...patch, upserts: [{ ...withTool,
    work: { ...withTool.work, evidence: agent.work.evidence } }] }, new Set([agent.id])), null);
  const other = { ...agent, id: 'other', session: { ...agent.session, key: 'other', sessionId: 'other' } };
  const otherTool = { ...withTool, id: other.id, session: other.session,
    work: { ...withTool.work, evidence: [{ ...event, observedAtMs: 840 }] } };
  const two = { ...before, agents: { ...before.agents, [other.id]: other } };
  assert.equal(visibleEventReceiptAt(two, { ...patch, upserts: [withTool, otherTool] },
    new Set([agent.id, other.id])), 840);
});
