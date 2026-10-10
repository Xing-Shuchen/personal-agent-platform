import { useEffect, useState } from 'react';
import { requireViewer } from './viewer-access.ts';

type Agent = { id: string; description: string; enabled: boolean };
type Job = { key: string; agentId: string; name: string; schedule: string; timezone: string | null; enabled: boolean; nextNominalAt: string | null };
export type Occurrence = { key: string; agentId: string; name: string; timezone: string | null; enabled: boolean; nominalAt: string; dispatchAt: string };
type Run = { runId: string; agentId: string | null; jobId: string | null; startedAt?: string | null; completedAt?: string | null; status?: string | null };
type Tasks = { generatedAt: string; agents: Agent[]; jobs: Job[]; occurrences: Occurrence[]; timingBasis: 'jittered' | 'nominal'; activeRuns: Run[]; openRuns: Run[]; openRunCount: number; recentRuns: Run[] };

function valid(value: unknown): value is Tasks {
  if (!value || typeof value !== 'object') return false;
  const v = value as Record<string, unknown>;
  return typeof v.generatedAt === 'string' && Number.isSafeInteger(v.openRunCount) && Number(v.openRunCount) >= 0 &&
    (v.timingBasis === 'jittered' || v.timingBasis === 'nominal') &&
    ['agents', 'jobs', 'occurrences', 'activeRuns', 'openRuns', 'recentRuns'].every(key => Array.isArray(v[key]));
}
function when(value: string | null | undefined): string {
  if (!value) return '时间未提供';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? '时间未提供' : date.toLocaleString('zh-CN');
}
function runTitle(run: Run): string {
  const job = run.agentId && run.jobId?.startsWith(`${run.agentId}/`)
    ? run.jobId.slice(run.agentId.length + 1) : run.jobId;
  return [run.agentId, job].filter(Boolean).join(' / ') || run.runId;
}
function runStatus(value: string | null | undefined): string {
  return value === 'success' ? '成功' : value === 'failed' ? '失败' :
    value === 'not_ready' ? '尚未就绪' : '结果未提供';
}
function scheduleList(items: Occurrence[], basis: Tasks['timingBasis']) {
  return <ul>{items.map(item => <li key={`${item.key}:${item.nominalAt}`}><strong>{item.agentId} / {item.name}</strong>
    <span>{when(item.dispatchAt)}{!item.enabled ? '（若启用）' : basis === 'nominal' ? '（名义时间）' : '（预计派发）'} · {item.timezone ?? '系统时区'}</span></li>)}</ul>;
}

export function splitOccurrences(items: readonly Occurrence[], nowMs: number) {
  const hourEnd = nowMs + 60 * 60 * 1000;
  const future = items.filter(item => new Date(item.dispatchAt).getTime() >= nowMs)
    .sort((a, b) => new Date(a.dispatchAt).getTime() - new Date(b.dispatchAt).getTime() ||
      a.key.localeCompare(b.key) || a.nominalAt.localeCompare(b.nominalAt));
  return {
    soon: future.filter(item => item.enabled && new Date(item.dispatchAt).getTime() <= hourEnd),
    later: future.filter(item => item.enabled && new Date(item.dispatchAt).getTime() > hourEnd),
    disabled: future.filter(item => !item.enabled)
  };
}

