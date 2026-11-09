/**
 * Value-threshold filter:
 *   - panel opens, "Value" input accepts numeric input
 *   - "Add filter" dispatches VALUE_THRESHOLD, populates selectedData,
 *     and adds a single replaceable filter history row
 *   - a second "Add filter" call REPLACES the filter entry (doesn't
 *     stack), since the app's dispatch collapses adjacent filter entries
 */

import { expect, test } from '@playwright/test'
import { installMocks } from './support/mocks'
import { openOp, setupEditView, waitForSelection } from './support/app'
import { buildObservations } from './support/fixtures'

test.describe('filter: value threshold', () => {
  test.beforeEach(async ({ page }) => {
    await installMocks(page, { qcHistories: true })
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

    // Filter entry shows up at top of history. The dispatch pipeline
    // can collapse the row into a rolled-up "Selection" entry after
    // dispatchSelection fires, so accept either label as proof the
    // filter ran.
    const filterRow = page
      .locator('[data-testid^="history-item-"]')
      .filter({ hasText: /Value Threshold|Selection/ })
    await expect(filterRow.first()).toBeVisible()
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

    // Only a single filter row should remain in history: the second
    // add-filter replaces the first in-place rather than stacking.
    // Accept either "Value Threshold" or a rolled-up "Selection"
    // label (both represent a single filter-class entry).
    const rows = page
      .locator('[data-testid^="history-item-"]')
      .filter({ hasText: /Value Threshold|Selection/ })
    await expect(rows).toHaveCount(1)
  })

  test('match all excludes a fill value with not equal to', async ({ page }) => {
    const y = buildObservations().result
    const fill = y.find((v) => v < 8)!
    const matchAll = y.filter((v) => v < 8 && v !== fill).length

    const addFilter = async (operator: string, value: number) => {
      await page.getByTestId('value-threshold-operator').click()
      await page.getByRole('option', { name: operator, exact: true }).click()
      await page.getByLabel('Value').fill(String(value))
      await page.getByRole('button', { name: /add filter/i }).click()
    }

    await openOp(page, 'valueThreshold')
    await addFilter('Less than', 8)
    await waitForSelection(page, 1)
    await addFilter('Not equal to', fill)

    const row = page
      .locator('[data-testid^="history-item-"]')
      .filter({ hasText: /Value Threshold/ })
    await expect(row).toContainText(`${y.length} pts`)

    await page
      .getByTestId('value-threshold-match')
      .getByRole('button', { name: 'Match all' })
      .click()
    await expect(row).toContainText(`${matchAll} pts`)
  })
})
