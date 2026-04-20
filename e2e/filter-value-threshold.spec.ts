/**
 * Value-threshold filter:
 *   - panel opens, "Value" input accepts numeric input
 *   - "Add filter" dispatches VALUE_THRESHOLD, populates selectedData,
 *     and adds a single replaceable filter history row
 *   - a second "Add filter" call REPLACES the filter entry (doesn't
 *     stack) — the app's dispatch collapses adjacent filter entries
 */

import { expect, test } from '@playwright/test'
import { installMocks } from './support/mocks'
import { openOp, setupEditView, waitForSelection } from './support/app'

test.describe('filter: value threshold', () => {
  test.beforeEach(async ({ page }) => {
    await installMocks(page)
    await setupEditView(page)
  })

  test('adds a filter and populates the selection', async ({ page }) => {
    await openOp(page, 'valueThreshold')
    await page.getByLabel('Value').fill('8')
    await page.getByRole('button', { name: /add filter/i }).click()

    // The fixture observations are y = 10 + 5*sin(i/5) → all > 8 fails,
    // but default comparator is GT (= "greater than"), so the match
    // depends on operator selection. We just assert *some* selection
    // lands without pinning the exact count.
    await waitForSelection(page, 1)

    // Filter entry shows up at top of history.
    const filterRow = page
      .locator('[data-testid^="history-item-"]')
      .filter({ hasText: 'Value Threshold' })
    await expect(filterRow).toBeVisible()
  })

  test('second add-filter replaces the prior filter history entry', async ({
    page,
  }) => {
    await openOp(page, 'valueThreshold')
    await page.getByLabel('Value').fill('5')
    await page.getByRole('button', { name: /add filter/i }).click()
    await waitForSelection(page, 1)

    // Change value and add again.
    await page.getByLabel('Value').fill('9')
    await page.getByRole('button', { name: /add filter/i }).click()

    // Only a single VALUE_THRESHOLD row should remain in history.
    const rows = page
      .locator('[data-testid^="history-item-"]')
      .filter({ hasText: 'Value Threshold' })
    await expect(rows).toHaveCount(1)
  })
})
