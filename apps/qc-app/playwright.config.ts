import { defineConfig, devices } from '@playwright/test'

const appHost = process.env.E2E_APP_HOST || '127.0.0.1'
const appPort = process.env.E2E_APP_PORT || '15173'
const appBaseUrl = `http://${appHost}:${appPort}`

const reporter = process.env.CI
  ? [
      ['list'] as const,
      ['github'] as const,
      ['html', { open: 'never', outputFolder: 'playwright-report' }] as const,
      ['junit', { outputFile: 'test-results/results.xml' }] as const,
    ]
  : [
      ['list'] as const,
      ['html', { open: 'never', outputFolder: 'playwright-report' }] as const,
    ]

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 1,
  workers: process.env.CI ? 1 : 2,
  reporter,
  outputDir: 'test-results',
  use: {
    baseURL: appBaseUrl,
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
    { name: 'firefox', use: { ...devices['Desktop Firefox'] } },
  ],
  webServer: {
    command: `npm run dev -- --host ${appHost} --port ${appPort}`,
    url: appBaseUrl,
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
    env: {
      ...process.env,
      VITE_APP_E2E_HOOKS: '1',
    },
  },
})
