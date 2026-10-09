/**
 * Shift datetimes edit: offsets selected timestamps by a given
 * amount + TimeUnit. The op runs a compound delete+add pipeline
 * internally, but from the UI we just see a single SHIFT_DATETIMES
 * row in edit history. Month and year shifts follow the chosen time
 * zone's calendar, which the step saves.
 */

import { expect, test } from '@playwright/test'
import { installMocks } from './support/mocks'
import { openOp, setupEditView } from './support/app'
import { expectHistoryContains, selectAllPoints } from './support/ops'

test.use({ timezoneId: 'Asia/Tokyo' })

test.describe('edit: shift datetimes', () => {
  test.beforeEach(async ({ page }) => {
    await installMocks(page, { qcHistories: true })
    await setupEditView(page)
    await selectAllPoints(page)
  })

  test('shifts the selection by 1 hour and logs history', async ({ page }) => {
    await openOp(page, 'shiftDatetimes')
    await page.getByLabel('Amount').fill('1')
    await page.getByRole('button', { name: /^shift$/i }).click()
    await expectHistoryContains(page, 'Shift Datetimes')
  })

  test('a month shift saves the time zone it follows', async ({ page }) => {
    await openOp(page, 'shiftDatetimes')
    await page.getByTestId('shift-unit').click()
    await page.getByRole('option', { name: 'MONTH', exact: true }).click()

    const note = page.getByTestId('shift-calendar-note')
    const shift = page.getByRole('button', { name: /^shift$/i })
    await page.getByLabel('Amount').fill('0.5')
    await expect(note).toHaveText('Months and years shift by whole numbers.')
    await expect(shift).toBeDisabled()

    await page.getByLabel('Amount').fill('1')
    await expect(note).toContainText('Asia/Tokyo')
    await shift.click()
    await expectHistoryContains(page, 'Shift Datetimes')

    const row = page
      .locator('[data-testid^="history-item-"]')
      .filter({ hasText: 'Shift Datetimes' })
    await row.getByRole('button', { name: 'Expand arguments', exact: true }).click()
    await expect(row.getByText('Asia/Tokyo', { exact: true })).toBeVisible()
  })
})
