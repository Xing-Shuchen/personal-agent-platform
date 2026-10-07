import assert from 'node:assert/strict';
import test from 'node:test';
import { normalizeSessionRow } from '@pap/openclaw-adapter';
import { opaqueSessionCues, sceneName } from '../../packages/office-scene/src/stateMapping/identity.ts';

test('same-owner session name cues stay distinct when raw key tails collide', () => {
  const a = normalizeSessionRow({ key: 'agent:a:first-same', agentId: 'a', sessionId: 's1' }, 'g', 100, { name: '同一专员' });
  const b = normalizeSessionRow({ key: 'agent:a:other-same', agentId: 'a', sessionId: 's2' }, 'g', 100, { name: '同一专员' });
  const visible = [a, b];
  assert.notEqual(sceneName(a, visible), sceneName(b, visible));
  assert.equal(sceneName(a, visible), sceneName(a, [...visible].reverse()));
  assert.ok(sceneName(a, visible).startsWith('同一专员·'));
});

test('a displayed ID-tail collision still produces unique short labels', () => {
  const base = normalizeSessionRow({ key: 'agent:a:first-same', agentId: 'a', sessionId: 's1' }, 'g', 100, { name: '同一专员' });
  const a = { ...base, id: 'session_aaaacafe' };
  const b = { ...base, id: 'session_bbbbcafe', session: { ...base.session, key: 'agent:a:other-same' } };
  const c = { ...base, id: 'session_cccc1234', session: { ...base.session, key: 'agent:a:third-1' } };
  const visible = [a, b, c];
  const names = visible.map(agent => sceneName(agent, visible));
  assert.equal(new Set(names).size, visible.length);
  assert.ok(names.every(name => Array.from(name).length <= 32));
});

test('a single seat keeps the full specialist identity when it fits two lines', () => {
  const agent = normalizeSessionRow({ key: 'agent:historian:main', agentId: 'historian', sessionId: 's1' },
    'g', 100, { name: 'personal-historian' });
  assert.equal(sceneName(agent, [agent]), 'personal-historian');
  const long = { ...agent, name: '专员'.repeat(30) };
  assert.equal(Array.from(sceneName(long, [long])).length, 32);
  assert.ok(sceneName(long, [long]).endsWith('…'));
});

test('visible session cues do not disclose raw direct-recipient key tails', () => {
  const key = 'agent:a:feishu:direct:ou_private_recipient_987654';
  const first = normalizeSessionRow({ key, agentId: 'a', sessionId: 's1' }, 'g', 100, { name: '专员' });
  const second = normalizeSessionRow({ key: 'agent:a:main', agentId: 'a', sessionId: 's2' }, 'g', 100, { name: '专员' });
  const cue = opaqueSessionCues([first, second]).get(first.id);
  assert.ok(cue);
  assert.equal(cue, opaqueSessionCues([second, first]).get(first.id));
  assert.ok(!cue.includes('987654'));
  assert.ok(!sceneName(first, [first, second]).includes('987654'));
  assert.equal(first.session.key, key, 'the adapter retains the raw key for exact identity');
  const fallback = normalizeSessionRow({ key, agentId: 'a', sessionId: 's1' }, 'g', 100);
  assert.ok(!fallback.name.includes('987654'));
});