export function PapTasks() {
  const [tasks, setTasks] = useState<Tasks | null>(null);
  const [error, setError] = useState(false);
  const [nowMs, setNowMs] = useState(() => Date.now());
  useEffect(() => {
    const timer = window.setInterval(() => setNowMs(Date.now()), 15000);
    return () => clearInterval(timer);
  }, []);
  useEffect(() => {
    let disposed = false;
    let timer: number | undefined;
    let requestId = 0;
    const schedule = () => { timer = window.setTimeout(refresh, document.hidden ? 60000 : 15000); };
    const refresh = async () => {
      const current = ++requestId;
      if (timer !== undefined) { clearTimeout(timer); timer = undefined; }
      try {
        const response = await fetch('/api/pap/tasks', { cache: 'no-store' });
        const value: unknown = requireViewer(response).ok ? await response.json() : null;
        if (!valid(value)) throw new Error('invalid PAP task response');
        if (!disposed && current === requestId) { setTasks(value); setNowMs(Date.now()); setError(false); }
      } catch { if (!disposed && current === requestId) { setNowMs(Date.now()); setError(true); } }
      if (!disposed && current === requestId) schedule();
    };
    const visibility = () => {
      if (timer !== undefined) { clearTimeout(timer); timer = undefined; }
      if (document.hidden) {
        ++requestId;
        schedule();
      } else void refresh();
    };
    document.addEventListener('visibilitychange', visibility);
    void refresh();
    return () => { disposed = true; ++requestId; if (timer !== undefined) clearTimeout(timer);
      document.removeEventListener('visibilitychange', visibility); };
  }, []);
  const enabled = tasks?.jobs.filter(job => job.enabled) ?? [];
  const { soon, later, disabled } = splitOccurrences(tasks?.occurrences ?? [], nowMs);
  return <section id="pap-tasks" className="pap-tasks" aria-label="PAP 任务">
    <div className="panel-head"><h2>PAP 任务</h2><span>{tasks ? `本地记录 · ${when(tasks.generatedAt)}` : '本地记录'}</span></div>
    {error && <p className="pap-note">PAP 任务数据暂时不可用{tasks ? '；以下为上次读取结果。' : '。'}</p>}
    {tasks && <div className="pap-task-body">
      <div className="pap-stat-row"><div><strong>{tasks.activeRuns.length}</strong><span>进程仍在的 PAP 运行</span></div><div><strong>{enabled.length}</strong><span>已启用的计划任务</span></div><div><strong>{tasks.jobs.length}</strong><span>已声明的任务</span></div><div><strong>{tasks.agents.filter(agent => agent.enabled).length}/{tasks.agents.length}</strong><span>已启用的 PAP 专员</span></div></div>
      <div className="pap-task-columns"><section><h3>即将到来 · 未来 1 小时 <small>{soon.length}</small></h3>{soon.length ? scheduleList(soon, tasks.timingBasis) : <p className="pap-note">未来 1 小时没有已启用任务的预计派发时间。</p>}<p className="pap-footnote">按预计派发时间排序；实际执行还取决于 pap tick 是否运行。</p></section>
      <section><h3>之后的计划任务 <small>{later.length}</small></h3>{later.length ? scheduleList(later, tasks.timingBasis) : <p className="pap-note">没有更晚的已启用任务。每项重复任务最多展示后续 8 次。</p>}<p className="pap-footnote">重复任务按每次预计时间列出；每项展示接下来 1 小时内的全部次数，以及之后最多 8 次。</p></section>
      <section><h3>未启用任务 · 时间预览 <small>{disabled.length}</small></h3>{disabled.length ? scheduleList(disabled, tasks.timingBasis) : <p className="pap-note">没有未启用任务。</p>}<p className="pap-footnote">这些任务不会由 pap tick 执行；这里只预览声明的重复时间。</p></section>
      <section><h3>PAP 进程仍在</h3>{tasks.activeRuns.length ? <ul>{tasks.activeRuns.map(run => <li key={run.runId}><strong>{runTitle(run)}</strong><span>{when(run.startedAt)} · 进程身份已确认，任务状态仍以结束记录为准</span></li>)}</ul> : <p className="pap-note">没有确认仍在的 PAP 执行进程。</p>}</section>
      <section><h3>开始后未找到结束记录 <small>{tasks.openRunCount}</small></h3>{tasks.openRuns.length ? <ul>{tasks.openRuns.slice(0, 5).map(run => <li key={run.runId}><strong>{runTitle(run)}</strong><span>{when(run.startedAt)} · 运行状态未确认</span></li>)}</ul> : <p className="pap-note">没有未配对的开始记录。</p>}</section>
      <section><h3>最近完成</h3>{tasks.recentRuns.length ? <ul>{tasks.recentRuns.slice(0, 5).map(run => <li key={run.runId}><strong>{runTitle(run)}</strong><span>{when(run.completedAt)} · {runStatus(run.status)}</span></li>)}</ul> : <p className="pap-note">没有完成记录。</p>}</section>
      <section><h3>PAP 专员身份</h3><ul>{tasks.agents.map(agent => <li key={agent.id}><strong>{agent.id} <small>{agent.enabled ? '已启用' : '未启用'}</small></strong><span>{agent.description}</span></li>)}</ul></section></div>
    </div>}
  </section>;
}
