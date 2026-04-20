/**
 * Edit history toolbar:
 *   - Undo (toolbar + Ctrl+Z) pops the trailing edit and repopulates
 *     the redoStack; Redo re-applies it.
 *   - Expand chevron on a history row opens the Arguments panel.
 *   - "Reload from this step" reloads to a specific history index.
 *
 * We exercise the flow end-to-end: one filter + one edit, then undo /
 * redo the edit and check the row count.
 */

import { expect, test } from '@playwright/test'
import { installMocks } from './support/mocks'
import { openOp, setupEditView } from './support/app'
import { expectHistoryContains, selectAllPoints } from './support/ops'

test.describe('edit history toolbar', () => {
  test.beforeEach(async ({ page }) => {
    await installMocks(page)
    await setupEditView(page)
    await selectAllPoints(page)
    await openOp(page, 'changeValues')
    await page.getByLabel('Value').fill('1')
    await page.getByRole('button', { name: 'Apply' }).click()
    await expectHistoryContains(page, 'Change Values')
  })

  test('toolbar undo / redo buttons round-trip the trailing edit', async ({
    page,
  }) => {
    // Wait for the value-threshold + change-values rows (2 entries).
    await expect(
      page.locator('[data-testid^="history-item-"]')
    ).toHaveCount(2)

    await page.getByTestId('history-undo-btn').click()
    // After undo only the filter row remains.
    await expect(
      page.locator('[data-testid^="history-item-"]')
    ).toHaveCount(1)

    await page.getByTestId('history-redo-btn').click()
    // Redo reinstates the trailing edit.
    await expect(
      page.locator('[data-testid^="history-item-"]')
    ).toHaveCount(2)
  })

  test('expand chevron reveals the Arguments panel for a history row', async ({
    page,
  }) => {
    const row = page.getByTestId('history-item-1')
    await row.getByRole('button', { name: /expand arguments/i }).click()
    await expect(row.getByText('Arguments')).toBeVisible()
  })

  test('per-item undo button on the trailing entry rolls it back', async ({
    page,
  }) => {
    // Trailing row is index 1 (the CHANGE_VALUES entry).
    await page.getByTestId('history-undo-1').click()
    await expect(
      page.locator('[data-testid^="history-item-"]')
    ).toHaveCount(1)
  })
})
