/**
 * Tooltip-toggle "hidden" notice + inline threshold editor.
 *
 *   1. Manually toggling tooltips off surfaces the "Tooltips hidden /
 *      X / Y pts" notice next to the toggle.
 *   2. The pencil button next to the threshold opens a popover with
 *      the current limit pre-filled.
 *   3. The popover buffers the edit — typing alone doesn't change the
 *      displayed threshold; only Apply (or Enter) commits.
 *   4. Closing the popover without applying discards the in-progress
 *      edit; the displayed threshold stays put.
 *   5. Apply is disabled while the buffered value is below the 100-pt
 *      floor.
 */

import { expect, test, type Page } from '@playwright/test'
import { installMocks } from './support/mocks'
import { setupEditView } from './support/app'

/**
 * Pull the threshold number out of the notice text. The notice
 * renders as "Tooltips hidden{count} / {threshold} pts" with locale-
 * formatted numbers — strip the comma group separators before
 * parsing.
 */
async function readDisplayedThreshold(page: Page): Promise<number> {
  const noticeText = await page
    .getByTestId('tooltips-notice')
    .innerText()
  const match = noticeText.match(/\/\s*([\d,]+)\s*pts/)
  if (!match) throw new Error(`Could not parse threshold from "${noticeText}"`)
  return Number(match[1].replace(/,/g, ''))
}

test.describe('tooltip-threshold notice + popover', () => {
  test.beforeEach(async ({ page }) => {
    await installMocks(page)
    await setupEditView(page)
    // Make sure tooltips are currently on so the toggle goes off → on
    // → off transitions deterministically. The toggle is enabled
    // because the mocked fixture stays well under the 10k threshold.
    await expect(page.getByTestId('tooltips-toggle-btn')).toBeEnabled()
  })

  test('manually disabling tooltips reveals the notice with the current threshold', async ({
    page,
  }) => {
    await expect(page.getByTestId('tooltips-notice')).toHaveCount(0)

    await page.getByTestId('tooltips-toggle-btn').click()

    const notice = page.getByTestId('tooltips-notice')
    await expect(notice).toBeVisible()
    await expect(notice).toContainText('Tooltips hidden')
    // Default threshold is 10,000 pts; locale-formatted in the UI.
    await expect(notice).toContainText('10,000 pts')
  })

  test('Apply commits the new threshold, Enter does the same, and the popover discards on cancel', async ({
    page,
  }) => {
    await page.getByTestId('tooltips-toggle-btn').click()
    expect(await readDisplayedThreshold(page)).toBe(10_000)

    // --- Apply path -------------------------------------------------
    await page.getByTestId('threshold-edit-btn').click()
    const input = page.getByTestId('threshold-input').locator('input')
    await expect(input).toBeVisible()
    await input.fill('25000')

    // Buffered: nothing has changed in the notice yet.
    expect(await readDisplayedThreshold(page)).toBe(10_000)

    await page.getByTestId('threshold-apply-btn').click()
    // Popover closes and the new value lands in the notice.
    await expect(page.getByTestId('threshold-input')).toHaveCount(0)
    await expect.poll(() => readDisplayedThreshold(page)).toBe(25_000)

    // --- Cancel path -----------------------------------------------
    await page.getByTestId('threshold-edit-btn').click()
    await page.getByTestId('threshold-input').locator('input').fill('99999')
    // Click outside the menu to dismiss it without committing.
    await page.keyboard.press('Escape')
    await expect(page.getByTestId('threshold-input')).toHaveCount(0)
    expect(await readDisplayedThreshold(page)).toBe(25_000)

    // --- Enter path -------------------------------------------------
    await page.getByTestId('threshold-edit-btn').click()
    const enterInput = page.getByTestId('threshold-input').locator('input')
    await enterInput.fill('5000')
    await enterInput.press('Enter')
    await expect(page.getByTestId('threshold-input')).toHaveCount(0)
    await expect.poll(() => readDisplayedThreshold(page)).toBe(5_000)
  })

  test('Apply is disabled while the buffered value is below the 100-pt floor', async ({
    page,
  }) => {
    await page.getByTestId('tooltips-toggle-btn').click()
    await page.getByTestId('threshold-edit-btn').click()

    const input = page.getByTestId('threshold-input').locator('input')
    const apply = page.getByTestId('threshold-apply-btn')

    await input.fill('50')
    await expect(apply).toBeDisabled()

    await input.fill('100')
    await expect(apply).toBeEnabled()

    await input.fill('')
    await expect(apply).toBeDisabled()
  })
})
