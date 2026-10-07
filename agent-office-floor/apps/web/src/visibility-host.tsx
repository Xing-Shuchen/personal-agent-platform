/** Development-only browser check of host polling and visibility transitions. */
import 'pixi.js/unsafe-eval';
import React from 'react';
import { createRoot } from 'react-dom/client';
import { App } from './App.tsx';
import { syntheticState } from './synthetic.ts';
import './style.css';

const result = document.getElementById('result')!;
let hidden = false, stateReads = 0, streamAttempts = 0;
const viewerReports: boolean[] = [];
const realFetch = globalThis.fetch.bind(globalThis);
Object.defineProperty(document, 'hidden', { configurable: true, get: () => hidden });
globalThis.fetch = (async (input: RequestInfo | URL, init?: RequestInit) => {
  const path = String(input);
  if (path === '/api/floor/state') {
    stateReads++;
    return new Response(JSON.stringify(syntheticState), { status: 200,
      headers: { 'Content-Type': 'application/json' } });
  }
  if (path === '/api/floor/view') {
    viewerReports.push(JSON.parse(String(init?.body)).visible as boolean);
    return new Response(null, { status: 204 });
  }
  if (path === '/api/pap/tasks') return new Response(JSON.stringify({ generatedAt: new Date().toISOString(),
    agents: [], jobs: [], occurrences: [], timingBasis: 'nominal', activeRuns: [], openRuns: [],
    openRunCount: 0, recentRuns: [] }), { status: 200, headers: { 'Content-Type': 'application/json' } });
  return realFetch(input, init);
}) as typeof fetch;
class FakeEventSource {
  onerror: ((event: Event) => void) | null = null;
  private closed = false;
  private listeners = new Map<string, EventListenerOrEventListenerObject[]>();
  constructor() {
    const attempt = ++streamAttempts;
    setTimeout(() => {
      if (this.closed) return;
      if (attempt <= 3) this.onerror?.(new Event('error'));
      else for (const listener of this.listeners.get('floor') ?? []) {
        const event = new MessageEvent('floor', { data: JSON.stringify({ type: 'snapshot', state: syntheticState }) });
        if (typeof listener === 'function') listener(event);
        else listener.handleEvent(event);
      }
    }, 20);
  }
  addEventListener(type: string, listener: EventListenerOrEventListenerObject) {
    this.listeners.set(type, [...this.listeners.get(type) ?? [], listener]);
  }
  close() { this.closed = true; }
}
globalThis.EventSource = FakeEventSource as unknown as typeof EventSource;

async function until(check: () => boolean, label: string): Promise<void> {
  const deadline = Date.now() + 10000;
  while (!check()) {
    if (Date.now() > deadline) throw new Error(`timed out: ${label}`);
    await new Promise(resolve => setTimeout(resolve, 20));
  }
}
createRoot(document.getElementById('root')!).render(<App initialState={syntheticState} />);
void (async () => {
  await until(() => document.body.textContent?.includes('页面传输：快照轮询') === true, 'polling fallback');
  hidden = true;
  document.dispatchEvent(new Event('visibilitychange'));
  const beforeHidden = stateReads;
  await new Promise(resolve => setTimeout(resolve, 2500));
  if (stateReads !== beforeHidden) throw new Error(`hidden polling remained fast: ${stateReads - beforeHidden} reads`);
  if (viewerReports.at(-1) !== false) throw new Error('viewer hint did not report hidden');
  hidden = false;
  document.dispatchEvent(new Event('visibilitychange'));
  await until(() => stateReads > beforeHidden && streamAttempts >= 4 && viewerReports.at(-1) === true,
    'visible snapshot, stream and viewer hint');
  result.textContent = 'PASS · 隐藏后降频；恢复可见时立即读取快照、重连 SSE 并报告观察者';
})().catch(error => { result.textContent = `FAIL · ${error instanceof Error ? error.message : String(error)}`; });
