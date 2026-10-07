/** Isolated visual fixture: never imported by the production entry. */
import 'pixi.js/unsafe-eval';
import React from 'react';
import { createRoot } from 'react-dom/client';
import { OfficeScene } from '@pap/office-scene';
import { syntheticState } from './synthetic.ts';
import './style.css';

createRoot(document.getElementById('root')!).render(<div style={{ maxWidth: 1000, margin: '30px auto' }}>
  <h1>合成 FloorState 场景测试</h1>
  <OfficeScene state={syntheticState} ids={Object.keys(syntheticState.agents)} selectedId={null} onSelect={() => {}} />
</div>);
