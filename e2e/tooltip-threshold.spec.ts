/**
 * Data-points combobox: mode menu + threshold editor.
 *
 *   1. Default (auto) mode renders the inline "Data points / X / Y pts"
 *      notice next to the combobox; the toggle button is disabled
 *      because the threshold drives the on/off state.
 *   2. Switching to "Manual toggle" via the caret menu hides the
 *      notice and enables the icon button — clicking the icon flips
 *      data-points hover on/off.
 *   3. Back in auto mode the pencil button next to the threshold opens
 *      a popover with the current limit pre-filled.
 *   4. The popover buffers the edit — typing alone doesn't change the
 *      displayed threshold; only Apply (or Enter) commits.
 *   5. Closing the popover without applying discards the in-progress
 *      edit; the displayed threshold stays put.
 *   6. Apply is disabled while the buffered value is below the 100-pt
 *      floor.
 */

import { expect, test, type Page } from '@playwright/test'
import { installMocks } from './support/mocks'
import { setupEditView } from './support/app'

/**
 * Pull the threshold number out of the notice text. The notice
 * renders as "Data points{count} / {threshold} pts" with locale-
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

/** Open the mode menu, pick an option, wait for the menu to close. */
async function pickMode(page: Page, mode: 'manual' | 'auto') {
  await page.getByTestId('tooltips-mode-btn').click()
  await page.getByTestId(`tooltips-mode-${mode}`).click()
  await expect(page.getByTestId('tooltips-mode-menu')).toHaveCount(0)
}

test.describe('data-points combobox', () => {
  test.beforeEach(async ({ page }) => {
    await installMocks(page)
    await setupEditView(page)
    // Reset the persisted preference so each test starts in auto mode
    // — the store persists `tooltipsMode` so a leaked manual setting
    // from a sibling test would otherwise hide the notice.
    await page.evaluate(() =>
      localStorage.removeItem('qc.plot.tooltipsMaxDataPoints')
    )
    await page.reload()
    // Wait for the combobox to mount before each test acts on it.
    await expect(page.getByTestId('tooltips-toggle-btn')).toBeVisible()
  })

  test('auto mode (default) shows the notice and disables the toggle', async ({
    page,
  }) => {
    const toggle = page.getByTestId('tooltips-toggle-btn')
    const notice = page.getByTestId('tooltips-notice')

    await expect(toggle).toBeDisabled()
    await expect(notice).toBeVisible()
    await expect(notice).toContainText('Data points')
    // Default threshold is 10,000 pts; locale-formatted in the UI.
    await expect(notice).toContainText('10,000 pts')
  })

  test('manual mode hides the notice and enables the toggle; the icon flips on/off', async ({
    page,
  }) => {
    await pickMode(page, 'manual')

    const toggle = page.getByTestId('tooltips-toggle-btn')
    await expect(toggle).toBeEnabled()
    await expect(page.getByTestId('tooltips-notice')).toHaveCount(0)

    // Manual mode starts at "on" by default — flip it off and back on.
    await expect(toggle).toHaveAttribute('aria-pressed', 'true')
    await toggle.click()
    await expect(toggle).toHaveAttribute('aria-pressed', 'false')
    await toggle.click()
    await expect(toggle).toHaveAttribute('aria-pressed', 'true')
  })

  test('switching back to auto restores the notice and disables the toggle', async ({
    page,
  }) => {
    await pickMode(page, 'manual')
    await expect(page.getByTestId('tooltips-notice')).toHaveCount(0)

    await pickMode(page, 'auto')
    await expect(page.getByTestId('tooltips-notice')).toBeVisible()
    await expect(page.getByTestId('tooltips-toggle-btn')).toBeDisabled()
  })

  test('Apply commits the new threshold, Enter does the same, and the popover discards on cancel', async ({
    page,
  }) => {
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
