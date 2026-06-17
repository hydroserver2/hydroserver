/**
 * Datetime-range filter: selects points whose phenomenonTime falls
 * inside [from, to] using the DatePickerField inputs. The panel is
 * live-commit — opening it seeds a selection that spans the full
 * series range, without any Apply-filter button to press.
 */

import { expect, test } from '@playwright/test'
import { installMocks } from './support/mocks'
import { openOp, setupEditView, waitForSelection } from './support/app'

test.describe('filter: datetime range', () => {
  test.beforeEach(async ({ page }) => {
    await installMocks(page)
    await setupEditView(page)
  })

  test('opening the panel seeds a selection spanning the default window', async ({
    page,
  }) => {
    await openOp(page, 'datetimeRange')
    // Live-commit: the RangeStager pushes a selection as soon as it
    // resolves its initial range, so we just wait for the selection
    // to populate — no Apply-filter button exists.
    await waitForSelection(page, 1)

    // Sanity: the "N points selected in range." label appears after
    // the selection settles (plural form since the fixture has > 1).
    await expect(page.getByText(/points? selected in range\./i)).toBeVisible()
  })
})
