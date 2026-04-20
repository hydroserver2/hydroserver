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
 */
export async function selectAllPoints(page: Page): Promise<void> {
  await openOp(page, 'valueThreshold')
  // The fixture sine wave is bounded by y ≈ 5..15, so `> 0` hits all.
  await page.getByLabel('Value').fill('0')
  await page.getByRole('button', { name: /add filter/i }).click()
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
