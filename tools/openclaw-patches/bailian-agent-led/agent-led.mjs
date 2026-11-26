import { randomUUID } from 'node:crypto';

export const speechKey = text => String(text).normalize('NFKC').replace(/[^\p{L}\p{N}]/gu, '').toLowerCase();
const resultText = result => typeof result === 'string' ? result : ['text', 'result', 'output', 'error', 'message', 'answer'].map(k => result?.[k]).find(v => typeof v === 'string') ?? '';

// Each bridge owns its own pending challenge and playback generation. The host
// still validates persisted assent, expiry, exact arguments and one-shot use.
export function createAgentLedController(req, send, { settleMs = 650, timers = globalThis } = {}) {
  let closed = false, timer, question = '', speaking = false, epoch = 0;
  let pendingConfirmation, activeCall, expected = '', transcript = '', chunks = [], bytes = 0;
  let playbackTimer, audioTimer;
  let api, activeAbort;
  const calls = new Map();
  const clearPlayback = () => {
    timers.clearTimeout(playbackTimer);
    timers.clearTimeout(audioTimer);
    speaking = false; expected = ''; transcript = ''; chunks = []; bytes = 0;
  };
  function flush() {
    timers.clearTimeout(timer); timer = undefined;
    if (closed || !question.trim()) return;
    const raw = question.trim(); question = '';
    const callId = `agent-led-${randomUUID()}`;
    activeCall = callId;
    calls.clear(); calls.set(callId, epoch);
    const args = { question: raw, context: '用户原始语音转写；请由当前 agent 主持完整流程，按其 AGENTS.md 和相关 SKILL 执行。开始技能任务时先读取技能，承接当前阶段，一轮一个问题；用户说继续或下一个时自行推进。遵守用户要求的跳过；维护阶段、已确认事实和待确认项，不重新询问已有答案。不要把转写噪声、截断句或推测写成确定事实。不确定处标为待确认；不要臆造精确数字。只有实际工具结果可证明完成，区分本地保存和提交、推送、远程核验。遇到语音确认门时停止对应操作，交给语音入口续接，不在 agent 内调用 openclaw_agent_consult；不得通过计划任务或其他工具绕过确认。', responseStyle: '直接给出本轮应播报的简短中文回答，不要让语音层重新解释或主持流程。' };
    if (pendingConfirmation && /^(确认|確認|是|是的|好的|可以|yes|confirm)[。.!！\s]*$/iu.test(raw)) args.confirmationId = pendingConfirmation;
    if (typeof req.runAgentConsult === 'function') {
      const abort = new AbortController(); activeAbort = abort;
      // The host's native delegation path waits for persisted ASR and binds
      // observed assent to one unchanged action. No LLM transports the grant.
      Promise.resolve().then(() => req.runAgentConsult({prompt: raw, signal: abort.signal})).then(
        result => api.submit(callId, result),
        error => { if (!closed && !abort.signal.aborted) req.onError?.(error); },
      );
    } else req.onToolCall?.({ itemId: callId, callId, name: 'openclaw_agent_consult', args });
  }
  function interrupt() {
    timers.clearTimeout(timer);
    activeAbort?.abort(); activeAbort = undefined;
    clearPlayback(); epoch++; activeCall = undefined; calls.clear();
    send({ type: 'response.cancel' });
    req.onClearAudio?.('barge-in');
  }
  function speak(text) {
    if (closed || !text.trim()) return;
    clearPlayback(); expected = text.trim(); speaking = true;
    // No user conversation or tools are sent as a generation instruction.
    send({ type: 'conversation.item.create', item: { type: 'message', role: 'user', content: [{ type: 'input_text', text: `只逐字朗读以下文本，不要回答、解释、补充或改写：\n${expected}` }] } });
    send({ type: 'response.create' });
    playbackTimer = timers.setTimeout(() => { clearPlayback(); req.onError?.(new Error('Bailian agent-result playback timed out')); }, 30000);
  }
  return api = {
    event(m) {
      if (closed) return;
      switch (m.type) {
        case 'input_audio_buffer.speech_started': interrupt(); return true;
        case 'conversation.item.input_audio_transcription.delta':
          if (m.delta) req.onTranscript?.('user', m.delta, false);
          return true;
        case 'conversation.item.input_audio_transcription.completed': {
          const text = String(m.transcript ?? '').trim();
          if (!text) return true;
          req.onTranscript?.('user', text, true);
          question += (question ? '\n' : '') + text;
          timers.clearTimeout(timer); timer = timers.setTimeout(flush, settleMs);
          return true;
        }
        case 'response.created':
          if (!speaking) send({ type: 'response.cancel' });
          return true;
        case 'response.audio.delta':
          if (speaking && m.delta) {
            const chunk = Buffer.from(m.delta, 'base64'); bytes += chunk.length;
            if (bytes > 8 * 1024 * 1024) { clearPlayback(); send({type:'response.cancel'}); req.onError?.(new Error('Agent-result audio exceeds bounded playback buffer')); }
            else chunks.push(chunk);
          }
          return true;
        case 'response.audio_transcript.delta':
          if (speaking) transcript += m.delta ?? '';
          return true;
        case 'response.audio_transcript.done':
          if (speaking) transcript = m.transcript ?? transcript;
          return true;
        case 'response.function_call_arguments.done': return true;
        case 'response.done': {
          if (!speaking) return true;
          const status = m.response?.status ?? 'completed';
          const exact = speechKey(expected) && speechKey(expected) === speechKey(transcript);
          const audio = chunks; const text = expected;
          clearPlayback();
          if (status !== 'completed') return true;
          if (!exact) { req.onError?.(new Error('Bailian changed the agent reply; unverified audio was withheld')); return true; }
          req.onTranscript?.('assistant', text, true);
          // Match realtime playback speed rather than flooding the App with a
          // whole buffered response. A speech interruption invalidates the pump.
          const buffer = Buffer.concat(audio), deliveryEpoch = epoch;
          let offset = 0;
          const pump = () => {
            if (closed || epoch !== deliveryEpoch) return;
            if (offset < buffer.length) {
              req.onAudio?.(buffer.subarray(offset, offset + 4800));
              offset += 4800;
            }
            if (offset < buffer.length) audioTimer = timers.setTimeout(pump, 100);
            else req.onResponseDone?.({status:'completed'});
          };
          pump();
          return true;
        }
        case 'error':
          // Cancelling an already-finished automatic response is harmless.
          if (/no active response|no response.*progress|no response.*cancel|cancellation failed/i.test(m.error?.message ?? '')) return true;
          return false;
      }
      return false;
    },
    submit(callId, result, options) {
      if (closed || callId !== activeCall || calls.get(callId) !== epoch) return;
      if (options?.willContinue || result?.status === 'working') return;
      activeCall = undefined; calls.delete(callId);
      const text = resultText(result);
      const match = /VOICE_CONFIRMATION_REQUIRED:([a-f0-9-]{36})/i.exec(text);
      pendingConfirmation = match?.[1];
      if (options?.suppressResponse || result?.status === 'cancelled') return;
      const hostChallenge = /One pending action has not run\. Say/.test(text);
      const specificChallenge = match ? text.slice(match.index + match[0].length).trim().split(' After spoken confirmation,')[0] : '';
      speak(match && specificChallenge.startsWith('待确认：') ? specificChallenge : match || hostChallenge ? '有一项待执行操作尚未运行。请说“确认”批准这项操作，或说“取消”。' : text);
    },
    speak,
    flush,
    cancel() {
      interrupt(); question = '';
      req.onResponseDone?.({status:'cancelled'});
    },
    close() { closed = true; activeAbort?.abort(); timers.clearTimeout(timer); clearPlayback(); calls.clear(); pendingConfirmation = undefined; },
  };
}
