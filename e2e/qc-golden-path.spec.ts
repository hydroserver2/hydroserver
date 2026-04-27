import { test, expect } from '@playwright/test'

declare global {
  interface Window {
    __vbwTestHooks?: {
      waitForSelectedData: (
        minLength?: number,
        timeoutMs?: number
      ) => Promise<number>
    }
  }
}

// Smoke spec covering the QC golden path against the live playground.hydroserver.org
// backend (Option A from RESEARCH.md). No page.route() mocks, no fixture JSON.
//
// Steps:
//   1. Navigate to app root — a fresh browser has no persisted workspace
//      selection, so the router's workspace guard redirects to /workspaces.
//   2. Select "Test Workspace #2" from the picker.
//   3. Wait for datastreams table (init-complete signal on Home).
//   4. Select the first datastream and wait for data-loading-indicator to hide.
//   5. Switch to Edit view via the navigation rail.
//   6. Open "Value thresholds", add a filter, close dialog.
//   7. Wait for selection to populate, open "Change values", commit edit.
//   8. Assert CHANGE_VALUES appears in EditHistory.
//   9. Click Save Changes, confirm, assert success snackbar.

// Live smoke — talks to playground.hydroserver.org. Opt in with
// `E2E_LIVE=1 npx playwright test qc-golden-path` so CI runs the fast
// mocked suite by default; the live smoke is for pre-release confidence.
test.describe('QC golden path (live)', () => {
  test.skip(
    !process.env.E2E_LIVE,
    'Set E2E_LIVE=1 to run the live-backend smoke'
  )

  test('qc golden path: filter, edit, submit', async ({ page }) => {
    // First-run Vite + createHydroServer + qc-utils calibration + observation
    // fetch can exceed the default 30s test timeout. 180s gives the whole
    // flow room to breathe on a cold dev server.
    test.setTimeout(180_000)

    // Step 1 & 2 — Navigate to app root. Fresh browser has no stored
    // workspace, so the guard redirects to /workspaces. Pick
    // "Test Workspace #2" (pinned because the datastream referenced
    // below lives there). The picker loads the workspace list
    // asynchronously; waiting for the SELECT button to be visible is
    // our "picker ready" signal.
    await page.goto('/')
    const pickButton = page
      .getByRole('listitem')
      .filter({ hasText: 'Test Workspace #2' })
      .getByRole('button', { name: /^Select$/ })
    await expect(pickButton).toBeVisible({ timeout: 60_000 })
    await pickButton.click()

    // Step 3 — Wait for datastreams table. App.vue's onMounted fetches
    // the workspace catalog; the table becomes visible once the fetch
    // settles.
    await expect(page.getByTestId('datastreams-table')).toBeVisible({
      timeout: 60_000,
    })

    // Step 4 — Select the first available datastream. The table is
    // virtualized (`v-data-table-virtual`), so rows outside the
    // initial viewport aren't in the DOM. We don't care which
    // datastream we pick — the filter/edit/submit flow is the same
    // for any — so target the first rendered `plot-checkbox-*` row
    // instead of pinning to a specific id. After checking, wait
    // for the data-loading-indicator to hide — observations have
    // finished loading into Plotly.
    const firstPlotButton = page.locator('[data-testid^="plot-checkbox-"]').first()
    await expect(firstPlotButton).toBeVisible({ timeout: 30_000 })
    await firstPlotButton.click()
    await page
      .getByTestId('data-loading-indicator')
      .waitFor({ state: 'hidden', timeout: 90_000 })

    // Step 5 — Switch to the Edit view. Edit rail item becomes enabled once
    // qcDatastream is set (happens when a datastream is plotted).
    await page.getByTestId('nav-rail-item-edit').click()
    await expect(page.getByText('Filter Data')).toBeVisible()

    // Step 6 — Open "Value thresholds" operation panel, add a filter.
    // Conservative value (0) chosen per plan 01-03 to ensure the threshold
    // selects at least some points against arbitrary live observations.
    // The drawer row carries both the title text and a per-op testid —
    // use the testid so we don't collide with the panel header that
    // renders the same title after the click.
    await page.getByTestId('op-valueThreshold').click()
    await expect(
      page.getByTestId('operation-panel-valueThreshold')
    ).toBeVisible()
    await page.getByLabel('Value').fill('0')
    await page.getByRole('button', { name: 'Add filter' }).click()
    // Panel dismissal isn't needed — selecting another drawer item
    // swaps the rendered operation in the shared OperationPanel.

    // Step 7 — Apply a "Change values" edit.
    // Wait for the ValueThreshold filter to populate selectedData via the
    // app-side test hook installed from main.ts. The hook registers a Pinia
    // `watch` on useDataVisStore().selectedData and resolves as soon as
    // length >= 1. This replaces the previous waitForTimeout + force-click
    await page.waitForFunction(
      () => typeof window.__vbwTestHooks?.waitForSelectedData === 'function',
      undefined,
      { timeout: 10_000 }
    )
    await page.evaluate(() =>
      window.__vbwTestHooks!.waitForSelectedData(1, 10_000).then(() => { })
    )
    await page.getByTestId('op-changeValues').click()

    // ChangeValues panel
    await page.getByLabel('Value').fill('1')
    await page.getByRole('button', { name: 'Apply' }).click()

    // Step 8 — Assert the edit landed in EditHistory. Filters now emit
    // their own history rows, so we can't pin to history-item-0; the
    // CHANGE_VALUES row lands after the ValueThreshold one. Find the
    // row by text instead. EditHistory formats ALL_CAPS_SNAKE as
    // Title Case, so we look for "Change Values".
    const changeRow = page
      .locator('[data-testid^="history-item-"]')
      .filter({ hasText: 'Change Values' })
    await expect(changeRow).toBeVisible({ timeout: 30_000 })

    // Dev-only sanity check: the calibration layer attached an
    // execution-mode chip ("inline" or "worker") to the history row.
    // This asserts the chip rendered without pinning its content —
    // either is a legitimate calibration outcome depending on the
    // device running the test.
    const modeChip = changeRow.locator('.edit-history__mode-chip')
    await expect(modeChip).toBeVisible()
    await expect(modeChip).toHaveText(/inline|worker/)

    // Step 9 — Save Changes → confirm → assert success snackbar.
    await page.getByTestId('exit-save-btn').click()
    await expect(page.getByText('Submit QC observations?')).toBeVisible()
    await page.getByRole('button', { name: 'Submit' }).click()
    // ⚠ REQUIRES LIVE VALIDATION: success snackbar text — confirmed against
    // Snackbar.success call sites but not yet observed in a live run.
    await expect(
      page.getByText('Quality-controlled observations submitted')
    ).toBeVisible({ timeout: 60_000 })
    // MH-17: after submit the store clears editHistory → history-item-0 must be gone.
    await expect(page.getByTestId('history-item-0')).toHaveCount(0, { timeout: 15_000 })
  })
})
