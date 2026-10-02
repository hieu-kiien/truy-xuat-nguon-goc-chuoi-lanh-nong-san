import { defineConfig } from 'playwright/test'
export default defineConfig({
  testDir: './staging',
  timeout: 120000,
  expect: { timeout: 30000 },
  workers: 1,
  retries: 0,
  reporter: 'list',
  outputDir: '../staging-results',
  use: { baseURL: 'https://ttcs-frontend-staging.onrender.com', trace: 'off', screenshot: 'only-on-failure' },
  projects: [
    { name: 'desktop', use: { viewport: { width: 1440, height: 1000 } } },
    { name: 'mobile', use: { viewport: { width: 390, height: 844 } } },
  ],
})
