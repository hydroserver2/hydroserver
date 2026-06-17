/**
 * Interpolate edit: fills selected points with linearly-interpolated
 * values between the nearest non-selected anchors.
 */

import { test } from '@playwright/test'
import { installMocks } from './support/mocks'
import { openOp, setupEditView } from './support/app'
import { expectHistoryContains, selectAllPoints } from './support/ops'

test.describe('edit: interpolate', () => {
  test.beforeEach(async ({ page }) => {
    await installMocks(page)
    await setupEditView(page)
    await selectAllPoints(page)
  })

  test('dispatches INTERPOLATE and logs history', async ({ page }) => {
    await openOp(page, 'interpolate')
    await page.getByRole('button', { name: /^interpolate$/i }).click()
    await expectHistoryContains(page, 'Interpolate')
  })
})
