import assert from 'node:assert/strict';
import test from 'node:test';
import { normalizeSessionRow } from '@pap/openclaw-adapter';
import { visualState } from '../../packages/office-scene/src/stateMapping/index.ts';

test('only a fresh running session shows its bounded current tool name', () => {
  const running = normalizeSessionRow({ key: 'k', agentId: 'a', sessionId: 's',
    status: 'running', hasActiveRun: true, activeRunIds: ['r'] }, 'g', 100);
  assert.equal(visualState(running).label, '运行中');
  const withTool = { ...running, work: { ...running.work,
    tool: { name: 'read_file', callId: 'c', phase: 'start' as const } } };
  assert.equal(visualState(withTool).label, '工具 read_file');
  assert.equal(visualState({ ...withTool, work: { ...withTool.work, phase: 'reading' } }).label, '读取中');
  for (const [phase, label] of [['thinking', '处理中'], ['finishing', '收尾中'],
    ['waiting_child', '等待子会话']] as const) {
    const visual = visualState({ ...withTool, work: { ...withTool.work, phase } });
    assert.equal(visual.label, label);
    assert.equal(visual.animation, 'read');
  }
  assert.equal(visualState({ ...withTool, freshness: 'stale' }).label, '状态过期');
  assert.equal(visualState({ ...withTool, work: { ...withTool.work, status: 'error' } }).label, '运行失败');
  assert.equal(visualState({ ...withTool, work: { ...withTool.work,
    tool: { name: 'long_tool_name_that_must_not_overlap_a_neighbor', callId: 'c', phase: 'start' } } }).label,
  '工具 long_tool_nam…');
});
