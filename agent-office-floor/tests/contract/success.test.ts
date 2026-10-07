import assert from 'node:assert/strict';
import test from 'node:test';
import { normalizeSessionRow } from '@pap/openclaw-adapter';
import { SuccessLedger } from '../../packages/office-scene/src/stateMapping/success.ts';
const row = (sessionId: string, status: string, runId?: string) => normalizeSessionRow({ key: 'k', agentId: 'a', sessionId, status, activeRunIds: [], hasActiveRun: false, ...(runId ? { lastRunId: runId } : {}) }, 'g', Date.now());
test('success effect fires once for a new verified terminal run, never on first snapshot or instance replacement', () => {
  const ledger = new SuccessLedger();
  assert.equal(ledger.observe(row('s1','done','r1')), false);
  assert.equal(ledger.observe(row('s1','done','r1')), false);
  assert.equal(ledger.observe(row('s1','done','r2')), true);
  assert.equal(ledger.observe(row('s1','done','r2')), false);
  assert.equal(ledger.observe(row('s2','done','r3')), false);
  assert.equal(ledger.observe(row('s2','done','r4')), true);
});
test('terminal outcome waits for direct activity to clear before one celebration', () => {
  const ledger = new SuccessLedger();
  ledger.observe(row('s1','done','r1'));
  const complete = row('s1','done','r2');
  const pending = { ...complete, work: { ...complete.work, status: 'running' as const,
    activeRunIds: ['r3'], hasActiveRun: true } };
  assert.equal(ledger.observe(pending), false);
  assert.equal(ledger.observe(row('s1','done','r2')), true);
  assert.equal(ledger.observe(row('s1','done','r2')), false);
});
