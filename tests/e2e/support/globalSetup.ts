import type { FullConfig } from '@playwright/test'
import { chromium, request } from '@playwright/test'

const FRONTEND_READY_TIMEOUT_MS = 30_000
const APP_BOOT_ROUTE = '/browse'

function getAppBaseUrl(config: FullConfig) {
  const projectBaseUrl = config.projects[0]?.use?.baseURL
  if (typeof projectBaseUrl === 'string' && projectBaseUrl.length > 0) {
    return projectBaseUrl.replace(/\/$/, '')
  }

  const appHost = process.env.E2E_APP_HOST || '127.0.0.1'
  const appPort = process.env.E2E_APP_PORT || '14173'
  return `http://${appHost}:${appPort}`
}

function getApiBaseUrl() {
  const apiHost = process.env.E2E_API_HOST || '127.0.0.1'
  const apiPort = process.env.E2E_API_PORT || '18000'
  return `http://${apiHost}:${apiPort}`
}

function summarizeMessages(title: string, messages: string[]) {
  if (!messages.length) return `${title}: none`
  return `${title}:\n- ${messages.slice(0, 5).join('\n- ')}`
}

export default async function globalSetup(config: FullConfig) {
  const appBaseUrl = getAppBaseUrl(config)
  const apiBaseUrl = getApiBaseUrl()

  const apiContext = await request.newContext({ baseURL: apiBaseUrl })
  const apiResponse = await apiContext.get('/api/data/workspaces')
  if (!apiResponse.ok()) {
    await apiContext.dispose()
    throw new Error(
      `E2E startup check failed before browser launch: API readiness probe returned ${apiResponse.status()} from ${apiBaseUrl}/api/data/workspaces`
    )
  }
  await apiContext.dispose()

  const browser = await chromium.launch()
  const page = await browser.newPage()
  const consoleErrors: string[] = []
  const pageErrors: string[] = []

  page.on('console', (message) => {
    if (message.type() === 'error') {
      consoleErrors.push(message.text())
    }
  })
  page.on('pageerror', (error) => {
    pageErrors.push(error.stack || error.message)
  })

  try {
    const targetUrl = `${appBaseUrl}${APP_BOOT_ROUTE}`
    const response = await page.goto(targetUrl, { waitUntil: 'domcontentloaded' })

    if (!response) {
      throw new Error(
        `E2E startup check failed: no HTTP response was received from ${targetUrl}`
      )
    }

    if (!response.ok()) {
      throw new Error(
        `E2E startup check failed: frontend returned ${response.status()} for ${targetUrl}`
      )
    }

    await page.waitForFunction(
      () => {
        const appRoot = document.querySelector('#app')
        return !!appRoot && appRoot.children.length > 0
      },
      { timeout: FRONTEND_READY_TIMEOUT_MS }
    )

    await page.locator('.v-application').waitFor({
      state: 'visible',
      timeout: 10_000,
    })
  } catch (error) {
    const bodyText =
      (await page.locator('body').innerText().catch(() => '')) || '<empty body>'
    const diagnostic = [
      `E2E startup check failed: the frontend did not mount successfully at ${appBaseUrl}${APP_BOOT_ROUTE}.`,
      `This usually means the Vite dev server served HTML but the Vue app never booted.`,
      `Body text snapshot: ${bodyText.trim().slice(0, 300) || '<empty body>'}`,
      summarizeMessages('Browser console errors', consoleErrors),
      summarizeMessages('Page errors', pageErrors),
      `Original error: ${error instanceof Error ? error.message : String(error)}`,
    ].join('\n')

    throw new Error(diagnostic)
  } finally {
    await browser.close()
  }
}
