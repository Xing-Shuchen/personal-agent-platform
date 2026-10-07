import assert from 'node:assert/strict';
import test from 'node:test';
import { normalizeSessionRow } from '../../packages/openclaw-adapter/src/normalization/session.ts';
import { linkSessionRelations } from '../../packages/openclaw-adapter/src/normalization/relations.ts';

const make = (row: Record<string, unknown> & { key: string }) => ({ row, agent: normalizeSessionRow(row, 'g', 100) });

test('visible child activity is separate from parent direct runs', () => {
  const parent = make({ key: 'parent', agentId: 'a', sessionId: 'p1', activeRunIds: [], hasActiveRun: false,
    childSessions: ['child'] });
  const child = make({ key: 'child', agentId: 'b', sessionId: 'c1', parentSessionKey: 'parent',
    activeRunIds: ['r'], hasActiveRun: true });
  const [p, c] = linkSessionRelations([parent, child]);
  assert.equal(p.work.status, 'idle');
  assert.deepEqual(p.relation.childIds, [c.id]);
  assert.equal(p.relation.runningVisibleChildren, 1);
  assert.equal(c.relation.parentId, p.id);
});

test('ambiguous raw keys and contradictory relation rows are not linked', () => {
  const p1 = make({ key: 'global', agentId: 'a', childSessions: ['child'] });
  const p2 = make({ key: 'global', agentId: 'b', childSessions: ['child'] });
  const child = make({ key: 'child', agentId: 'c', parentSessionKey: 'global' });
  const linked = linkSessionRelations([p1, p2, child]);
  assert.equal(linked[2].relation.parentId, null);
  assert.deepEqual(linked[0].relation.childIds, []);
  assert.deepEqual(linked[1].relation.childIds, []);
  const wrong = make({ key: 'other', agentId: 'd', parentSessionKey: 'global' });
  const unique = linkSessionRelations([p1, wrong]);
  assert.equal(unique[1].relation.parentId, null);
});

test('a child tied to an old parent instance is not attached after key reuse', () => {
  const parent = make({ key: 'parent', agentId: 'a', sessionId: 'new-instance',
    childSessions: ['child'] });
  const oldChild = make({ key: 'child', agentId: 'b', sessionId: 'child-instance',
    parentSessionKey: 'parent', parentSessionId: 'old-instance' });
  const [p, c] = linkSessionRelations([parent, oldChild]);
  assert.deepEqual(p.relation.childIds, []);
  assert.equal(c.relation.parentId, null);
  const currentChild = make({ ...oldChild.row, parentSessionId: 'new-instance' });
  const [currentParent, linked] = linkSessionRelations([parent, currentChild]);
  assert.deepEqual(currentParent.relation.childIds, [linked.id]);
  assert.equal(linked.relation.parentId, currentParent.id);
});
