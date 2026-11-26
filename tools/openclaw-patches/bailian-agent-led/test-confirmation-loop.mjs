import assert from 'node:assert/strict';
import { test, afterEach } from 'node:test';
import { readFileSync } from 'node:fs';
import { createHash, randomUUID } from 'node:crypto';
import { join, resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
import vm from 'node:vm';
assert.ok(process.env.OPENCLAW_DIST, 'Set OPENCLAW_DIST to the installed runtime');
const dist=resolve(process.env.OPENCLAW_DIST);
const load=async name=>import(pathToFileURL(join(dist,name)).href);
function region(name){const s=readFileSync(join(dist,'agent-tools.before-tool-call-iy-Keqfw.mjs'),'utf8');const a=s.indexOf(`//#region ${name}\n`);assert.notEqual(a,-1);return s.slice(a,s.indexOf('//#endregion',a));}
const { t:createDeferredCore }=await load('deferred-D0La5CRk.mjs');
const { t:buildToolMutationState }=await load('tool-mutation-CDE0DtL7.mjs');
const names=['checkClientVoiceToolConfirmationPolicy','consumeClientVoiceToolConfirmationPolicy','captureClientVoiceConfirmationUtterance','prepareClientVoiceConfirmationTranscript','recordClientVoiceConfirmationTranscriptAppend','noteClientVoiceConfirmationUtterance','authorizeObservedClientVoiceConfirmation','bindAuthorizedClientVoiceConfirmation','readClientVoiceConfirmationReadiness','observeClientVoiceConfirmationRun','resetClientVoiceConfirmationStateForTest','isExplicitAffirmation'];
const confirmation=vm.runInNewContext(region('src/talk/client-voice-confirmation-policy.ts')+region('src/talk/client-voice-confirmation.ts')+`\n({${names.join(',')}})`,{createHash,randomUUID,createDeferredCore,buildToolMutationState,setTimeout,clearTimeout,process:{env:{}}});
afterEach(()=>confirmation.resetClientVoiceConfirmationStateForTest());
function action(extra={}){return {agentId:'test-agent',voiceSessionId:'test-call',runId:'request-run',toolCallId:'blocked-call',toolName:'exec',toolParams:{command:'git push origin main',title:'Publish the requested note'},now:Date.now(),...extra};}
function speech(r,text){const entryId=randomUUID();const p={agentId:r.agentId,voiceSessionId:r.voiceSessionId,now:r.now+1,entryId};const captured=confirmation.captureClientVoiceConfirmationUtterance(p);const observed=confirmation.prepareClientVoiceConfirmationTranscript({...p,confirmation:captured});confirmation.recordClientVoiceConfirmationTranscriptAppend({entryId,confirmation:observed,text,appended:true});confirmation.noteClientVoiceConfirmationUtterance({...p,confirmation:observed,timestamp:r.now+1});}
function grant(r){return confirmation.authorizeObservedClientVoiceConfirmation({agentId:r.agentId,voiceSessionId:r.voiceSessionId,now:r.now+2});}
test('pending prompt identifies the operation without exposing shell arguments', () => {
  const request = action({toolParams:{command:'lark-cli minutes +search --as bot --start 2026-10-27 --page-size 15',title:'Search today'}});
  const observer=confirmation.observeClientVoiceConfirmationRun(request);
  confirmation.checkClientVoiceToolConfirmationPolicy(request);
  assert.match(observer.readReply(),/查询飞书妙记/);
  assert.match(observer.readReply(),/2026-10-27/);
  assert.doesNotMatch(observer.readReply(),/--as bot/);
  observer.release();
});
test('alternate tools in the same blocked turn cannot replace the action being confirmed', () => {
  const request=action();const observer=confirmation.observeClientVoiceConfirmationRun(request);
  const first=confirmation.checkClientVoiceToolConfirmationPolicy(request);
  const alternate=confirmation.checkClientVoiceToolConfirmationPolicy({...request,toolName:'sessions_spawn',toolParams:{task:'alternate execution'}});
  assert.equal(first.reason.split(' ')[0],alternate.reason.split(' ')[0]);
  speech(request,'确认批准这项操作');const approval=grant(request);assert.ok(approval);
  confirmation.bindAuthorizedClientVoiceConfirmation({grant:approval,runId:'retry-run',now:request.now+2});
  assert.equal(confirmation.consumeClientVoiceToolConfirmationPolicy({...request,runId:'retry-run',now:request.now+3}).allowed,true);
  assert.equal(confirmation.consumeClientVoiceToolConfirmationPolicy({...request,runId:'retry-run',now:request.now+3}).allowed,false);
  observer.release();
});
test('exact action-reference assent accepts natural Chinese but never changed instructions', () => {
  assert.equal(confirmation.isExplicitAffirmation('确认批准这项操作。'),true);
  assert.equal(confirmation.isExplicitAffirmation('确认批准这项操作？'),false);
  assert.equal(confirmation.isExplicitAffirmation('确认批准这项操作，换个文件'),false);
});
