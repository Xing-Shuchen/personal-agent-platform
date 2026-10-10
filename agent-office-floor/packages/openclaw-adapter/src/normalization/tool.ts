/** Accept only the identity and phase fields from a session.tool event. */
export type ToolReceipt = Readonly<{
  runId: string;
  seq: number;
  sessionKey: string;
  sessionId: string;
  agentId: string;
  callId: string;
  name: string;
  phase: 'start' | 'update' | 'end';
}>;

const id = (value: unknown, limit = 128): value is string =>
  typeof value === 'string' && value.length > 0 && value.length <= limit;
const displayName = (value: unknown): value is string =>
  id(value, 80) && /^[A-Za-z_][A-Za-z0-9_.:-]*$/.test(value) && !value.includes('..');

export function initialToolCapability(events: readonly string[]): 'unverified' | 'unsupported' {
  return events.includes('session.tool') ? 'unverified' : 'unsupported';
}

/** Only names whose operation is unambiguously a read receive the reading animation. */
export function isReadTool(name: string): boolean {
  return name === 'read_file';
}

export function toolReceipt(payload: unknown): ToolReceipt | null {
  if (!payload || typeof payload !== 'object' || Array.isArray(payload)) return null;
  const value = payload as Record<string, unknown>;
  const session = value.session;
  const data = value.data;
  if (!session || typeof session !== 'object' || Array.isArray(session) ||
      !data || typeof data !== 'object' || Array.isArray(data)) return null;
  const source = session as Record<string, unknown>;
  const tool = data as Record<string, unknown>;
  const phase = tool.phase === 'start' ? 'start' : tool.phase === 'result' ? 'end' :
    tool.phase === 'update' || tool.phase === 'input_delta' || tool.phase === 'review' ? 'update' : null;
  if (value.stream !== 'tool' || !phase || !id(value.runId) ||
      !Number.isSafeInteger(value.seq) || Number(value.seq) < 0 ||
      !id(value.sessionKey, 1024) || !id(source.key, 1024) || value.sessionKey !== source.key ||
      !id(source.sessionId) || !id(value.agentId) || !id(tool.toolCallId) ||
      !displayName(tool.name)) return null;
  return { runId: value.runId, seq: Number(value.seq), sessionKey: value.sessionKey,
    sessionId: source.sessionId, agentId: value.agentId, callId: tool.toolCallId,
    name: tool.name, phase };
}
