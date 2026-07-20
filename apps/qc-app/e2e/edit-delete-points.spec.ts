/**
 * Delete-points edit: removes the selected indexes from the series.
 * The confirmation lives inline inside the panel (no separate dialog),
 * so one Delete click fires the op.
 */

import { test } from '@playwright/test'
import { installMocks } from './support/mocks'
import { openOp, setupEditView } from './support/app'
import { expectHistoryContains, selectAllPoints } from './support/ops'

test.describe('edit: delete points', () => {
  test.beforeEach(async ({ page }) => {
    await installMocks(page)
    await setupEditView(page)
    await selectAllPoints(page)
  })

  test('dispatches DELETE_POINTS for the current selection', async ({ page }) => {
    await openOp(page, 'deletePoints')
    await page.getByRole('button', { name: /^delete$/i }).click()
    await expectHistoryContains(page, 'Delete Points')
  })
})
