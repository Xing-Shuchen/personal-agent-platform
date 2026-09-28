import esbuild from 'esbuild';
import { readFileSync } from 'node:fs';
import { compile } from 'svelte/compiler';

const sveltePlugin = {
  name: 'svelte',
  setup(build) {
    build.onLoad({ filter: /\.svelte$/ }, async ({ path }) => {
      const source = readFileSync(path, 'utf8');
      const compiled = compile(source, { filename: path, generate: 'client', css: 'injected' });
      return { contents: compiled.js.code, loader: 'js', warnings: compiled.warnings.map(w => ({ text: w.message })) };
    });
  }
};
await esbuild.build({ entryPoints: ['src/main.ts'], outfile: 'main.js', bundle: true,
  platform: 'node', conditions: ['browser'], format: 'cjs', target: 'es2022', external: ['obsidian'], plugins: [sveltePlugin] });
