import { JSDOM } from 'jsdom';
import { createRequire } from 'node:module';
import { resolve, join } from 'node:path';
import { readFileSync } from 'node:fs';
import assert from 'node:assert/strict';

const dom = new JSDOM('<!doctype html><div id="app"></div>', { url: 'http://localhost/' });
for (const key of ['window', 'document', 'navigator', 'Element', 'HTMLElement', 'HTMLInputElement', 'HTMLSelectElement', 'HTMLTextAreaElement', 'Node', 'Text', 'Comment', 'Document', 'SVGElement', 'MutationObserver', 'getComputedStyle']) {
  Object.defineProperty(globalThis, key, { configurable: true, value: key === 'getComputedStyle' ? dom.window.getComputedStyle.bind(dom.window) : dom.window[key] });
}
for (const key of Object.getOwnPropertyNames(dom.window).filter(key => key.startsWith('HTML') || key.startsWith('SVG'))) {
  if (!(key in globalThis)) Object.defineProperty(globalThis, key, { configurable: true, value: dom.window[key] });
}
globalThis.requestAnimationFrame = callback => setTimeout(callback, 0);
globalThis.cancelAnimationFrame = clearTimeout;
HTMLElement.prototype.empty = function () { this.replaceChildren(); };
HTMLElement.prototype.addClass = function (name) { this.classList.add(name); };

let factory;
class Plugin {
  app = { vault: { adapter: {} }, workspace: {} };
  async loadData() { return { database: '', output: resolve(process.argv[2]), projector: resolve('../../agents/world-historian/runtime/dashboard_projector.py') }; }
  registerView(_type, value) { factory = value; }
  addRibbonIcon() {}
  addCommand() {}
  addSettingTab() {}
}
class ItemView { constructor() { this.contentEl = document.getElementById('app'); } }
class PluginSettingTab {}
class FileSystemAdapter {}
const obsidian = { Plugin, ItemView, PluginSettingTab, FileSystemAdapter, Modal: class {}, Notice: class {}, Setting: class {} };

const require = createRequire(import.meta.url);
const Module = require('node:module');
const originalLoad = Module._load;
Module._load = function (id, ...rest) { return id === 'obsidian' ? obsidian : originalLoad.call(this, id, ...rest); };
let PluginClass;
try { PluginClass = require('./main.js').default; }
finally { Module._load = originalLoad; }
const plugin = new PluginClass();
await plugin.onload();
const output=resolve(process.argv[2]);
const pointer=readFileSync(join(output,'CURRENT'),'utf8').trim();
const firstThread=JSON.parse(readFileSync(join(output,'generations',pointer,'threads.json'),'utf8'))[0];
assert.ok((await plugin.search(firstThread.title.slice(0,5))).some(hit=>hit.type==='thread'&&hit.id===firstThread.thread_id));
assert.equal(typeof factory, 'function');
const view = factory({});
await view.onOpen();
await new Promise(resolve => setTimeout(resolve, 0));
assert.match(document.body.textContent, /World Historian/);
assert.ok(document.querySelectorAll('.wh-row').length > 0);
console.log('Built Obsidian plugin bundle mounted successfully');
