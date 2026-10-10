import { emptyFloorState } from '@pap/floor-contract';
import type { FloorAgent, FloorStatus } from '@pap/floor-contract';

const labels: FloorStatus[] = ['running','waiting_input','error','completed','idle','queued','stopped','unknown','running','idle','completed','error'];
const agent = (i: number): FloorAgent => ({
  id: `fixture-${i}`, session: { gatewayId: 'synthetic', key: `fixture:${i}`, agentId: 'synthetic', sessionId: `s-${i}` },
  name: `测试专员 ${i+1}`, kind: 'direct', avatarKey: `appearance-${i}`,
  relation: { parentId: null, childIds: [], runningVisibleChildren: 0 },
  work: { status: labels[i % labels.length], phase: labels[i % labels.length] === 'running' ? 'executing' : null, hasActiveRun: labels[i % labels.length] === 'running', activeRunIds: labels[i % labels.length] === 'running' ? [`r-${i}`] : [], tool: null, attention: [], compacting: false, looping: false, latestOutcome: labels[i % labels.length] === 'completed' ? { runId: `r-${i}`, result: 'success', endedAtMs: Date.now(), message: null } : labels[i % labels.length] === 'error' ? { runId: `r-${i}`, result: 'error', endedAtMs: Date.now(), message: 'fixture' } : null, summary: null, summarySource: null, evidence: [] },
  model: { selected: null, selectedProvider: null, active: null, activeProvider: null },
  usage: { inputTokens: null, outputTokens: null, totalTokens: null, totalTokensFresh: null, contextTokens: null },
  progress: null, lastMessagePreview: null, metadataUpdatedAtMs: null, lastActivityAtMs: null, lastInteractionAtMs: null, lastVerifiedAtMs: Date.now(), freshness: i === 11 ? 'stale' : 'fresh'
});
export const syntheticStateForCount = (count: number) => ({ ...emptyFloorState('fixture'),
  agents: Object.fromEntries(Array.from({ length: count }, (_, i) => [`fixture-${i}`, agent(i)])) });
export const syntheticState = syntheticStateForCount(labels.length);
