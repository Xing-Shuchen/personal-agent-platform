import assert from 'node:assert/strict';
import test from 'node:test';
import { preferCandidateRow } from '../../packages/openclaw-adapter/src/normalization/snapshot-order.ts';

test('sample time orders overlapping pages; request order resolves equal or absent times', () => {
  const current = { key: 'k', snapshotAt: 200 };
  assert.equal(preferCandidateRow(current, { key: 'k', snapshotAt: 199 }), false);
  assert.equal(preferCandidateRow(current, { key: 'k', snapshotAt: 200 }), true);
  assert.equal(preferCandidateRow(current, { key: 'k', snapshotAt: 201 }), true);
  assert.equal(preferCandidateRow(current, { key: 'k' }), true);
  assert.equal(preferCandidateRow({ key: 'k' }, { key: 'k', snapshotAt: 100 }), true);
});
