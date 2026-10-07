/** Browser-only 20-cycle mount and unmount fixture; excluded from production. */
import 'pixi.js/unsafe-eval';
import React from 'react';
import { createRoot } from 'react-dom/client';
import { OfficeScene } from '@pap/office-scene';
import { syntheticState } from './synthetic.ts';
import './style.css';

const mount = document.getElementById('mount')!;
const result = document.getElementById('result')!;
const root = createRoot(mount);
const nativeRaf = window.requestAnimationFrame.bind(window);
const nativeCancel = window.cancelAnimationFrame.bind(window);
const pendingFrames = new Set<number>();
window.requestAnimationFrame = callback => {
  const id = nativeRaf(time => { pendingFrames.delete(id); callback(time); });
  pendingFrames.add(id);
  return id;
};
window.cancelAnimationFrame = id => { pendingFrames.delete(id); nativeCancel(id); };
const add = document.addEventListener.bind(document);
const remove = document.removeEventListener.bind(document);
let visibilityListeners = 0;
document.addEventListener = ((type: string, listener: EventListenerOrEventListenerObject, options?: boolean | AddEventListenerOptions) => {
  if (type === 'visibilitychange') visibilityListeners++;
  add(type, listener, options);
}) as typeof document.addEventListener;
document.removeEventListener = ((type: string, listener: EventListenerOrEventListenerObject, options?: boolean | EventListenerOptions) => {
  if (type === 'visibilitychange') visibilityListeners--;
  remove(type, listener, options);
}) as typeof document.removeEventListener;

async function until(check: () => boolean, label: string): Promise<void> {
  const deadline = Date.now() + 5000;
  while (!check()) {
    if (Date.now() > deadline) throw new Error(`timed out: ${label}`);
    await new Promise(resolve => setTimeout(resolve, 20));
  }
}
const frame = () => new Promise<void>(resolve => nativeRaf(() => resolve()));
let sceneFrames = 0;
async function checkVisibilityTicker(): Promise<void> {
  const previous = Object.getOwnPropertyDescriptor(document, 'hidden');
  let forcedHidden = false;
  Object.defineProperty(document, 'hidden', { configurable: true, get: () => forcedHidden });
  try {
    forcedHidden = true;
    document.dispatchEvent(new Event('visibilitychange'));
    const stoppedAt = sceneFrames;
    await new Promise(resolve => setTimeout(resolve, 300));
    if (sceneFrames !== stoppedAt) throw new Error('scene ticker advanced while hidden');
    forcedHidden = false;
    document.dispatchEvent(new Event('visibilitychange'));
    await until(() => sceneFrames > stoppedAt, 'ticker resumes when visible');
  } finally {
    if (previous) Object.defineProperty(document, 'hidden', previous);
    else Reflect.deleteProperty(document, 'hidden');
    document.dispatchEvent(new Event('visibilitychange'));
  }
}
async function run() {
  for (let i = 1; i <= 20; i++) {
    root.render(<OfficeScene state={syntheticState} ids={Object.keys(syntheticState.agents)} selectedId={null} onSelect={() => {}} onFrame={() => { sceneFrames++; }} />);
    await until(() => mount.querySelectorAll('canvas').length === 1, `canvas mount ${i}`);
    if (i === 1) await checkVisibilityTicker();
    await frame();
    root.render(null);
    await until(() => mount.querySelectorAll('canvas').length === 0, `canvas removal ${i}`);
    await frame(); await frame();
    if (visibilityListeners !== 0) throw new Error(`visibility listener leak after cycle ${i}: ${visibilityListeners}`);
    if (pendingFrames.size !== 0) throw new Error(`animation frame leak after cycle ${i}: ${pendingFrames.size}`);
    result.textContent = `已完成 ${i}/20 次挂载与卸载`;
  }
  result.textContent = 'PASS · 隐藏时停止、恢复可见时重启动画；20 次挂载与卸载均清理 Canvas、监听器和动画帧';
}
void run().catch(error => { result.textContent = `FAIL · ${error instanceof Error ? error.message : String(error)}`; });
