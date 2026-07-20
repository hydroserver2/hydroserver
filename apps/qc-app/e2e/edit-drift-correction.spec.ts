/**
 * Drift-correction edit: applies a linear drift over each group of
 * consecutive selected indexes. The group count is derived from
 * `selectedData`, which our `selectAllPoints()` preamble fills with
 * one big contiguous block → exactly one group.
 */

import { expect, test } from '@playwright/test'
import { installMocks } from './support/mocks'
import { openOp, setupEditView } from './support/app'
import { expectHistoryContains, selectAllPoints } from './support/ops'

test.describe('edit: drift correction', () => {
  test.beforeEach(async ({ page }) => {
    await installMocks(page)
    await setupEditView(page)
    await selectAllPoints(page)
  })

  test('applies drift correction over a single selected group', async ({
    page,
  }) => {
    await openOp(page, 'driftCorrection')
    // Header summary ("N consecutive group") confirms the selection
    // made it into the panel. Without it the Apply button is disabled.
    await expect(
      page.getByText(/\d+ consecutive group/i)
    ).toBeVisible({ timeout: 10_000 })

    // Drift amount field is the first number input in the panel.
    const drift = page
      .getByTestId('operation-panel-driftCorrection')
      .locator('input[type="number"]')
      .first()
    await drift.fill('1')
    await page.getByRole('button', { name: 'Apply' }).click()
    await expectHistoryContains(page, 'Drift Correction')
  })
})
