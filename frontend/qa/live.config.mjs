import { defineConfig } from 'playwright/test'
import { fileURLToPath } from 'node:url'
export default defineConfig({
  testDir: './live',
  timeout: 45000,
  expect: { timeout: 8000 },
  workers: 1,
  retries: 0,
  reporter: [['list'], ['html', { outputFolder: 'live-report', open: 'never' }]],
  outputDir: 'live-results',
  // No trace/network body artifacts: credential tests use an ephemeral generated password.
  use: { baseURL: 'http://127.0.0.1:5175', trace: 'off', screenshot: 'only-on-failure' },
  webServer: [
    { cwd: fileURLToPath(new URL('../../backend/', import.meta.url)), command: 'python -m uvicorn app.main:app --host 127.0.0.1 --port 8000', url: 'http://127.0.0.1:8000/', timeout: 30000, reuseExistingServer: false },
    { cwd: fileURLToPath(new URL('../', import.meta.url)), command: 'npm run dev -- --host 127.0.0.1 --port 5175 --strictPort', url: 'http://127.0.0.1:5175', timeout: 30000, reuseExistingServer: false,
      env: { VITE_API_BASE_URL: 'http://127.0.0.1:8000', VITE_ENABLE_DEMO_LOGIN: 'true' } },
  ],
  projects: [
    { name: 'live-desktop', use: { viewport: { width: 1440, height: 1000 } } },
    { name: 'live-mobile', use: { viewport: { width: 390, height: 844 } } },
  ],
})
