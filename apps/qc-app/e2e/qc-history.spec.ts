/**
 * QC History: export e2e. Apply a filter and a delete that consumes its
 * selection, save the history from the EditHistory header, and check the
 * downloaded payload.
 */

import { expect, test } from '@playwright/test'
import { readFile } from 'node:fs/promises'
import { installMocks } from './support/mocks'
import { openOp, setupEditView } from './support/app'
import { expectHistoryContains, selectAllPoints } from './support/ops'

test.describe('QC history: export', () => {
  test.beforeEach(async ({ page }) => {
    await installMocks(page, { qcHistories: true })
    await setupEditView(page)
  })

  test('saves the history with its window and operations', async ({ page }) => {
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
    // and the DELETE_POINTS edit; selection-coupled ops keep the
    // SELECTION between them).
    await expectHistoryContains(page, 'Delete Points')
    const beforeRows = page.locator('[data-testid^="history-item-"]')
    const beforeCount = await beforeRows.count()
    expect(beforeCount).toBeGreaterThanOrEqual(2)

    // --- Save: trigger the Save button and capture the download --
    const saveBtn = page.getByTestId('history-save-btn')
    await expect(saveBtn).toBeEnabled()
    const downloadPromise = page.waitForEvent('download')
    await saveBtn.click()
    const download = await downloadPromise
    const path = await download.path()
    expect(path).toBeTruthy()
    const buf = await readFile(path!)
    const history = JSON.parse(buf.toString('utf-8'))

    expect(history.version).toBe('1')
    expect(history.window).toBeDefined()
    expect(typeof history.window.startDate).toBe('string')
    expect(typeof history.window.endDate).toBe('string')
    expect(Array.isArray(history.operations)).toBe(true)
    expect(history.operations.length).toBe(beforeCount)
  })
})
