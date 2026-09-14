/**
 * The editor plot fills its container once the Edit view opens, whether it
 * was entered through the nav rail or through Start editing. Plotly can lay
 * the plot out while the view is still switching, so the resize observer has
 * to catch up to the container's final size.
 */

import { expect, test, type Page } from '@playwright/test'
import { installMocks } from './support/mocks'
import { setupEditView, setupSessionEditView } from './support/app'

/** Largest gap in px between Plotly's laid-out size and the plot div. */
function layoutMismatch(page: Page): Promise<number> {
  return page.evaluate(() => {
    const gd = document.querySelector('[data-testid="main-plot"]') as
      | (HTMLElement & { _fullLayout?: { width: number; height: number } })
      | null
    const layout = gd?._fullLayout
    if (!gd || !layout) return Number.MAX_SAFE_INTEGER
    return Math.max(
      Math.abs(layout.width - gd.offsetWidth),
      Math.abs(layout.height - gd.offsetHeight)
    )
  })
}

test.describe('editor plot layout', () => {
  test.beforeEach(async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 })
  })

  test('fills its container after entering through the rail', async ({
    page,
  }) => {
    await installMocks(page)
    await setupEditView(page)
    await expect
      .poll(() => layoutMismatch(page), { timeout: 5_000 })
      .toBeLessThanOrEqual(1)
  })

  test('fills its container after starting a session', async ({ page }) => {
    await installMocks(page, { qcHistories: true })
    await setupSessionEditView(page)
    await expect
      .poll(() => layoutMismatch(page), { timeout: 5_000 })
      .toBeLessThanOrEqual(1)
  })
})
