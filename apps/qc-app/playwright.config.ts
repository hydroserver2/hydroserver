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
  retries: 1,
  workers: 2,
  reporter,
  outputDir: 'test-results',
  use: {
    baseURL: appBaseUrl,
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'on-first-retry',
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
    {
      name: 'firefox-smoke',
      testMatch: [
        '**/smoke.spec.ts',
        '**/navigation.spec.ts',
        '**/all-operations.spec.ts',
        '**/submit.spec.ts',
      ],
      use: { ...devices['Desktop Firefox'] },
    },
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
