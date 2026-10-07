import assert from 'node:assert/strict';
import { readdirSync, readFileSync } from 'node:fs';
import { extname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import test from 'node:test';

const root = fileURLToPath(new URL('../../packages/office-scene/src/', import.meta.url));
function sourceFiles(directory: string): string[] {
  return readdirSync(directory, { withFileTypes: true }).flatMap(entry => {
    const path = join(directory, entry.name);
    return entry.isDirectory() ? sourceFiles(path) : ['.ts', '.tsx'].includes(extname(path)) ? [path] : [];
  });
}

test('office scene keeps business data and runtime dependencies outside its package', () => {
  const files = sourceFiles(root);
  assert.ok(files.length > 0);
  for (const path of files) {
    const source = readFileSync(path, 'utf8');
    const imports = [...source.matchAll(/\b(?:from\s*|import\s*\(|import\s*)['"]([^'"]+)['"]/g)]
      .map(match => match[1]);
    for (const target of imports) {
      assert.ok(target.startsWith('.') || ['react', 'pixi.js', '@pap/floor-contract'].includes(target),
        `${path} imports ${target}`);
    }
    assert.doesNotMatch(source, /window\.cth|@\/store\/store|\b(?:Electron|electron|PTY)\b/,
      `${path} contains a removed MD runtime dependency`);
  }
});
