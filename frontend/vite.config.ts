/// <reference types="vitest" />
import path from 'node:path';
import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

// In development the browser talks to Vite (same origin) and Vite forwards /api to the backend,
// so there are no CORS problems and the refresh cookie works exactly as in production.
const backend = process.env.VITE_API_PROXY ?? 'http://localhost:8000';

// Vitest 2 and Vite 6 disagree about the `test` key's type, so keep the config in a variable
// (excess-property checks only apply to inline object literals). Runtime behaviour is unchanged.
const config = {
  plugins: [react(), tailwindcss()],
  resolve: { alias: { '@': path.resolve(__dirname, 'src') } },
  server: { port: 5173, proxy: { '/api': { target: backend, changeOrigin: false } } },
  build: { sourcemap: true, target: 'es2022' },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
    css: false,
    exclude: ['e2e/**', 'node_modules/**'],
  },
};

export default defineConfig(config);