import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { fileURLToPath } from 'node:url';
export default defineConfig(({ mode }) => ({
  plugins: [react()], base: './', publicDir: '../../assets/owned',
  build: mode === 'csp-theme' || mode === 'csp-gpu' ? { rollupOptions: { input: {
    index: fileURLToPath(new URL('./index.html', import.meta.url)),
    ...(mode === 'csp-theme' ? { theme: fileURLToPath(new URL('./theme-fallback.html', import.meta.url)) } :
      { gpu: fileURLToPath(new URL('./gpu-recovery.html', import.meta.url)) })
  } } } : undefined,
  server: { host: '127.0.0.1', proxy: { '/api': 'http://127.0.0.1:4174', '/healthz': 'http://127.0.0.1:4174' } }
}));
