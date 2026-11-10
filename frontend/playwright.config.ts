import { defineConfig } from '@playwright/test';

/**
 * End-to-end tests drive a REAL browser against a RUNNING stack:
 *   1. start the backend (docker compose up) and create a user (python -m scripts.init_db)
 *   2. start the frontend:  npm run dev
 *   3. E2E_ADMIN_USERNAME=... E2E_ADMIN_PASSWORD=... npm run test:e2e
 */
export default defineConfig({
  testDir: 'e2e',
  fullyParallel: false,
  retries: 0,
  reporter: [['list'], ['html', { open: 'never' }]],
  use: {
    baseURL: process.env.E2E_BASE_URL ?? 'http://localhost:5173',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
});
