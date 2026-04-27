/**
 * Add-points edit: the panel starts with one empty row; filling in
 * a datetime + value and clicking "Add 1 point" dispatches
 * ADD_POINTS.
 */

import { expect, test } from '@playwright/test'
import { installMocks } from './support/mocks'
import { openOp, setupEditView } from './support/app'
import { expectHistoryContains } from './support/ops'

test.describe('edit: add points', () => {
  test.beforeEach(async ({ page }) => {
    await installMocks(page)
    await setupEditView(page)
  })

  test('adds a single point and logs history', async ({ page }) => {
    await openOp(page, 'addPoints')
    // The datetime is now driven by `DatePickerField` (separate
    // MM/DD/YYYY + HH:MM:SS inputs) rather than a single combined
    // textbox. The first row is autopopulated with `last datapoint
    // + intendedTimeSpacing`, so we just need to fill in a value
    // and click Apply.
    const panel = page.getByTestId('operation-panel-addPoints')
    await expect(
      panel.locator('input[placeholder="MM/DD/YYYY"]').first()
    ).toBeVisible()
    await panel.getByRole('spinbutton', { name: 'Value' }).fill('5')
    // Click the Apply button (label is dynamic: "Add 1 point").
    await panel.getByRole('button', { name: /^Add \d+ point/ }).click()
    await expectHistoryContains(page, 'Add Points')
    await expect(page.getByTestId('op-addPoints')).toBeVisible()
  })
})
