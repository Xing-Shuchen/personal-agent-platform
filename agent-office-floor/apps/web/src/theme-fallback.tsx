/** Built only in csp-theme mode; the primary map deliberately returns 404. */
import 'pixi.js/unsafe-eval';
import React from 'react';
import { createRoot } from 'react-dom/client';
import { OfficeScene, ownedOffice } from '@pap/office-scene';
import { syntheticState } from './synthetic.ts';
import './style.css';

const missingTheme = { ...ownedOffice, id: 'missing-custom', mapUrl: '/theme/missing.tmj' };
createRoot(document.getElementById('root')!).render(<main className="office-app">
  <h1>自定义主题回落测试</h1>
  <OfficeScene state={syntheticState} ids={Object.keys(syntheticState.agents)}
    selectedId={null} onSelect={() => {}} theme={missingTheme} />
  <ul className="roster">{Object.values(syntheticState.agents).map(agent =>
    <li key={agent.id}>{agent.name}</li>)}</ul>
</main>);
