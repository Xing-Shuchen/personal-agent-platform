import assert from 'node:assert/strict';
import test from 'node:test';
import { projectSelectedIdentities, selectedIdentityBindings, selectedIdentityRoster } from '../../apps/server/src/identity-bindings.ts';

test('identity projection keeps only selected names and stable appearance keys', () => {
  const raw = [{ id: 'a', identityName: '甲专员', identityEmoji: '✦', workspace: '/private/a', model: 'secret-route' },
    { id: 'b', identityName: '乙专员', workspace: '/private/b' }];
  assert.deepEqual(projectSelectedIdentities(raw, ['a']), { a: { name: '甲专员', avatarKey: 'a' } });
  assert.deepEqual(selectedIdentityBindings(['a'], { a: { name: '我的别名' }, b: { name: 'leak' } },
    () => JSON.stringify(raw)), { a: { name: '我的别名', avatarKey: 'a' } });
});

test('all selected identities are visible with Feishu apps first, including agents without sessions', () => {
  const bindings = { a: { name: '甲专员' }, b: { name: '乙专员' }, c: { name: '丙专员' } };
  assert.deepEqual(selectedIdentityRoster(['a','b','c','a'], bindings, ['c','a','unselected']), [
    { id: 'c', name: '丙专员', hasFeishuApp: true },
    { id: 'a', name: '甲专员', hasFeishuApp: true },
    { id: 'b', name: '乙专员', hasFeishuApp: false }
  ]);
});

test('no selected IDs cause no OpenClaw identity read', () => {
  let reads = 0;
  assert.deepEqual(selectedIdentityBindings([], {}, () => { reads++; return '[]'; }), {});
  assert.equal(reads, 0);
});

test('malformed manual bindings cannot inject non-string browser values', () => {
  const result = selectedIdentityBindings(['a'], { a: { name: { private: 'text' }, avatarKey: '\n' } },
    () => JSON.stringify([{ id: 'a', identityName: '甲专员' }]));
  assert.deepEqual(result, { a: { name: '甲专员', avatarKey: 'a' } });
  assert.deepEqual(selectedIdentityBindings(['__proto__'], {}, () =>
    JSON.stringify([{ id: '__proto__', identityName: 'unsafe' }])), {});
});
