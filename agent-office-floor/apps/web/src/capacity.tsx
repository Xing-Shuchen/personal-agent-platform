/** Synthetic capacity fixture, excluded from the production entry. */
import 'pixi.js/unsafe-eval';
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { Application } from 'pixi.js';
import { App } from './App.tsx';
import { syntheticStateForCount } from './synthetic.ts';
import './style.css';

function EmptyPixi({ onFrame, preference }: { onFrame: (atMs: number, workMs: number) => void;
  preference: 'webgl' | 'webgpu' }) {
  const host = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    const app = new Application();
    let disposed = false;
    void app.init({ width: 768, height: 480, background: '#172a38', preference }).then(() => {
      if (disposed) { app.destroy(true); return; }
      host.current?.appendChild(app.canvas);
      app.ticker.add(() => onFrame(performance.now(), 0));
    }).catch(() => { if (!disposed) setError(`${preference} 初始化失败`); });
    return () => { disposed = true; try { app.destroy(true); } catch { /* late init */ } };
  }, [onFrame, preference]);
  return <div ref={host}>{error}</div>;
}

function CanvasBaseline({ onFrame }: { onFrame: (atMs: number, workMs: number) => void }) {
  const host = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const context = host.current?.getContext('2d');
    let frame = 0;
    const tick = () => {
      const started = performance.now();
      if (context) { context.fillStyle = '#172a38'; context.fillRect(0, 0, 768, 480); }
      onFrame(performance.now(), performance.now() - started);
      frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [onFrame]);
  return <canvas ref={host} width={768} height={480} />;
}

function CapacityFixture() {
  const params = new URLSearchParams(location.search);
  const requested = Number(params.get('count') ?? 100);
  const count = Number.isInteger(requested) && requested >= 1 && requested <= 100 ? requested : 100;
  const requestedSeconds = Number(params.get('seconds') ?? 10);
  const sampleSeconds = Number.isInteger(requestedSeconds) && requestedSeconds >= 10 && requestedSeconds <= 120 ? requestedSeconds : 10;
  const sampleMs = sampleSeconds * 1000;
  const scene = params.get('scene') ?? 'full';
  const [result, setResult] = useState(`测量中：先预热 3 秒，再采样 ${sampleSeconds} 秒`);
  const [rafResult, setRafResult] = useState('浏览器 rAF 测量中');
  const meter = useRef({ started: 0, measured: 0, frames: 0, workMs: 0, finished: false });
  useEffect(() => {
    let frame = 0, started = 0, measured = 0, frames = 0;
    const tick = (now: number) => {
      if (document.hidden) { started = 0; measured = 0; frames = 0; frame = requestAnimationFrame(tick); return; }
      if (!started) started = now;
      if (now - started >= 3000) {
        if (!measured) measured = now;
        frames++;
        if (now - measured >= sampleMs) {
          setRafResult(`浏览器 rAF：${(frames * 1000 / (now - measured)).toFixed(1)} FPS（${sampleSeconds} 秒）`);
          return;
        }
      }
      frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [sampleMs, sampleSeconds]);
  const onFrame = useCallback((now: number, workMs: number) => {
    const sample = meter.current;
    if (sample.finished) return;
    if (document.hidden) { sample.started = 0; sample.measured = 0; sample.frames = 0; sample.workMs = 0; return; }
    if (!sample.started) sample.started = now;
    if (now - sample.started < 3000) return;
    if (!sample.measured) sample.measured = now;
    sample.frames++;
    sample.workMs += workMs;
    if (now - sample.measured >= sampleMs) {
      sample.finished = true;
      setResult(`${scene === 'canvas' ? 'Canvas 2D' : 'Pixi'} 完成帧率：${(sample.frames * 1000 / (now - sample.measured)).toFixed(1)} FPS，平均帧工作 ${(sample.workMs / sample.frames).toFixed(1)} ms（${sampleSeconds} 秒）`);
    }
  }, [sampleMs, sampleSeconds, scene]);
  return <><p role="status" data-frame-meter>{scene === 'full' ? `${count} 个合成会话 · ${result}` :
    scene.startsWith('empty') ? `空 Pixi ${scene === 'empty-webgpu' ? 'WebGPU 偏好' : 'WebGL'} 场景 · ${result}` :
      scene === 'canvas' ? `Canvas 2D 基线 · ${result}` : '无场景基线'} · {rafResult}</p>
    {scene === 'full' ? <App initialState={syntheticStateForCount(count)} transportDisabled onSceneFrame={onFrame} /> :
      scene.startsWith('empty') ? <EmptyPixi onFrame={onFrame} preference={scene === 'empty-webgpu' ? 'webgpu' : 'webgl'} /> :
        scene === 'canvas' ? <CanvasBaseline onFrame={onFrame} /> : null}</>;
}

createRoot(document.getElementById('root')!).render(<CapacityFixture />);
