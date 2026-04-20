/**
 * Workspace picker + navigation rail flows:
 *   - fresh browser redirects to /workspaces
 *   - picking a workspace navigates to Home
 *   - the nav-rail workspace-switch button offers to revisit the picker
 *   - the edit rail item is disabled until a datastream is plotted
 *   - unsaved-edits dialog appears when leaving Edit with history
 */

import { expect, test } from '@playwright/test'
import { installMocks } from './support/mocks'
import {
  gotoHome,
  openOp,
  plotFirstDatastream,
  setupEditView,
} from './support/app'
import { selectAllPoints } from './support/ops'

test.describe('navigation', () => {
  test.beforeEach(async ({ page }) => {
    await installMocks(page)
  })

  test('fresh browser redirects to the workspace picker', async ({ page }) => {
    await page.goto('/')
    // Either still /workspaces, or the picker's select button is visible.
    await expect(
      page
        .getByRole('listitem')
        .filter({ hasText: 'E2E Test Workspace' })
        .getByRole('button', { name: /^Select$/ })
    ).toBeVisible({ timeout: 15_000 })
  })

  test('picking a workspace lands the user on Home', async ({ page }) => {
    await gotoHome(page)
    await expect(page.getByTestId('datastreams-table')).toBeVisible()
  })

  test('Edit rail item is disabled until a datastream is plotted', async ({
    page,
  }) => {
    await gotoHome(page)
    const editRail = page.getByTestId('nav-rail-item-edit')
    await expect(editRail).toHaveClass(/v-list-item--disabled/)
    await plotFirstDatastream(page)
    await expect(editRail).not.toHaveClass(/v-list-item--disabled/)
  })

  test('unsaved-edits dialog warns before navigating away from Edit', async ({
    page,
  }) => {
    await setupEditView(page)
    await selectAllPoints(page)
    await openOp(page, 'changeValues')
    await page.getByLabel('Value').fill('1')
    await page.getByRole('button', { name: 'Apply' }).click()

    // Click back to the select view via the nav-rail Select item.
    await page.getByTestId('nav-rail-item-select').click()
    await expect(page.getByText(/unsaved edits/i)).toBeVisible()
    await expect(
      page.getByRole('button', { name: /discard/i })
    ).toBeVisible()
  })
})
