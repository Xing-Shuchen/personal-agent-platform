/** Development-only browser check for out-of-order PAP task responses. */
import React from 'react';
import { createRoot } from 'react-dom/client';
import { PapTasks } from './PapTasks.tsx';
import './style.css';

const result = document.getElementById('result')!;
let requests = 0;
let resolveOld: ((response: Response) => void) | null = null;
const payload = (name: string) => new Response(JSON.stringify({ generatedAt: new Date().toISOString(),
  agents: [{ id: name, description: name, enabled: false }], jobs: [], occurrences: [],
  timingBasis: 'nominal', activeRuns: [], openRuns: [], openRunCount: 0, recentRuns: [] }),
  { status: 200, headers: { 'Content-Type': 'application/json' } });
globalThis.fetch = (async (input: RequestInfo | URL) => {
  if (String(input) !== '/api/pap/tasks') throw new Error(`unexpected request: ${input}`);
  requests++;
  if (requests === 1) return new Promise<Response>(resolve => { resolveOld = resolve; });
  return payload('new-identity');
}) as typeof fetch;
async function until(check: () => boolean, label: string): Promise<void> {
  const deadline = Date.now() + 5000;
  while (!check()) {
    if (Date.now() > deadline) throw new Error(`timed out: ${label}`);
    await new Promise(resolve => setTimeout(resolve, 20));
  }
}
createRoot(document.getElementById('root')!).render(<PapTasks />);
void (async () => {
  await until(() => requests === 1 && resolveOld !== null, 'initial request');
  document.dispatchEvent(new Event('visibilitychange'));
  await until(() => requests === 2 && document.body.textContent?.includes('new-identity') === true,
    'newer request result');
  resolveOld!(payload('old-identity'));
  await new Promise(resolve => setTimeout(resolve, 100));
  if (document.body.textContent?.includes('old-identity')) throw new Error('older result replaced newer tasks');
  if (!document.body.textContent?.includes('new-identity')) throw new Error('newer result disappeared');
  result.textContent = 'PASS · 较旧的 PAP 响应最后返回，任务列表仍保留最新身份';
})().catch(error => { result.textContent = `FAIL · ${error instanceof Error ? error.message : String(error)}`; });
