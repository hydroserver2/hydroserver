/**
 * Rate-of-change filter: the input is divided by 100 before being
 * dispatched (the UI suffixes it with `%`), so a generous threshold
 * like `> -100` matches every valid rate in the fixture series.
 */

import { expect, test } from '@playwright/test'
import { installMocks } from './support/mocks'
import { openOp, setupEditView, waitForSelection } from './support/app'

test.describe('filter: rate of change', () => {
  test.beforeEach(async ({ page }) => {
    await installMocks(page)
    await setupEditView(page)
  })

  test('applies rate-of-change filter and populates a selection', async ({
    page,
  }) => {
    await openOp(page, 'rateOfChange')
    await page.getByRole('spinbutton', { name: 'Rate of change' }).fill('-100')
    await page.getByRole('button', { name: /apply filter/i }).click()
    await waitForSelection(page, 1)

    // Filter entry may be collapsed to a rolled-up "Selection" row after
    // dispatchSelection fires — accept either as proof the filter ran.
    const row = page
      .locator('[data-testid^="history-item-"]')
      .filter({ hasText: /Rate Of Change|Selection/ })
    await expect(row.first()).toBeVisible()
  })
})
