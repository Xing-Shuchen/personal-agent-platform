import assert from 'node:assert/strict';
import { afterEach, test } from 'node:test';
import { readFileSync } from 'node:fs';
import { createHash, randomUUID } from 'node:crypto';
import { join, resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
import vm from 'node:vm';

assert.ok(process.env.OPENCLAW_DIST, 'Set OPENCLAW_DIST to the installed OpenClaw dist directory');
const dist = resolve(process.env.OPENCLAW_DIST);
const candidate = resolve(process.env.VOICE_PATCH_CANDIDATE ?? dist);
const load = async (name) => import(pathToFileURL(join(dist, name)).href);
function region(dir, file, name) {
  const text = readFileSync(join(dir, file), 'utf8');
  const start = text.indexOf(`//#region ${name}\n`);
  assert.notEqual(start, -1, name);
  const end = text.indexOf('//#endregion', start);
  assert.notEqual(end, -1, name);
  return text.slice(start, end);
}
const { t: createDeferredCore } = await load('deferred-D0La5CRk.mjs');
const { t: buildToolMutationState } = await load('tool-mutation-CDE0DtL7.mjs');
const confirmationFile = 'agent-tools.before-tool-call-iy-Keqfw.mjs';
const confirmationNames = [
  'checkClientVoiceToolConfirmationPolicy', 'consumeClientVoiceToolConfirmationPolicy',
  'captureClientVoiceConfirmationUtterance', 'prepareClientVoiceConfirmationTranscript',
  'recordClientVoiceConfirmationTranscriptAppend', 'noteClientVoiceConfirmationUtterance',
  'authorizeObservedClientVoiceConfirmation', 'bindAuthorizedClientVoiceConfirmation',
  'readClientVoiceConfirmationReadiness', 'observeClientVoiceConfirmationRun',
  'resetClientVoiceConfirmationStateForTest', 'isExplicitAffirmation',
];
const confirmation = vm.runInNewContext(
  region(candidate, confirmationFile, 'src/talk/client-voice-confirmation-policy.ts') +
  region(candidate, confirmationFile, 'src/talk/client-voice-confirmation.ts') +
  `\n({${confirmationNames.join(',')}})`,
  { createHash, randomUUID, createDeferredCore, buildToolMutationState, setTimeout, clearTimeout, process: { env: {} } },
);
afterEach(() => confirmation.resetClientVoiceConfirmationStateForTest());
function action(overrides = {}) {
  return { agentId: 'test-agent', voiceSessionId: 'test-call', runId: 'request-run', toolCallId: 'blocked-call',
    toolName: 'exec', toolParams: { command: 'git push origin main', title: 'Publish the requested note' }, now: Date.now(), ...overrides };
}
function speech(request, text, { persisted = true, timestamp = request.now + 1, scope = {}, context } = {}) {
  const entryId = randomUUID();
  const params = { agentId: request.agentId, voiceSessionId: request.voiceSessionId, ...scope, now: timestamp, entryId };
  const captured = context ?? confirmation.captureClientVoiceConfirmationUtterance(params);
  const observed = confirmation.prepareClientVoiceConfirmationTranscript({ ...params, confirmation: captured });
  confirmation.recordClientVoiceConfirmationTranscriptAppend({ entryId, confirmation: observed, text, appended: persisted });
  confirmation.noteClientVoiceConfirmationUtterance({ ...params, confirmation: observed, timestamp });
}
function grant(request, scope = {}) {
  return confirmation.authorizeObservedClientVoiceConfirmation({ agentId: request.agentId, voiceSessionId: request.voiceSessionId, now: request.now + 2, ...scope });
}
for (const text of ['是', '是。', '是的', '确认', '确认！', '確認', '保存', '好的，可以', '是，保存，确认，所有都确认，不用再问了，都确认', 'yes', 'yes, do it!', 'ＹＥＳ！', 'go ahead']) {
  test(`persisted assent authorizes exactly one unchanged action: ${text}`, () => {
    const request = action();
    assert.equal(confirmation.checkClientVoiceToolConfirmationPolicy(request).allowed, false);
    speech(request, text);
    const approval = grant(request);
    assert.ok(approval);
    assert.match(approval.retryContext, /unchanged arguments/);
    assert.equal(confirmation.bindAuthorizedClientVoiceConfirmation({ grant: approval, runId: 'retry-run', now: request.now + 2 }), true);
    const retry = { ...request, runId: 'retry-run', now: request.now + 3 };
    assert.equal(confirmation.checkClientVoiceToolConfirmationPolicy(retry).allowed, true);
    assert.equal(confirmation.consumeClientVoiceToolConfirmationPolicy(retry).allowed, true);
    assert.equal(confirmation.consumeClientVoiceToolConfirmationPolicy(retry).allowed, false);
  });
}
for (const text of ['不', '否', '取消', '不要保存', '先别执行', '不确认', '是，不要执行', 'yes, no', 'yes?', '确认？', '确认吗', '确认后会怎样', '如果没问题就确认', '他说确认', '“确认”', '不用再问了', '好像是', '是，换个文件', '确认，删除别的文件', 'permissions is full access', '嗯']) {
  test(`non-assent never authorizes: ${text}`, () => {
    const request = action();
    confirmation.checkClientVoiceToolConfirmationPolicy(request);
    speech(request, text);
    assert.equal(grant(request), undefined);
  });
}
for (const text of ['取消', '不用保存', '否，谢谢', '不行', '不用了']) test(`Chinese cancellation clears the pending action: ${text}`, () => {
  const request = action();
  confirmation.checkClientVoiceToolConfirmationPolicy(request);
  speech(request, text);
  assert.equal(confirmation.readClientVoiceConfirmationReadiness(request.agentId, request.voiceSessionId), undefined);
  speech(request, '确认', { timestamp: request.now + 3 });
  assert.equal(grant(request), undefined);
});
test('unsaved transcription cannot authorize', () => {
  const request = action();
  confirmation.checkClientVoiceToolConfirmationPolicy(request);
  speech(request, '确认', { persisted: false });
  assert.equal(grant(request), undefined);
});
test('utterance captured before the challenge cannot authorize it', () => {
  const request = action();
  const context = confirmation.captureClientVoiceConfirmationUtterance({ ...request, now: request.now - 1 });
  confirmation.checkClientVoiceToolConfirmationPolicy(request);
  speech(request, '确认', { context });
  assert.equal(grant(request), undefined);
});
test('another call or agent cannot supply consent', () => {
  const request = action();
  confirmation.checkClientVoiceToolConfirmationPolicy(request);
  speech(request, '确认', { scope: { voiceSessionId: 'other-call' } });
  assert.equal(grant(request), undefined);
  speech(request, '确认', { scope: { agentId: 'other-agent' } });
  assert.equal(grant(request), undefined);
});
test('changed arguments and a different run do not inherit consent', () => {
  const request = action();
  confirmation.checkClientVoiceToolConfirmationPolicy(request);
  speech(request, '都确认');
  confirmation.bindAuthorizedClientVoiceConfirmation({ grant: grant(request), runId: 'retry-run', now: request.now + 2 });
  assert.equal(confirmation.checkClientVoiceToolConfirmationPolicy({ ...request, runId: 'other-run' }).allowed, false);
  assert.equal(confirmation.checkClientVoiceToolConfirmationPolicy({ ...request, runId: 'retry-run', toolParams: { command: 'git push another-target main' } }).allowed, false);
});
test('superseding action invalidates earlier speech', () => {
  const request = action();
  confirmation.checkClientVoiceToolConfirmationPolicy(request);
  speech(request, '确认');
  confirmation.checkClientVoiceToolConfirmationPolicy({ ...request, toolParams: { command: 'git push another-target main' }, now: request.now + 2 });
  assert.equal(grant(request), undefined);
});
test('expired action cannot be confirmed', () => {
  const request = action({ now: Date.now() - 130_000 });
  confirmation.checkClientVoiceToolConfirmationPolicy(request);
  speech(request, '确认', { timestamp: Date.now() });
  assert.equal(grant(request, { now: Date.now() }), undefined);
});
test('local writes retain their existing behavior', () => {
  assert.equal(confirmation.checkClientVoiceToolConfirmationPolicy(action({ toolName: 'write', toolParams: { path: 'note.md', content: 'synthetic fixture' } })).allowed, true);
});
test('confirmation prompt advertises supported Chinese words', () => {
  const request = action();
  const observer = confirmation.observeClientVoiceConfirmationRun(request);
  const result = confirmation.checkClientVoiceToolConfirmationPolicy(request);
  assert.match(result.reason, /Chinese 是\/确认/);
  assert.match(observer.readReply(), /确认/);
  assert.match(observer.readReply(), /取消/);
  observer.release();
});

const { r: isOpenAIGptLiveApiModel } = await load('realtime-quicksilver-HjMjNxOa.mjs');
const instructions = vm.runInNewContext(region(candidate, 'realtime-quicksilver-instructions-DcZHzxQd.mjs', 'extensions/openai/realtime-quicksilver-instructions.ts') + '\n({buildOpenAIQuicksilverDelegationPrompt, buildOpenAIQuicksilverInstructions})', { isOpenAIGptLiveApiModel });
const { t: OpenAILiveDelegationQueue } = await load('realtime-live-delegation-queue-uq4IZI5i.mjs');
const { t: parseOpenAIQuicksilverEvent } = await load('realtime-quicksilver-events-BOWZiUvn.mjs');
const { n: buildOpenAIQuicksilverContextAppend } = await load('realtime-quicksilver-protocol-ySN9ISA2.mjs');
const { o: projectOpenAIQuicksilverErrorMessage } = await load('realtime-quicksilver-redaction-Cfc2vSbu.mjs');
const { c: chunkOpenAIQuicksilverAppendText, r: boundOpenAIQuicksilverDelegationResult } = await load('realtime-quicksilver-wire-BMSCbCWC.mjs');
const { t: OpenAIQuicksilverTranscript } = await load('realtime-quicksilver-transcript-v08XZjPO.mjs');
const { c: readErrorName, i: extractErrorCode, u: toErrorObject } = await load('error-coercion-CvJK4lmH.mjs');
const { r: truncateUtf16Safe } = await load('utf16-slice-D_ngcYKd.mjs');
const { o: buildRealtimeVoiceAgentControlSpeechMessage } = await load('agent-run-control-shared-HQwazRP4.mjs');
const Controller = vm.runInNewContext(region(candidate, 'realtime-quicksilver-delegation-controller-DIDxDLgz.mjs', 'extensions/openai/realtime-quicksilver-delegation-controller.ts') + '\nOpenAIQuicksilverDelegationController', {
  AbortController, readErrorName, extractErrorCode, toErrorObject, truncateUtf16Safe,
  isOpenAIGptLiveApiModel, OpenAILiveDelegationQueue, ...instructions, parseOpenAIQuicksilverEvent,
  buildOpenAIQuicksilverContextAppend, projectOpenAIQuicksilverErrorMessage,
  chunkOpenAIQuicksilverAppendText, boundOpenAIQuicksilverDelegationResult,
  OpenAIQuicksilverTranscript, buildRealtimeVoiceAgentControlSpeechMessage,
});
const settle = () => new Promise((done) => setImmediate(done));
function harness(model, runner, handleDelegationInput = () => 'delegate') {
  const sent = [];
  const errors = [];
  const socket = { readyState: 1, send: (text) => sent.push(JSON.parse(text)) };
  const signal = new AbortController().signal;
  const controller = new Controller({ model, signal, getSocket: () => socket, logger: { warn: (e) => errors.push(e) }, onFatalError: (e) => errors.push(e), runAgentConsult: runner, handleDelegationInput }, String);
  return { controller, sent, errors };
}
for (const model of ['gpt-live-1-codex', 'gpt-live-1']) {
  test(`${model}: consult sends no speech until its actual result`, async () => {
    let finish;
    let calls = 0;
    const h = harness(model, () => { calls++; return new Promise((resolve) => { finish = resolve; }); });
    h.controller.startDelegation('request-1', '保存测试笔记');
    assert.equal(calls, 1);
    assert.equal(h.sent.length, 0, 'admission must not inject filler or internal directions');
    finish({ text: '测试笔记已保存。' });
    await settle();
    assert.equal(h.sent.length, 1);
    const packet = h.sent[0];
    assert.equal(model === 'gpt-live-1' ? packet.content : packet.content[0].text, '测试笔记已保存。');
    assert.equal(model === 'gpt-live-1' ? packet.delegation_id : packet.delegation_item_id, 'request-1');
    assert.equal(h.errors.length, 0);
    h.controller.stop();
  });
}
test('explicit status/control requests still receive their response', () => {
  const h = harness('gpt-live-1-codex', () => assert.fail('must not start a consult'), (_text, reply) => { reply('任务仍在执行。'); return 'control'; });
  h.controller.startDelegation('status-1', '进度如何');
  assert.equal(h.sent.length, 1);
  assert.equal(h.sent[0].content[0].text, '任务仍在执行。');
  h.controller.stop();
});
test('an aborted consult cannot emit a late completion', async () => {
  let finish;
  const h = harness('gpt-live-1-codex', () => new Promise((resolve) => { finish = resolve; }));
  h.controller.startDelegation('request-1', '测试');
  h.controller.stop(new Error('test abort'));
  finish({ text: 'late result' });
  await settle();
  assert.equal(h.sent.length, 0);
});
test('provider instructions separate internal directions and completed actions', () => {
  const text = instructions.buildOpenAIQuicksilverInstructions('gpt-live-1-codex', '使用中文。');
  assert.match(text, /wait silently/);
  assert.match(text, /Internal directions are not spoken content/);
  assert.match(text, /pending publish or sync/);
});
