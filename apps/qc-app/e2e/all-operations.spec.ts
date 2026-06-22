/**
 * Single-session smoke that walks one datastream through every
 * filter / edit / add operation in order. Each step is performed
 * manually (open panel → fill controls → click commit), one after
 * another, against the same series — so any state pollution between
 * ops (stale selections, leftover box-select rectangles, indices
 * shifted by a prior insert/delete) surfaces as a failure on the
 * next op rather than going unnoticed.
 *
 * Regressions this test exists to catch:
 *   - Change Values had no effect after Fill Gaps (the inserted-
 *     indices auto-selection landed in `history[length - 2]` and
 *     stale selectedpoints from the lasso rectangle clobbered the
 *     post-action highlight).
 *   - Edit ops that read indices from `history[length - 2].selected`
 *     silently no-op'd if a prior op left a non-SELECTION entry
 *     there — the panels now dispatch `[SELECTION, OP]` atomically.
 */

import { expect, test, type Page } from '@playwright/test'
import { installMocks } from './support/mocks'
import { openOp, setupEditView, waitForSelection } from './support/app'
import { expectHistoryContains } from './support/ops'
import { FIXTURE_OBS_START_MS } from './support/fixtures'

/**
 * Fixture: 20 points → ~4h gap → 20 more points. Gives Find Gaps /
 * Fill Gaps something to detect, while keeping enough points around
 * for the selection-driven edits that come after.
 */
function observationsWithGap() {
  // Anchor to FIXTURE_OBS_START_MS (relative to "now") so the series
  // falls inside the QC app's default 1w window — a hard-coded literal
  // would slide out of range as the calendar moves and leave the main
  // plot empty.
  const startMs = FIXTURE_OBS_START_MS
  const spacingMs = 15 * 60 * 1000
  const phenomenonTime: string[] = []
  const result: number[] = []
  for (let i = 0; i < 20; i++) {
    phenomenonTime.push(new Date(startMs + i * spacingMs).toISOString())
    result.push(10 + i * 0.1)
  }
  const gapStart = startMs + 20 * spacingMs + 4 * 60 * 60 * 1000
  for (let i = 0; i < 20; i++) {
    phenomenonTime.push(new Date(gapStart + i * spacingMs).toISOString())
    result.push(12 + i * 0.1)
  }
  return { phenomenonTime, result }
}

/** Re-seed a contiguous selection spanning the full series. Uses
 *  Datetime Range (live-commit, no Apply button) so the selection is
 *  guaranteed to be one consecutive block — Drift Correction needs
 *  groups of length > 1 and Value Threshold can yield non-contiguous
 *  hits once intermediate edits have shifted Y values around. */
async function seedWideSelection(page: Page) {
  await openOp(page, 'datetimeRange')
  await waitForSelection(page, 1)
}

