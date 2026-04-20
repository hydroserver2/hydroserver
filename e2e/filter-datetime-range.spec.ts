/**
 * Datetime-range filter: selects points whose phenomenonTime falls
 * inside [from, to] using the DatePickerField inputs. The picker
 * defaults to the current data-selection window, so clicking Apply
 * without changing anything seeds a selection spanning the entire
 * series.
 */

import { expect, test } from '@playwright/test'
import { installMocks } from './support/mocks'
import { openOp, setupEditView, waitForSelection } from './support/app'

test.describe('filter: datetime range', () => {
  test.beforeEach(async ({ page }) => {
    await installMocks(page)
    await setupEditView(page)
  })

  test('apply filter without editing dates selects the default window', async ({
    page,
  }) => {
    await openOp(page, 'datetimeRange')
    await page.getByRole('button', { name: /apply filter/i }).click()
    await waitForSelection(page, 1)

    const row = page
      .locator('[data-testid^="history-item-"]')
      .filter({ hasText: 'Datetime Range' })
    await expect(row).toBeVisible()
  })
})
