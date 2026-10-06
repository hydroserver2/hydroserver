/**
 * Warm the dev server before the first test runs.
 *
 * Vite transforms the module graph on demand, so the first `page.goto('/')`
 * of a run used to pay for the whole app (Plotly and Vuetify included) inside
 * a 30 s test timeout, and the first test of a file lost that race. Playwright
 * starts `webServer` before global setup, so loading the app once here moves
 * that cost out of the tests; every worker afterwards gets the cached
 * transform.
 *
 * The app only pulls the rest of the graph once it mounts, so this boots it
 * the way a spec does: the same route mocks and the same seeded workspace.
 */

import { chromium, type FullConfig } from '@playwright/test'
import { seedWorkspaceSelection } from './app'
import { installMocks } from './mocks'

const WARMUP_TIMEOUT = 180_000

export default async function warmDevServer(config: FullConfig): Promise<void> {
  const baseURL = config.projects.map((p) => p.use.baseURL).find(Boolean)
  if (!baseURL) {
    throw new Error('No baseURL is configured, so the dev server cannot be warmed.')
  }

  const browser = await chromium.launch()
  try {
    const page = await browser.newPage({ baseURL })
    await installMocks(page, { qcHistories: true })
    await seedWorkspaceSelection(page)

    const response = await page.goto(baseURL, {
      waitUntil: 'load',
      timeout: WARMUP_TIMEOUT,
    })
    if (!response?.ok()) {
      throw new Error(
        `The dev server answered ${response?.status() ?? 'nothing'} for ${baseURL}.`
      )
    }
    await page.waitForSelector('[data-testid="datastreams-table"]', {
      timeout: WARMUP_TIMEOUT,
    })
  } finally {
    await browser.close()
  }
}
