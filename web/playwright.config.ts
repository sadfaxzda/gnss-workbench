import { defineConfig, devices } from '@playwright/test'
import path from 'node:path'
import { apiPort, webPort } from './ports'

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  workers: 1,
  timeout: 45000,
  expect: { timeout: 20000 },
  reporter: [['list'], ['html', { open: 'never' }]],
  use: {
    baseURL: `http://127.0.0.1:${webPort}`,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'], viewport: { width: 1440, height: 1000 } },
    },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'], viewport: { width: 1440, height: 1000 } },
    },
  ],
  webServer: [
    {
      command: `uv run --project .. gnss serve --port ${apiPort}`,
      url: `http://127.0.0.1:${apiPort}/api/health`,
      reuseExistingServer: !process.env.CI,
      env: { GNSS_RUNTIME_ROOT: path.resolve('../runtime/e2e') },
    },
    {
      command: 'pnpm dev',
      url: `http://127.0.0.1:${webPort}`,
      reuseExistingServer: !process.env.CI,
    },
  ],
})