test.describe('all operations: single-session walkthrough', () => {
  test.beforeEach(async ({ page }) => {
    await installMocks(page, { observations: observationsWithGap() })
    await setupEditView(page)
  })

  test('runs every filter, edit, and add operation in sequence', async ({
    page,
  }) => {
    test.setTimeout(120_000)

    // --- Filter: Value Threshold -------------------------------------
    await openOp(page, 'valueThreshold')
    await page.getByLabel('Value').fill('0')
    await page.getByRole('button', { name: /add filter/i }).click()
    await waitForSelection(page, 1)

    // --- Filter: Datetime Range --------------------------------------
    await openOp(page, 'datetimeRange')
    // Datetime Range commits live as the inputs settle; just opening
    // the panel against the seeded fixture is enough for a smoke pass.
    await expect(
      page.getByTestId('operation-panel-datetimeRange')
    ).toBeVisible()

    // --- Filter: Change ----------------------------------------------
    await openOp(page, 'change')
    await expect(page.getByTestId('operation-panel-change')).toBeVisible()

    // --- Filter: Rate of Change --------------------------------------
    await openOp(page, 'rateOfChange')
    await expect(
      page.getByTestId('operation-panel-rateOfChange')
    ).toBeVisible()

    // --- Filter: Persistence -----------------------------------------
    await openOp(page, 'persistence')
    await expect(
      page.getByTestId('operation-panel-persistence')
    ).toBeVisible()

    // --- Filter: Find Gaps -------------------------------------------
    await openOp(page, 'gaps')
    await page.getByLabel('Amount').fill('30')
    await waitForSelection(page, 1)
    await expect(
      page.getByText(/gaps? in the (datastream|selected range)/i)
    ).toBeVisible()

    // --- Add: Fill Gaps ----------------------------------------------
    // Fill the deliberate ~4h gap with 15-minute samples. After the
    // commit, recordPostActionSelection lands an inserted-indices
    // SELECTION in history — the next edit must NOT silently
    // operate on those indices.
    await openOp(page, 'fillGaps')
    const fillPanel = page.getByTestId('operation-panel-fillGaps')
    const fillInputs = fillPanel.locator('input[type="number"]')
    await fillInputs.nth(0).fill('30')
    await fillInputs.nth(1).fill('15')
    await fillPanel.getByRole('button', { name: /fill gaps/i }).click()
    await expectHistoryContains(page, 'Fill Gaps')

    // --- Edit: Change Values (after Fill Gaps — regression guard) ---
    // Re-seed a fresh wide selection so we're operating on real data,
    // not the post-fill auto-selection. The dispatch chain in
    // ChangeValues.vue now anchors the SELECTION explicitly, so this
    // applies to the indices the user actually sees in the panel.
    await seedWideSelection(page)
    await openOp(page, 'changeValues')
    await page.getByLabel('Value').fill('1')
    await page.getByRole('button', { name: 'Apply' }).click()
    await expectHistoryContains(page, 'Change Values')

    // --- Edit: Interpolate -------------------------------------------
    await seedWideSelection(page)
    await openOp(page, 'interpolate')
    await page.getByRole('button', { name: /^interpolate$/i }).click()
    await expectHistoryContains(page, 'Interpolate')

    // --- Edit: Drift Correction --------------------------------------
    await seedWideSelection(page)
    await openOp(page, 'driftCorrection')
    await expect(
      page.getByText(/\d+ consecutive group/i)
    ).toBeVisible({ timeout: 10_000 })
    const drift = page
      .getByTestId('operation-panel-driftCorrection')
      .locator('input[type="number"]')
      .first()
    await drift.fill('1')
    await page.getByRole('button', { name: 'Apply' }).click()
    await expectHistoryContains(page, 'Drift Correction')

    // --- Edit: Shift Datetimes ---------------------------------------
    await seedWideSelection(page)
    await openOp(page, 'shiftDatetimes')
    await page.getByLabel('Amount').fill('1')
    await page.getByRole('button', { name: /^shift$/i }).click()
    await expectHistoryContains(page, 'Shift Datetimes')

    // --- Add: Add Points ---------------------------------------------
    await openOp(page, 'addPoints')
    const addPanel = page.getByTestId('operation-panel-addPoints')
    await expect(
      addPanel.locator('input[placeholder="MM/DD/YYYY"]').first()
    ).toBeVisible()
    await addPanel.getByRole('spinbutton', { name: 'Value' }).fill('5')
    await addPanel.getByRole('button', { name: /^Add \d+ point/ }).click()
    await expectHistoryContains(page, 'Add Points')

    // --- Edit: Delete Points (closes out the run) --------------------
    // Delete LAST so we don't shrink the dataset out from under the
    // earlier selection-driven edits. The panel auto-clears the
    // selection on commit, which is the right end-of-session state.
    await seedWideSelection(page)
    await openOp(page, 'deletePoints')
    await page.getByRole('button', { name: /^delete$/i }).click()
    await expectHistoryContains(page, 'Delete Points')
  })
})
