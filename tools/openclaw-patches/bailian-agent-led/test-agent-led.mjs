import assert from 'node:assert/strict';
import { test } from 'node:test';
import { createAgentLedController } from './agent-led.mjs';

function harness(overrides = {}) {
  const scheduled = new Map(); let next = 0;
  const events = { calls: [], transcript: [], audio: [], errors: [], done: [], sent: [] };
  const timers = { setTimeout(fn) { scheduled.set(++next, fn); return next; }, clearTimeout(id) { scheduled.delete(id); } };
  const controller = createAgentLedController({
    onToolCall: e => events.calls.push(e), onTranscript: (...e) => events.transcript.push(e),
    onAudio: e => events.audio.push(e), onError: e => events.errors.push(e),
    onResponseDone: e => events.done.push(e), onClearAudio() {}, ...overrides,
  }, e => events.sent.push(e), { timers });
  const final = text => controller.event({ type: 'conversation.item.input_audio_transcription.completed', transcript: text });
  const response = text => {
    controller.event({ type: 'response.created' });
    controller.event({ type: 'response.audio.delta', delta: Buffer.from('audio').toString('base64') });
    controller.event({ type: 'response.audio_transcript.done', transcript: text });
    controller.event({ type: 'response.done', response: { status: 'completed' } });
  };
  return { controller, events, scheduled, final, response };
}
test('ordinary replies, next and skips always delegate raw speech to the agent', () => {
  for (const text of ['写今天的日记', '跳过吧，感觉都挺正常的。', '下一个', '昨晚十二点刚过睡，八点起']) {
    const h = harness(); h.final(text); h.controller.flush();
    assert.equal(h.events.calls.length, 1);
    assert.equal(h.events.calls[0].args.question, text);
    assert.equal(h.events.calls[0].name, 'openclaw_agent_consult');
    assert.equal(h.events.audio.length, 0);
  }
});
test('adjacent final ASR fragments merge without paraphrasing', () => {
  const h = harness(); h.final('我觉得主要的是'); h.final('汇报时能把任务讲清楚');
  assert.equal(h.events.calls.length, 0);
  h.controller.flush();
  assert.equal(h.events.calls[0].args.question, '我觉得主要的是\n汇报时能把任务讲清楚');
});
test('direct provider inventions are cancelled and never spoken or persisted', () => {
  const h = harness(); h.response('接下来是心流时刻。');
  assert.equal(h.events.audio.length, 0); assert.equal(h.events.transcript.length, 0);
  assert.ok(h.events.sent.some(e => e.type === 'response.cancel'));
});
test('agent reply must match before any audio or assistant transcript is released', () => {
  const h = harness(); h.final('下一个'); h.controller.flush();
  h.controller.submit(h.events.calls[0].callId, { text: '下一栏是怪现状。' });
  h.controller.event({type:'response.audio.delta',delta:Buffer.from('audio').toString('base64')});
  assert.equal(h.events.audio.length, 0);
  h.controller.event({type:'response.audio_transcript.done',transcript:'下一栏是怪现状！'});
  h.controller.event({type:'response.done',response:{status:'completed'}});
  assert.equal(h.events.audio.length, 1); assert.equal(h.events.done.length, 1);
});
test('rewritten claims including false completion are withheld', () => {
  const h = harness(); h.final('保存'); h.controller.flush();
  h.controller.submit(h.events.calls[0].callId, { text: '本地已保存，尚未同步。' });
  h.response('已保存并同步到手机。');
  assert.equal(h.events.audio.length, 0); assert.equal(h.events.errors.length, 1);
});
test('a later turn carries the exact challenge only on explicit assent', () => {
  const h = harness(); h.final('同步'); h.controller.flush();
  const id = '12345678-1234-1234-1234-123456789abc';
  h.controller.submit(h.events.calls[0].callId, {text:`VOICE_CONFIRMATION_REQUIRED:${id} internal retry instructions`});
  h.final('确认'); h.controller.flush();
  assert.equal(h.events.calls[1].args.confirmationId, id);
  assert.equal(h.events.calls[1].args.question, '确认');
  assert.ok(!h.events.sent.at(-2).item.content[0].text.includes(id), 'challenge id never spoken');
});
for (const text of ['确认？', '如果没问题就确认', '取消', '先解释一下', '他说确认', '确认，换个文件']) test(`ambiguous or changed request gets no confirmation grant: ${text}`, () => {
  const h = harness(); h.final('同步'); h.controller.flush();
  h.controller.submit(h.events.calls[0].callId,{text:'VOICE_CONFIRMATION_REQUIRED:12345678-1234-1234-1234-123456789abc'});
  h.final(text); h.controller.flush(); assert.equal(h.events.calls[1].args.confirmationId, undefined);
});
test('interruptions discard stale tool results and buffered audio', () => {
  const h = harness(); h.final('旧问题'); h.controller.flush(); const old = h.events.calls[0].callId;
  h.controller.event({type:'input_audio_buffer.speech_started'});
  h.controller.submit(old, {text:'迟到的回答'});
  h.response('迟到的回答'); assert.equal(h.events.audio.length,0);
});
test('interim working results never trigger speech', () => {
  const h = harness(); h.final('保存'); h.controller.flush();
  h.controller.submit(h.events.calls[0].callId,{status:'working',text:'checking'},{willContinue:true});
  assert.equal(h.events.sent.length,0);
});
test('close clears pending challenges, timers and late delivery', () => {
  const h = harness(); h.final('测试'); h.controller.flush(); const call = h.events.calls[0].callId;
  h.controller.close(); h.controller.submit(call,{text:'late'}); h.final('确认');
  assert.equal(h.scheduled.size,0); assert.equal(h.events.calls.length,1); assert.equal(h.events.sent.length,0);
});
test('native host delegation owns normal speech without App tool forwarding', async () => {
  const inputs=[];
  const h=harness({runAgentConsult:async input=>{inputs.push(input);return {text:'下一栏是怪现状。'};}});
  h.final('下一个');h.controller.flush();
  await new Promise(resolve=>setImmediate(resolve));
  assert.equal(inputs[0].prompt,'下一个');
  assert.equal(h.events.calls.length,0);
  h.response('下一栏是怪现状。');assert.equal(h.events.audio.length,1);
});
test('native host confirmation challenge is spoken without exposing protocol details', async () => {
  const h=harness({runAgentConsult:async()=>({text:'One pending action has not run. Say "yes" or "确认" to confirm that action, or "no" or "取消" to cancel it.'})});
  h.final('同步');h.controller.flush();await new Promise(resolve=>setImmediate(resolve));
  const prompt=h.events.sent.find(e=>e.type==='conversation.item.create').item.content[0].text;
  assert.match(prompt,/尚未运行/);assert.doesNotMatch(prompt,/One pending/);
});
test('native host execution is aborted on speech interruption and cannot speak late', async () => {
  let resolve,signal;
  const h=harness({runAgentConsult:input=>{signal=input.signal;return new Promise(r=>resolve=r);}});
  h.final('旧问题');h.controller.flush();await new Promise(resolve=>setImmediate(resolve));
  h.controller.event({type:'input_audio_buffer.speech_started'});
  assert.equal(signal.aborted,true);resolve({text:'late'});
  await new Promise(resolve=>setImmediate(resolve));
  assert.ok(!h.events.sent.some(e=>e.type==='response.create'));
});
test('explicit output cancellation reports a terminal event and clears pending fragments', () => {
  const h=harness();h.final('不要再执行');h.controller.cancel();h.controller.flush();
  assert.equal(h.events.calls.length,0);
  assert.deepEqual(h.events.done,[{status:'cancelled'}]);
});
test('validated long audio is paced and interruption clears queued playback', () => {
  const h=harness();h.final('继续');h.controller.flush();
  h.controller.submit(h.events.calls[0].callId,{text:'下一栏。'});
  h.controller.event({type:'response.audio.delta',delta:Buffer.alloc(15000).toString('base64')});
  h.controller.event({type:'response.audio_transcript.done',transcript:'下一栏。'});
  h.controller.event({type:'response.done',response:{status:'completed'}});
  assert.equal(h.events.audio.length,1);assert.equal(h.events.audio[0].length,4800);
  assert.equal(h.events.done.length,0);
  h.controller.cancel();assert.equal(h.scheduled.size,0);
});
test('specific native operation prompts are preserved instead of replaced by generic speech', async () => {
  const text='待确认：查询飞书妙记（起始日期 2026-10-27）。这项操作尚未执行。请说“确认”仅批准这项操作，或说“取消”。';
  const h=harness({runAgentConsult:async()=>({text})});
  h.final('查询今天的妙记');h.controller.flush();await new Promise(resolve=>setImmediate(resolve));
  assert.ok(h.events.sent.find(e=>e.type==='conversation.item.create').item.content[0].text.endsWith(text));
});
test('specific fallback challenge keeps operation details but strips protocol instructions', () => {
  const h=harness();h.final('查询');h.controller.flush();
  h.controller.submit(h.events.calls[0].callId,{text:'VOICE_CONFIRMATION_REQUIRED:12345678-1234-1234-1234-123456789abc 待确认：查询今天的妙记。请说确认。 After spoken confirmation, call openclaw_agent_consult with this confirmationId.'});
  const prompt=h.events.sent.find(e=>e.type==='conversation.item.create').item.content[0].text;
  assert.match(prompt,/查询今天的妙记/);assert.doesNotMatch(prompt,/confirmationId|12345678/);
});
