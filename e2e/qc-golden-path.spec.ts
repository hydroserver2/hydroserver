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
// Steps (see .vbw-planning/phases/01-e2e-playwright-setup/01-RESEARCH.md "Spec Sketch"):
//   1. Navigate to app root and wait for datastreams table (init-complete signal).
//   2. Select the first datastream and wait for data-loading-indicator to hide.
//   3. Switch to Edit view via the navigation rail.
//   4. Open "Value thresholds", add a filter, close dialog.
//   5. Wait for selection to populate, open "Change values", commit edit.
//   6. Assert CHANGE_VALUES appears in EditHistory.
//   7. Click Save Changes, confirm, assert success snackbar.

test.describe('QC golden path', () => {
  test('qc golden path: filter, edit, submit', async ({ page }) => {
    // First-run Vite + auto-login + qc-utils worker spin-up + observation
    // fetch can exceed the default 30s test timeout. 180s gives the whole
    // flow room to breathe on a cold dev server.
    test.setTimeout(180_000)

    // Step 1 — Navigate to app root. App.vue auto-initializes HydroServer
    // (login + fetch things/datastreams) — waiting for the datastreams table
    // to appear is our "isLoading === false" signal.
    await page.goto('/')
    await expect(page.getByTestId('datastreams-table')).toBeVisible({
      timeout: 60_000,
    })

    // Step 2 — Select the first datastream. The v-data-table-virtual renders
    // plot-checkbox-<id> per row; target the first one with an attribute
    // selector since the id is dynamic. After checking, wait for the
    // data-loading-indicator (v-progress-linear wrapped in v-if="isUpdating")
    // to hide — observations have finished loading into Plotly.
    // Pinned to Streamflow Datastream (~3,739 observations, Test Workspace #2, visible to auto-login user mauriel.ramirez@gmail.com). Backup: any of 11 Logan River at Mendon Road datastreams (~35,133 obs each).
    await page
      .getByTestId('plot-checkbox-0196d998-b358-7d7d-a836-69e72395a06b')
      .locator('input[type="checkbox"]')
      .check()
    await page
      .getByTestId('data-loading-indicator')
      .waitFor({ state: 'hidden', timeout: 90_000 })

    // Step 3 — Switch to the Edit view. Edit rail item becomes enabled once
    // qcDatastream is set (happens when a datastream is plotted).
    await page.getByTestId('nav-rail-item-edit').click()
    await expect(page.getByText('Filter points')).toBeVisible()

    // Step 4 — Open "Value thresholds" FilterPoints dialog, add a filter.
    // Conservative value (0) chosen per plan 01-03 to ensure the threshold
    // selects at least some points against arbitrary live observations.
    await page.getByText('Value thresholds').click()
    await expect(page.getByText('Filter by values')).toBeVisible()
    await page.getByLabel('Value').fill('0')
    await page.getByRole('button', { name: 'Add Filter' }).click()
    // Close the dialog — Escape is the most robust way to dismiss Vuetify
    // v-dialogs without relying on a specific Close button label.
    await page.keyboard.press('Escape')

    // Step 5 — Apply a "Change values" edit.
    // Wait for the ValueThreshold filter to populate selectedData via the
    // app-side test hook installed from main.ts. The hook registers a Pinia
    // `watch` on useDataVisStore().selectedData and resolves as soon as
    // length >= 1. This replaces the previous waitForTimeout + force-click
    // workaround (Phase 1 CARRY-01).
    await page.waitForFunction(
      () => typeof window.__vbwTestHooks?.waitForSelectedData === 'function',
      undefined,
      { timeout: 10_000 }
    )
    await page.evaluate(() =>
      window.__vbwTestHooks!.waitForSelectedData(1, 10_000).then(() => {})
    )
    await page.getByText('Change values').click()

    // ChangeValues dialog
    await page.getByLabel('Value').fill('1')
    await page.getByRole('button', { name: 'Change Values' }).click()

    // Step 6 — Assert the edit landed in EditHistory. history-item-0 is the
    // first (and for this spec, only) entry. Fall back to text assertion on
    // CHANGE_VALUES for defense-in-depth against timeline rendering quirks.
    await expect(page.getByTestId('history-item-0')).toBeVisible({
      timeout: 30_000,
    })
    await expect(page.getByText('CHANGE_VALUES')).toBeVisible()

    // Step 7 — Save Changes → confirm → assert success snackbar.
    await page.getByTestId('save-changes-btn').click()
    await expect(
      page.getByText('Submit Quality-Controlled Observations?')
    ).toBeVisible()
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
