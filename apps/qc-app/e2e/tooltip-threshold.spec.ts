/**
 * Data-points combobox: mode menu + threshold editor.
 *
 *   1. Default (auto) mode renders a live `{visible}/{threshold}`
 *      counter in place of the toggle button. The toggle button is
 *      hidden because the threshold drives the on/off state.
 *   2. Switching to "Manual toggle" via the caret menu hides the
 *      counter and renders the icon toggle button — clicking it
 *      flips data-points hover on/off.
 *   3. The mode menu carries the threshold form when auto is active:
 *      typing buffers, Apply / Enter commit, Escape (which closes
 *      the menu) discards the in-progress edit.
 *   4. Apply is disabled while the buffered value is below the 100-pt
 *      floor.
 */

import { expect, test, type Page } from '@playwright/test'
import { installMocks } from './support/mocks'
import { setupEditView } from './support/app'

/**
 * Pull the threshold number out of the auto-mode counter text. The
 * counter renders as "{count}/{threshold}" with locale-formatted
 * numbers — strip the comma group separators before parsing.
 */
async function readDisplayedThreshold(page: Page): Promise<number> {
  const counterText = await page
    .getByTestId('tooltips-counter')
    .innerText()
  const match = counterText.match(/\/\s*([\d,]+)/)
  if (!match) throw new Error(`Could not parse threshold from "${counterText}"`)
  return Number(match[1].replace(/,/g, ''))
}

/**
 * Open the mode menu, pick an option, then dismiss the menu so the
 * underlying toolbar is interactable again. The v-menu uses
 * `close-on-content-click="false"` (so the threshold form stays open
 * during edits), which means a mode-option click does NOT auto-close
 * the menu — Escape does that reliably regardless of which mode was
 * picked.
 */
async function pickMode(page: Page, mode: 'manual' | 'auto') {
  await page.getByTestId('tooltips-mode-btn').click()
  await page.getByTestId(`tooltips-mode-${mode}`).click()
  await page.keyboard.press('Escape')
  await expect(page.getByTestId('tooltips-mode-menu')).toHaveCount(0)
}

/** Open the mode menu (where the threshold form lives in auto mode). */
async function openModeMenu(page: Page) {
  await page.getByTestId('tooltips-mode-btn').click()
  await expect(page.getByTestId('tooltips-mode-menu')).toBeVisible()
}

test.describe('data-points combobox', () => {
  // Each scenario takes ~18–20 s serially on Firefox — boot, plot,
  // setup, several menu open/close cycles, and a page.reload() in
  // beforeEach. With Playwright's default `workers: 2` cap, two of
  // these scenarios contending for the shared dev server can each
  // run 30–40 s, blowing the default 30 s per-test budget. Bump
  // the budget here rather than serializing the file so the suite
  // stays parallel-friendly.
  test.setTimeout(60_000)

  test.beforeEach(async ({ page }) => {
    await installMocks(page)
    await setupEditView(page)
    // Reset the persisted preference bag so each test starts in auto
    // mode at the default threshold. The store persists `tooltipsMode`,
    // `tooltipsMaxDataPoints`, and `tooltipsManualEnabled` under a
    // single key — clearing it resets all three.
    await page.evaluate(() =>
      localStorage.removeItem('qc.plot.tooltipsMaxDataPoints')
    )
    await page.reload()
    // Wait for the combobox to mount before each test acts on it. In
    // the default (auto) mode the counter cell is the visible anchor;
    // the toggle button only renders in manual mode.
    await expect(page.getByTestId('tooltips-counter')).toBeVisible()
  })

  test('auto mode (default) shows the live counter and hides the toggle button', async ({
    page,
  }) => {
    const counter = page.getByTestId('tooltips-counter')
    await expect(counter).toBeVisible()
    // Default threshold is 10,000 pts; locale-formatted in the UI.
    await expect(counter).toContainText('10,000')
    await expect(page.getByTestId('tooltips-toggle-btn')).toHaveCount(0)
  })

  test('manual mode hides the counter and enables the toggle; the icon flips on/off', async ({
    page,
  }) => {
    await pickMode(page, 'manual')

    const toggle = page.getByTestId('tooltips-toggle-btn')
    await expect(toggle).toBeVisible()
    await expect(toggle).toBeEnabled()
    await expect(page.getByTestId('tooltips-counter')).toHaveCount(0)

    // Manual mode starts at "on" by default — flip it off and back on.
    await expect(toggle).toHaveAttribute('aria-pressed', 'true')
    await toggle.click()
    await expect(toggle).toHaveAttribute('aria-pressed', 'false')
    await toggle.click()
    await expect(toggle).toHaveAttribute('aria-pressed', 'true')
  })

  test('switching back to auto restores the counter and hides the toggle', async ({
    page,
  }) => {
    await pickMode(page, 'manual')
    await expect(page.getByTestId('tooltips-toggle-btn')).toBeVisible()

    await pickMode(page, 'auto')
    await expect(page.getByTestId('tooltips-counter')).toBeVisible()
    await expect(page.getByTestId('tooltips-toggle-btn')).toHaveCount(0)
  })

  // Each commit path lives in its own test so a slow Firefox boot +
  // five menu open/close cycles + three counter polls can't cumulatively
  // blow the per-test 30 s budget. Splitting also localizes failures:
  // "Enter doesn't commit" no longer hides behind "Apply was slow."
  test('Apply commits the new threshold', async ({ page }) => {
    expect(await readDisplayedThreshold(page)).toBe(10_000)

    await openModeMenu(page)
    const input = page.getByTestId('threshold-input').locator('input')
    await expect(input).toBeVisible()
    await input.fill('25000')

    // applyThreshold sets `modeMenuOpen.value = false` on success, so
    // the menu unmounts itself; the counter then reads the committed
    // value once the menu is out of the way.
    await page.getByTestId('threshold-apply-btn').click()
    await expect(page.getByTestId('tooltips-mode-menu')).toHaveCount(0)
    await expect.poll(() => readDisplayedThreshold(page)).toBe(25_000)
  })

  test('Enter on the threshold field commits via the keyup.enter handler', async ({ page }) => {
    expect(await readDisplayedThreshold(page)).toBe(10_000)

    await openModeMenu(page)
    const input = page.getByTestId('threshold-input').locator('input')
    await input.fill('5000')
    await input.press('Enter')
    await expect(page.getByTestId('tooltips-mode-menu')).toHaveCount(0)
    await expect.poll(() => readDisplayedThreshold(page)).toBe(5_000)
  })

  test('Escape discards an in-progress edit without committing', async ({ page }) => {
    expect(await readDisplayedThreshold(page)).toBe(10_000)

    await openModeMenu(page)
    await page.getByTestId('threshold-input').locator('input').fill('99999')
    await page.keyboard.press('Escape')
    await expect(page.getByTestId('tooltips-mode-menu')).toHaveCount(0)
    expect(await readDisplayedThreshold(page)).toBe(10_000)
  })

  test('Apply is disabled while the buffered value is below the 100-pt floor', async ({
    page,
  }) => {
    await openModeMenu(page)

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
