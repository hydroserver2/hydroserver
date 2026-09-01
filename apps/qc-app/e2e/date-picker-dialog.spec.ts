/**
 * The calendar dialog behind `DatePickerField` must open at the full
 * width of the Vuetify date picker. Dimension props on an overlay go
 * through `parseFloat`, so a rem-valued `max-width` collapses the
 * dialog into a thin strip.
 */

import { expect, test } from '@playwright/test'
import { installMocks } from './support/mocks'
import { openOp, setupEditView, waitForSelection } from './support/app'

test.describe('date picker dialog', () => {
  test('opens at the full width of the date picker', async ({ page }) => {
    await installMocks(page)
    await setupEditView(page)
    await openOp(page, 'datetimeRange')
    await waitForSelection(page, 1)

    await page.locator('.mdi-calendar-blank').first().click()

    const card = page.locator('.date-picker-card')
    await expect(card).toBeVisible()
    await expect(page.locator('.v-date-picker-month')).toBeVisible()

    // Polled: the dialog scales up on open, so the first measurement
    // lands mid-transition.
    await expect
      .poll(async () => (await card.boundingBox())?.width ?? 0)
      .toBeGreaterThanOrEqual(328)

    // The month grid is not clipped by a collapsed card.
    const cardBox = (await card.boundingBox())!
    const picker = (await page.locator('.v-date-picker').boundingBox())!
    expect(picker.width).toBeLessThanOrEqual(cardBox.width + 1)
  })
})
