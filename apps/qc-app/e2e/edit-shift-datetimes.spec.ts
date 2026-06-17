/**
 * Shift datetimes edit: offsets selected timestamps by a given
 * amount + TimeUnit. The op runs a compound delete+add pipeline
 * internally, but from the UI we just see a single SHIFT_DATETIMES
 * row in edit history.
 */

import { test } from '@playwright/test'
import { installMocks } from './support/mocks'
import { openOp, setupEditView } from './support/app'
import { expectHistoryContains, selectAllPoints } from './support/ops'

test.describe('edit: shift datetimes', () => {
  test.beforeEach(async ({ page }) => {
    await installMocks(page)
    await setupEditView(page)
    await selectAllPoints(page)
  })

  test('shifts the selection by 1 hour and logs history', async ({ page }) => {
    await openOp(page, 'shiftDatetimes')
    await page.getByLabel('Amount').fill('1')
    await page.getByRole('button', { name: /^shift$/i }).click()
    await expectHistoryContains(page, 'Shift Datetimes')
  })
})
