/**
 * Fill-gaps edit: fills detected gaps with either linearly-interpolated
 * values or a sentinel NoData value. Uses the same gap fixture as
 * filter-gaps so there's something to fill.
 */

import { test } from '@playwright/test'
import { installMocks } from './support/mocks'
import { openOp, setupEditView } from './support/app'
import { expectHistoryContains } from './support/ops'
import { FIXTURE_OBS_START_MS } from './support/fixtures'

function observationsWithGap() {
  // See FIXTURE_OBS_START_MS — anchored to "now" so the series sits
  // inside the QC app's default 1w window.
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

test.describe('edit: fill gaps', () => {
  test.beforeEach(async ({ page }) => {
    await installMocks(page, { observations: observationsWithGap() })
    await setupEditView(page)
  })

  test('dispatches FILL_GAPS with a 30-minute threshold', async ({ page }) => {
    await openOp(page, 'fillGaps')
    // The panel has two Amount fields (gap + fill), so target them by
    // position inside the panel rather than by label alone.
    const panel = page.getByTestId('operation-panel-fillGaps')
    const amountInputs = panel.locator('input[type="number"]')
    await amountInputs.nth(0).fill('30')
    await amountInputs.nth(1).fill('15')
    await panel.getByRole('button', { name: /fill gaps/i }).click()
    await expectHistoryContains(page, 'Fill Gaps')
  })
})
