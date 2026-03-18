import { defineConfig, devices } from '@playwright/test'
import path from 'path'

const repoRoot = path.resolve(__dirname, '../..')
const apiDir = path.join(repoRoot, 'django')
const appDir = path.join(repoRoot, 'apps/data-management')
const e2ePython = process.env.E2E_PYTHON || 'python3.11'
const apiHost = process.env.E2E_API_HOST || '127.0.0.1'
const apiPort = process.env.E2E_API_PORT || '18000'
const apiBaseUrl = `http://${apiHost}:${apiPort}`
const appHost = process.env.E2E_APP_HOST || '127.0.0.1'
const appPort = process.env.E2E_APP_PORT || '14173'
const appBaseUrl = `http://${appHost}:${appPort}`
const e2eDatabaseUrl =
  process.env.E2E_DATABASE_URL ||
  'postgresql://hsdbadmin:admin@127.0.0.1:5432/hydroserver_e2e'
const e2eAdminDatabaseUrl =
  process.env.E2E_ADMIN_DATABASE_URL ||
  'postgresql://hsdbadmin:admin@127.0.0.1:5432/postgres'

export default defineConfig({
  testDir: path.join(__dirname, 'specs'),
  globalSetup: path.join(__dirname, 'support', 'globalSetup.ts'),
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  timeout: 60 * 1000,
  expect: {
    timeout: 10 * 1000,
  },
  workers: process.env.CI ? 2 : 1,
  reporter: process.env.CI
    ? [
        ['list'],
        ['github'],
        ['html', { open: 'never' }],
        ['junit', { outputFile: 'test-results/results.xml' }],
      ]
    : [['list'], ['html', { open: 'never' }]],
  use: {
    baseURL: appBaseUrl,
    trace: process.env.CI ? 'on-first-retry' : 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
      },
    },
  ],
  webServer: [
    {
      command: `${e2ePython} ../tests/e2e/scripts/ensure_e2e_database.py && ${e2ePython} manage.py setup_e2e_data && ${e2ePython} manage.py runserver ${apiHost}:${apiPort}`,
      cwd: apiDir,
      env: {
        ...process.env,
        DATABASE_URL: e2eDatabaseUrl,
        E2E_DATABASE_URL: e2eDatabaseUrl,
        E2E_ADMIN_DATABASE_URL: e2eAdminDatabaseUrl,
        CELERY_BROKER_URL: process.env.CELERY_BROKER_URL || 'redis://127.0.0.1:6379/0',
        SMTP_URL: process.env.SMTP_URL || 'memory://',
        PROXY_BASE_URL: appBaseUrl,
        ALLOWED_HOSTS: '127.0.0.1,localhost',
        ANON_THROTTLE_RATE: '200/s',
        AUTH_THROTTLE_RATE: '200/s',
        DEPLOYMENT_BACKEND: 'dev',
        DEBUG: 'True',
      },
      url: `${apiBaseUrl}/api/data/workspaces`,
      reuseExistingServer: false,
      timeout: 180 * 1000,
    },
    {
      command: `npm run build && npm run preview -- --host ${appHost} --port ${appPort}`,
      cwd: appDir,
      env: {
        ...process.env,
        VITE_APP_VERSION: 'e2e',
        VITE_APP_GOOGLE_MAPS_API_KEY: '',
        VITE_APP_GOOGLE_MAPS_MAP_ID: '',
        VITE_APP_PROXY_BASE_URL: apiBaseUrl,
        VITE_HYDROSERVER_CLIENT_LOCAL: '1',
        VITE_HYDROSERVER_CLIENT_PATH: '../../packages/hydroserver-ts/src',
      },
      url: `${appBaseUrl}/browse`,
      reuseExistingServer: false,
      timeout: 300 * 1000,
    },
  ],
})
