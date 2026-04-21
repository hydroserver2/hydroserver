/**
 * Persistence filter: flags runs of identical consecutive Y values
 * that repeat at least N times. The default fixture is sinusoidal
 * so no run exists — we build a step-function series with a 5-point
 * plateau to give the filter something to match.
 */

import { expect, test } from '@playwright/test'
import { installMocks } from './support/mocks'
import { openOp, setupEditView, waitForSelection } from './support/app'

function observationsWithPlateau() {
  const startMs = Date.parse('2024-01-01T00:00:00Z')
  const spacingMs = 15 * 60 * 1000
  const result: number[] = []
  // 5-point plateau at y=7, then 15 varying points.
  for (let i = 0; i < 5; i++) result.push(7)
  for (let i = 0; i < 15; i++) result.push(i + 1)
  const phenomenonTime = result.map((_, i) =>
    new Date(startMs + i * spacingMs).toISOString()
  )
  return { phenomenonTime, result }
}

test.describe('filter: persistence', () => {
  test.beforeEach(async ({ page }) => {
    await installMocks(page, { observations: observationsWithPlateau() })
    await setupEditView(page)
  })

  test('flags the 5-point plateau as persistent', async ({ page }) => {
    await openOp(page, 'persistence')
    // Default threshold is 2 — accept anything >= 3 for the plateau.
    await page.locator('input[type="number"]').fill('3')
    await page.getByRole('button', { name: /apply filter/i }).click()
    await waitForSelection(page, 1)

    // Filter entry may be collapsed to a rolled-up "Selection" row after
    // dispatchSelection fires — accept either as proof the filter ran.
    const row = page
      .locator('[data-testid^="history-item-"]')
      .filter({ hasText: /Persistence|Selection/ })
    await expect(row.first()).toBeVisible()
  })
})
