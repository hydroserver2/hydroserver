/**
 * Filter-range toggle: a button on the "Filter Data" header in the
 * left drawer flips a shared range UI on/off. When on AND a filter
 * operation is staged (other than `datetimeRange`), a sidebar panel
 * appears above the operation details and every filter dispatch
 * picks up `[fromTs, toTs]` as the optional `range` argument.
 */

import { expect, test } from '@playwright/test'
import { installMocks } from './support/mocks'
import { openOp, setupEditView } from './support/app'

test.describe('filter range toggle', () => {
  test.beforeEach(async ({ page }) => {
    await installMocks(page)
    await setupEditView(page)
  })

  test('panel only appears when toggle is on AND an op is staged', async ({
    page,
  }) => {
    const toggle = page.locator('.edit-drawer__filter-range-btn')

    // Drawer toggle is "Off" out of the box.
    await expect(toggle).toHaveAttribute('aria-pressed', 'false')

    // Toggle on — but no operation is staged → panel stays hidden.
    await toggle.click()
    await expect(toggle).toHaveAttribute('aria-pressed', 'true')
    await expect(page.locator('.filter-range-panel')).toHaveCount(0)

    // Open Persistence — panel mounts.
    await openOp(page, 'persistence')
    await expect(page.locator('.filter-range-panel')).toBeVisible()
  })

  test('panel is suppressed for the datetime-range operation', async ({
    page,
  }) => {
    await page.locator('.edit-drawer__filter-range-btn').click()
    await openOp(page, 'persistence')
    await expect(page.locator('.filter-range-panel')).toBeVisible()

    // Switch to datetime-range — same toggle, but the op brings its
    // own picker so the shared panel hides to avoid the duplicate.
    await openOp(page, 'datetimeRange')
    await expect(page.locator('.filter-range-panel')).toHaveCount(0)
  })

  test('closing the panel via its X turns the drawer toggle Off', async ({
    page,
  }) => {
    const toggle = page.locator('.edit-drawer__filter-range-btn')
    await toggle.click()
    await openOp(page, 'persistence')

    const panel = page.locator('.filter-range-panel')
    await expect(panel).toBeVisible()
    // The header's leading close button collapses the shared state.
    await panel.locator('.filter-range-panel__header button').first().click()
    await expect(panel).toHaveCount(0)
    await expect(toggle).toHaveAttribute('aria-pressed', 'false')
  })

  test('toggle state persists across reloads via the userInterface store', async ({
    page,
  }) => {
    await page.locator('.edit-drawer__filter-range-btn').click()
    // pinia-plugin-persistedstate writes synchronously; verify the
    // payload landed before a reload so flakes don't masquerade as
    // missing-persistence regressions.
    await expect
      .poll(async () =>
        await page.evaluate(() =>
          localStorage.getItem('qc.userInterface.filterRangeActive')
        )
      )
      .toContain('"filterRangeActive":true')

    await page.reload()
    // Re-prime the edit view; the persisted toggle should still
    // come back On.
    const toggle = page.locator('.edit-drawer__filter-range-btn')
    await expect(toggle).toHaveAttribute('aria-pressed', 'true')
  })
})
