import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  // Allow one local retry too. The shared vite dev server occasionally
  // chokes on the initial datastreams fetch under parallel-worker load,
  // and a single retry clears that class of flake without papering over
  // real regressions (CI keeps the higher count for network wobbles).
  retries: process.env.CI ? 2 : 1,
  // Cap worker count even outside CI. The default (≈ CPU cores / 2) was
  // overwhelming Firefox against the shared vite dev server — 12 of 24
  // specs timed out on `waitForSelection` because observations fetches
  // and plotly boot were starving for network / CPU time. 2 workers
  // keeps the suite parallel enough to stay fast while leaving each
  // browser enough resources to boot reliably. Chromium coped with
  // the default but benefits equally from a lower cap.
  workers: process.env.CI ? 1 : 2,
  reporter: process.env.CI ? 'github' : 'html',
  use: {
    baseURL: 'http://127.0.0.1:1203',
    trace: 'on-first-retry',
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
    { name: 'firefox', use: { ...devices['Desktop Firefox'] } },
  ],
  webServer: {
    command: 'npm run dev',
    url: 'http://127.0.0.1:1203',
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
    env: {
      VITE_APP_E2E_HOOKS: '1',
    },
  },
})
