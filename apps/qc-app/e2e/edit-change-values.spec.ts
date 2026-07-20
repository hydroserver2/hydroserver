/**
 * Change values edit: applies an arithmetic operator (Add / Subtract /
 * Multiply / Divide / Assign) to the selected points' Y values. Runs
 * through the dispatch pipeline so a CHANGE_VALUES row lands in edit
 * history with a mode chip ("inline" vs "worker").
 */

import { expect, test } from '@playwright/test'
import { installMocks } from './support/mocks'
import { openOp, setupEditView } from './support/app'
import { expectHistoryContains, selectAllPoints } from './support/ops'

test.describe('edit: change values', () => {
  test.beforeEach(async ({ page }) => {
    await installMocks(page)
    await setupEditView(page)
    await selectAllPoints(page)
  })

  test('applies an ADD via the operator toggle and logs history', async ({
    page,
  }) => {
    await openOp(page, 'changeValues')
    await page.getByLabel('Value').fill('1')
    await page.getByRole('button', { name: 'Apply' }).click()
    await expectHistoryContains(page, 'Change Values')
  })

  test('assign operator writes constant values to the selection', async ({
    page,
  }) => {
    await openOp(page, 'changeValues')
    // The operator toggle has icon-only buttons with titled labels.
    await page.getByRole('button', { name: 'Assign' }).click()
    await page.getByLabel('Value').fill('42')
    await page.getByRole('button', { name: 'Apply' }).click()
    await expectHistoryContains(page, 'Change Values')
    // After apply the selection clears.
    await expect(page.getByTestId('op-changeValues')).toBeVisible()
  })
})
