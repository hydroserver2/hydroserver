/**
 * Gaps filter: surfaces timestamps where Δx between adjacent points
 * exceeds a threshold. The panel is live-commit via `GapFinder`'s
 * `auto-select-endpoints` prop — no Apply button, filling the
 * Amount input is enough to seed a selection once a gap is found.
 * The default fixture has a perfectly uniform 15-minute grid so a
 * small threshold still finds nothing — instead we use a custom
 * fixture with one deliberate gap.
 */

import { expect, test } from '@playwright/test'
import { installMocks } from './support/mocks'
import { openOp, setupEditView, waitForSelection } from './support/app'

function observationsWithGap() {
  const startMs = Date.parse('2024-01-01T00:00:00Z')
  const spacingMs = 15 * 60 * 1000
  const phenomenonTime: string[] = []
  const result: number[] = []
  for (let i = 0; i < 20; i++) {
    phenomenonTime.push(new Date(startMs + i * spacingMs).toISOString())
    result.push(10 + i * 0.1)
  }
  // Big ~4-hour gap before the tail.
  const gapStart = startMs + 20 * spacingMs + 4 * 60 * 60 * 1000
  for (let i = 0; i < 20; i++) {
    phenomenonTime.push(new Date(gapStart + i * spacingMs).toISOString())
    result.push(12 + i * 0.1)
  }
  return { phenomenonTime, result }
}

test.describe('filter: find gaps', () => {
  test.beforeEach(async ({ page }) => {
    await installMocks(page, { observations: observationsWithGap() })
    await setupEditView(page)
  })

  test('finds the deliberate gap in the fixture series', async ({ page }) => {
    await openOp(page, 'gaps')
    // Find gaps >= 30 minutes (unit defaults to minutes). Conservative
    // threshold that matches only the deliberate ~4h gap, not the
    // uniform 15-min spacing.
    await page.getByLabel('Amount').fill('30')
    // Live-commit: the GapFinder pushes gap-endpoint indices into the
    // store as soon as the threshold resolves.
    await waitForSelection(page, 1)

    // "N gap(s) in the datastream." (or "selected range" when the
    // shared filter-range toggle is on) alert confirms the detector
    // found at least one gap. Match either copy.
    await expect(
      page.getByText(/gaps? in the (datastream|selected range)/i)
    ).toBeVisible()
  })
})
