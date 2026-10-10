/** Isolated browser fixture for context-loss wiring; excluded from production builds. */
import 'pixi.js/unsafe-eval';
import React from 'react';
import { createRoot } from 'react-dom/client';
import { App } from './App.tsx';
import { syntheticState } from './synthetic.ts';
import './style.css';

function Fixture() {
  const [losses, setLosses] = React.useState(0);
  const lose = () => {
    const canvas = document.querySelector<HTMLCanvasElement>('.office-canvas canvas');
    if (!canvas) return;
    canvas.dispatchEvent(new Event('webglcontextlost', { cancelable: true }));
    setLosses(value => value + 1);
  };
  return <><div style={{ maxWidth: 1450, margin: '8px auto', padding: '0 34px' }}>
    <button onClick={lose}>模拟图形上下文丢失</button> <span>已发送 {losses} 次</span>
  </div><App initialState={syntheticState} transportDisabled /></>;
}

createRoot(document.getElementById('root')!).render(<Fixture />);
