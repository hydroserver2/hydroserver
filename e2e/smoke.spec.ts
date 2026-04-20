/**
 * Minimal smoke spec for the mocked-backend harness. Exists purely to
 * verify that `installMocks()` serves enough for the app to render
 * Home → plot → Edit view without talking to a real HydroServer.
 * Every feature-specific spec leans on the same preamble.
 */

import { expect, test } from '@playwright/test'
import { installMocks } from './support/mocks'
import { setupEditView } from './support/app'

test.describe('smoke (mocked backend)', () => {
  test.beforeEach(async ({ page }) => {
    await installMocks(page)
  })

  test('boots into edit view without live network', async ({ page }) => {
    await setupEditView(page)
    await expect(page.getByTestId('op-valueThreshold')).toBeVisible()
  })
})
