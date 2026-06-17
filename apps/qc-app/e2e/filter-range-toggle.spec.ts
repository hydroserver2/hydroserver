/**
 * Filter-range toggle: a "Date range" section inside the operation
 * details body lets the user opt into restricting a filter operation
 * to a datetime window. Off by default → empty state with an "Enable
 * date range" button. On → `FilterRangePanel` mounts and an X icon
 * in the section head disables it again. The whole section is
 * suppressed for filter operations that bring their own picker
 * (`datetimeRange`).
 */

import { expect, test } from '@playwright/test'
import { installMocks } from './support/mocks'
import { openOp, setupEditView } from './support/app'

const dateRangeSection = '.operation-panel__section'
const enableBtn = '.operation-panel__section-empty .v-btn'
const disableBtn = '.operation-panel__section-head .v-btn'

test.describe('filter range toggle', () => {
  test.beforeEach(async ({ page }) => {
    await installMocks(page)
    await setupEditView(page)
  })

  test('section only appears once a filter op is staged', async ({ page }) => {
    // No operation staged → no section anywhere.
    await expect(page.locator(dateRangeSection)).toHaveCount(0)
    await expect(page.locator('.filter-range-panel')).toHaveCount(0)

    // Open Persistence — section appears in the empty state by default.
    await openOp(page, 'persistence')
    await expect(page.locator(enableBtn)).toBeVisible()
    await expect(page.locator('.filter-range-panel')).toHaveCount(0)

    // Enable — panel mounts and X icon replaces the empty state.
    await page.locator(enableBtn).click()
    await expect(page.locator('.filter-range-panel')).toBeVisible()
    await expect(page.locator(disableBtn)).toBeVisible()
  })

  test('date-range section is suppressed for the datetime-range operation', async ({
    page,
  }) => {
    await openOp(page, 'persistence')
    await page.locator(enableBtn).click()
    await expect(page.locator('.filter-range-panel')).toBeVisible()

    // Switch to datetime-range — that op brings its own picker, so the
    // shared section and panel both go away.
    await openOp(page, 'datetimeRange')
    // Only the operation section remains, not the date-range section.
    await expect(page.locator('.operation-panel__section--op')).toHaveCount(1)
    await expect(page.locator(enableBtn)).toHaveCount(0)
    await expect(page.locator(disableBtn)).toHaveCount(0)
    await expect(page.locator('.filter-range-panel')).toHaveCount(0)
  })

  test('the X icon collapses the panel back to the empty state', async ({
    page,
  }) => {
    await openOp(page, 'persistence')
    await page.locator(enableBtn).click()
    await expect(page.locator('.filter-range-panel')).toBeVisible()

    await page.locator(disableBtn).click()
    await expect(page.locator('.filter-range-panel')).toHaveCount(0)
    await expect(page.locator(enableBtn)).toBeVisible()
  })

  test('toggle state persists across reloads via the userInterface store', async ({
    page,
  }) => {
    await openOp(page, 'persistence')
    await page.locator(enableBtn).click()
    // pinia-plugin-persistedstate writes synchronously; verify the
    // payload landed before a reload so flakes don't masquerade as
    // missing-persistence regressions.
    await expect
      .poll(async () =>
        await page.evaluate(() =>
          localStorage.getItem('qc:userInterface:v1')
        )
      )
      .toContain('"filterRangeActive":true')

    await page.reload()
    // Re-prime: section only renders once the op is re-staged.
    await openOp(page, 'persistence')
    await expect(page.locator('.filter-range-panel')).toBeVisible()
    await expect(page.locator(disableBtn)).toBeVisible()
  })
})
