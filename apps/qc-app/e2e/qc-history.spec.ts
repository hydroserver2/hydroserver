/**
 * QC History — round-trip e2e.
 *
 * Apply two operations (a value-threshold filter + a delete edit
 * that consumes its selection), use the EditHistory header's
 * Save button to download the QC history, then load that same file
 * back via the Load button and assert the history matches.
 *
 * The save side is exercised against a Playwright-wired download
 * promise; the load side feeds the captured payload back through
 * the hidden file input by way of `setInputFiles`.
 */

import { expect, test } from '@playwright/test'
import { readFile } from 'node:fs/promises'
import { installMocks } from './support/mocks'
import { openOp, setupEditView } from './support/app'
import { expectHistoryContains, selectAllPoints } from './support/ops'

test.describe('QC history: save / load round-trip', () => {
  test.beforeEach(async ({ page }) => {
    await installMocks(page)
    await setupEditView(page)
  })

  test('exports a QC history and re-applies it through the Load button', async ({
    page,
  }) => {
    // --- Author a couple of operations ---------------------------
    // First a filter that selects a useful subset of the fixture
    // sine wave (y > 0 hits all points). selectAllPoints() does
    // exactly this and waits for the selection store to populate.
    await selectAllPoints(page)
    // Then an edit that consumes the preceding SELECTION.
    await openOp(page, 'deletePoints')
    await page.getByRole('button', { name: /^delete$/i }).click()

    // History should now have the filter + edit pair (the
    // VALUE_THRESHOLD filter, the implicit SELECTION it produced,
    // and the DELETE_POINTS edit — selection-coupled ops keep the
    // SELECTION between them).
    await expectHistoryContains(page, 'Delete Points')
    const beforeRows = page.locator('[data-testid^="history-item-"]')
    const beforeCount = await beforeRows.count()
    expect(beforeCount).toBeGreaterThanOrEqual(2)

    // Snapshot just the method-name spans (`.edit-history__method`).
    // Pulling whole-row text would also capture the duration and
    // execution-mode chips, which legitimately differ across the
    // round-trip (the loaded run remeasures and re-tags them).
    const beforeMethodLabels = await beforeRows
      .locator('.edit-history__method')
      .evaluateAll((spans) => spans.map((s) => s.textContent?.trim() ?? ''))

    // --- Save: trigger the Save button and capture the download --
    const saveBtn = page.getByTestId('history-save-btn')
    await expect(saveBtn).toBeEnabled()
    const downloadPromise = page.waitForEvent('download')
    await saveBtn.click()
    const download = await downloadPromise
    const path = await download.path()
    expect(path).toBeTruthy()
    const buf = await readFile(path!)
    const historyText = buf.toString('utf-8')
    const history = JSON.parse(historyText)

    expect(history.version).toBe('1')
    expect(history.window).toBeDefined()
    expect(typeof history.window.startDate).toBe('string')
    expect(typeof history.window.endDate).toBe('string')
    expect(Array.isArray(history.operations)).toBe(true)
    expect(history.operations.length).toBe(beforeCount)

    // --- Reset history before loading ----------------------------
    // Discard via the Reload button on the baseline row, which
    // clears history in-place (preserving the editHistory ref).
    // Easier: re-enter the page is overkill; just undo back to 0.
    while (
      await page.getByTestId('history-undo-btn').isEnabled().catch(() => false)
    ) {
      await page.getByTestId('history-undo-btn').click()
      // Brief settle so the undo's redraw + selection sync fire.
      await page.waitForTimeout(150)
    }
    await expect(
      page.locator('[data-testid^="history-item-"]')
    ).toHaveCount(0)

    // --- Load: feed the captured QC history through the hidden input
    const fileInput = page.locator('input[type="file"][accept*="json"]')
    await fileInput.setInputFiles({
      name: 'round-trip.json',
      mimeType: 'application/json',
      buffer: buf,
    })

    // The composable does the reload + dispatch; wait for the row
    // count to repopulate.
    await expect(
      page.locator('[data-testid^="history-item-"]')
    ).toHaveCount(beforeCount, { timeout: 10_000 })

    // Compare method-label arrays directly.
    const afterRows = page.locator('[data-testid^="history-item-"]')
    const afterMethodLabels = await afterRows
      .locator('.edit-history__method')
      .evaluateAll((spans) =>
        spans.map((s) => s.textContent?.trim() ?? '')
      )
    expect(afterMethodLabels).toEqual(beforeMethodLabels)
  })
})
