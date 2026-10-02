import { defineConfig, devices } from 'playwright/test'

export default defineConfig({
  testDir: './browser',
  timeout: 45_000,
  expect: { timeout: 8000 },
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: process.env.CI ? 2 : undefined,
  reporter: [['list'], ['html', { open: 'never' }]],
  use: { baseURL: 'http://127.0.0.1:5174', trace: 'retain-on-failure', screenshot: 'only-on-failure' },
  webServer: {
    command: 'npm run preview:visual -- --port 5174 --strictPort',
    url: 'http://127.0.0.1:5174/preview.html',
    reuseExistingServer: false,
    timeout: 30_000,
  },
  projects: [
    { name: 'desktop-light', use: { viewport: { width: 1440, height: 1000 }, colorScheme: 'light' } },
    { name: 'desktop-dark', use: { viewport: { width: 1440, height: 1000 }, colorScheme: 'dark' } },
    { name: 'tablet', use: { viewport: { width: 1024, height: 768 }, colorScheme: 'light' } },
    { name: 'mobile-light', use: { ...devices['Pixel 7'], viewport: { width: 390, height: 844 }, colorScheme: 'light' } },
    { name: 'mobile-dark', use: { ...devices['Pixel 7'], viewport: { width: 390, height: 844 }, colorScheme: 'dark' } },
    { name: 'small-mobile', use: { viewport: { width: 320, height: 740 }, colorScheme: 'light' } },
    { name: 'reduced-motion', use: { viewport: { width: 1440, height: 1000 }, colorScheme: 'light', contextOptions: { reducedMotion: 'reduce' } } },
  ],
})
