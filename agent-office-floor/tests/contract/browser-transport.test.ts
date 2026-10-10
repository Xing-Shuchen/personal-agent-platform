import assert from 'node:assert/strict';
import test from 'node:test';
import { emptyFloorState } from '@pap/floor-contract';
import { admitHttpSnapshot, admitStreamUpdate } from '../../apps/web/src/transport.ts';

test('late HTTP snapshots cannot roll back an SSE revision or new epoch', () => {
  const a4 = { ...emptyFloorState('a', 4), revision: 4 };
  const a5 = { ...a4, revision: 5 };
  const b0 = emptyFloorState('b', 6);
  assert.equal(admitHttpSnapshot(a5, a4, 'a'), a5);
  assert.equal(admitHttpSnapshot(a4, a5, 'a'), a5);
  assert.equal(admitHttpSnapshot(b0, a5, 'a'), b0);
  assert.equal(admitHttpSnapshot(a5, b0, 'a'), b0);
  assert.equal(admitHttpSnapshot(null, a4, null), a4);
  assert.equal(admitHttpSnapshot(b0, a4, null), b0);
});

test('an SSE baseline cannot reverse a later patch in the same epoch', () => {
  const a4 = { ...emptyFloorState('a', 4), revision: 4 };
  const a5 = { ...a4, revision: 5 };
  assert.equal(admitStreamUpdate(a5, { type: 'snapshot', state: a4 }), a5);
  assert.equal(admitStreamUpdate(a4, { type: 'snapshot', state: a5 }), a5);
  const b0 = emptyFloorState('b', 6);
  assert.equal(admitStreamUpdate(a5, { type: 'snapshot', state: b0 }), b0);
});
