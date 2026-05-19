/**
 * Shared helpers specific to individual ops (beyond the generic
 * `support/app.ts` preamble). Kept here so each edit spec doesn't
 * repeat the "seed a selection" preamble.
 */

import { expect, type Page } from '@playwright/test'
import { openOp, waitForSelection } from './app'

/**
 * Apply a Value Threshold filter wide enough to select every point
 * in the fixture series. Useful preamble for edit ops that require
 * a prior selection (ChangeValues, Interpolate, DeletePoints, etc.).
 *
 * Uses the input's `keyup.enter` handler (`onAddFilter` is wired
 * directly on the field) instead of `fill('0')` + click on the
 * "Add filter" button. The button path occasionally flaked on Firefox
 * because Playwright fired the click before Vuetify's v-text-field
 * committed the typed value via `update:modelValue`, leaving the
 * button's `:disabled` guard "still true" and swallowing the click
 * — the panel saw no add-filter event, `selectedData` stayed empty,
 * and `waitForSelection` timed out. Pressing Enter on the focused
 * input commits and dispatches in one event, so there's no window
 * for the value commit to race the click.
 */
export async function selectAllPoints(page: Page): Promise<void> {
  await openOp(page, 'valueThreshold')
  // The fixture sine wave is bounded by y ≈ 5..15, so `> 0` hits all.
  const value = page.getByLabel('Value')
  await value.fill('0')
  await value.press('Enter')
  await waitForSelection(page, 1)
}

/**
 * Wait for a history entry matching `methodText` (the formatted
 * Title-Case rendering of the op's method name, e.g. "Change Values").
 */
export async function expectHistoryContains(page: Page, methodText: string) {
  const row = page
    .locator('[data-testid^="history-item-"]')
    .filter({ hasText: methodText })
  await expect(row).toBeVisible({ timeout: 30_000 })
}
