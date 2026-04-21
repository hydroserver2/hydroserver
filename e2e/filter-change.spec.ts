/**
 * Change filter: selects points whose Y delta vs. the previous sample
 * satisfies a comparator. With the fixture sine-wave series the delta
 * varies smoothly, so `>= -10` matches every sample past index 0.
 */

import { expect, test } from '@playwright/test'
import { installMocks } from './support/mocks'
import { openOp, setupEditView, waitForSelection } from './support/app'

test.describe('filter: change threshold', () => {
  test.beforeEach(async ({ page }) => {
    await installMocks(page)
    await setupEditView(page)
  })

  test('applies the change filter and populates a selection', async ({ page }) => {
    await openOp(page, 'change')
    // `Change` is the numeric threshold input label. Use the
    // spinbutton role to disambiguate from the "Clear Change" icon
    // button Vuetify renders on number fields.
    await page.getByRole('spinbutton', { name: 'Change' }).fill('-10')
    await page.getByRole('button', { name: /apply filter/i }).click()
    await waitForSelection(page, 1)

    // The filter dispatch lands a history row; the app's replace-in-place
    // semantics may collapse it into a subsequent "Selection" entry once
    // dispatchSelection runs, so we accept either the op name or the
    // rolled-up Selection label as proof the filter ran.
    const row = page
      .locator('[data-testid^="history-item-"]')
      .filter({ hasText: /Change|Selection/ })
    await expect(row.first()).toBeVisible()
  })
})
