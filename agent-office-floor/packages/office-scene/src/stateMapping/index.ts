import type { FloorAgent } from '@pap/floor-contract';
export type VisualState = Readonly<{ label: string; color: number; animation: 'idle'|'walk'|'type'|'read'; glyph: string; screenOn: boolean }>;
export function visualState(agent: FloorAgent): VisualState {
  if (agent.freshness !== 'fresh') return { label: agent.freshness === 'stale' ? '状态过期' : '状态未知', color: 0x849098, animation: 'idle', glyph: '?', screenOn: false };
  if (agent.work.compacting) return { label: '整理上下文', color: 0x7898e2, animation: 'read', glyph: '◌', screenOn: true };
  switch (agent.work.status) {
    case 'running': {
      const phase = agent.work.phase;
      const reading = phase === 'reading' || phase === 'thinking' || phase === 'finishing' || phase === 'waiting_child';
      const tool = agent.work.tool?.name;
      const shortTool = tool && (tool.length > 14 ? `${tool.slice(0, 13)}…` : tool);
      const label = phase === 'reading' ? '读取中' : phase === 'thinking' ? '处理中' :
        phase === 'finishing' ? '收尾中' : phase === 'waiting_child' ? '等待子会话' :
        shortTool ? `工具 ${shortTool}` : '运行中';
      return { label,
        color: 0x58b99a, animation: reading ? 'read' : 'type', glyph: '', screenOn: true };
    }
    case 'waiting_input': return { label: '等待输入', color: 0xf3bf63, animation: 'idle', glyph: '!', screenOn: false };
    case 'error': return { label: agent.work.latestOutcome?.result === 'timeout' ? '运行超时' : '运行失败', color: 0xf08080, animation: 'idle', glyph: '!', screenOn: false };
    case 'completed': return { label: '本轮已完成', color: 0x72b1ef, animation: 'idle', glyph: '', screenOn: false };
    case 'queued': return { label: '排队中', color: 0xc2a7ed, animation: 'idle', glyph: '…', screenOn: false };
    case 'stopped': return { label: '已停止', color: 0xaab1bb, animation: 'idle', glyph: '■', screenOn: false };
    case 'idle': return { label: '空闲', color: 0xaab1bb, animation: 'idle', glyph: '', screenOn: false };
    default: return { label: '状态未知', color: 0x849098, animation: 'idle', glyph: '?', screenOn: false };
  }
}
