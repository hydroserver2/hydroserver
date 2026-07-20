/**
 * Edit history toolbar:
 *   - Undo (toolbar + Ctrl+Z) pops the trailing edit and repopulates
 *     the redoStack; Redo re-applies it.
 *   - Expand chevron on a history row opens the Arguments panel.
 *   - "Reload from this step" reloads to a specific history index.
 *
 * We exercise the flow end-to-end: one filter + one edit, then undo /
 * redo the edit and check the row count.
 */

import { expect, test } from '@playwright/test'
import { installMocks } from './support/mocks'
import { openOp, setupEditView } from './support/app'
import { expectHistoryContains, selectAllPoints } from './support/ops'

test.describe('edit history toolbar', () => {
  test.beforeEach(async ({ page }) => {
    await installMocks(page)
    await setupEditView(page)
    await selectAllPoints(page)
    await openOp(page, 'changeValues')
    // Press Enter on the field instead of clicking Apply — same reason
    // as the selectAllPoints helper: Firefox occasionally fires the
    // Apply click before Vuetify's v-text-field commits, which leaves
    // the button's `:disabled` guard tripped and silently swallows the
    // click. The field's `@keyup.enter` handler dispatches in one
    // event, removing the commit/click race.
    const value = page.getByLabel('Value')
    await value.fill('1')
    await value.press('Enter')
    await expectHistoryContains(page, 'Change Values')
  })

  test('toolbar undo / redo buttons round-trip the trailing edit', async ({
    page,
  }) => {
    // Snapshot the post-edit row count. Edit ops emit a trailing
    // SELECTION through `recordPostActionSelection` (see
    // useFilterDispatch), so the exact count depends on whether that
    // marker landed — we just want round-trip invariance, not a fixed
    // integer.
    const rows = page.locator('[data-testid^="history-item-"]')
    const initial = await rows.count()
    expect(initial).toBeGreaterThanOrEqual(2)

    await page.getByTestId('history-undo-btn').click()
    await expect(rows).toHaveCount(initial - 1)

    await page.getByTestId('history-redo-btn').click()
    await expect(rows).toHaveCount(initial)
  })

  test('expand chevron reveals the Arguments panel for a history row', async ({
    page,
  }) => {
    const row = page.getByTestId('history-item-1')
    await row.getByRole('button', { name: /expand arguments/i }).click()
    await expect(row.getByText('Arguments')).toBeVisible()
  })

  test('per-item undo button on the trailing entry rolls it back', async ({
    page,
  }) => {
    // Per-item undo is only rendered on the trailing row, whatever its
    // index. Locate by the testid prefix instead of pinning to the
    // CHANGE_VALUES row, since `recordPostActionSelection` may have
    // appended a SELECTION marker after it.
    const rows = page.locator('[data-testid^="history-item-"]')
    const initial = await rows.count()
    expect(initial).toBeGreaterThanOrEqual(2)

    // The toolbar Undo button also matches `history-undo-*`; restrict to
    // the per-item buttons (`history-undo-<index>`) by requiring a digit.
    await page
      .locator('[data-testid^="history-undo-"]')
      .and(page.locator(':not([data-testid="history-undo-btn"])'))
      .click()
    await expect(rows).toHaveCount(initial - 1)
  })
})
