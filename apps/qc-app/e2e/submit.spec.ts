/**
 * Committing a QC session:
 *   - Save persists the session's operations
 *   - Commit posts the edited observations to the managed datastream with
 *     `bulk-create?mode=replace` and locks the session, which swaps the
 *     footer's Save and Commit for New session
 */

import { expect, test } from '@playwright/test'
import { installMocks, type MockQcSession } from './support/mocks'
import { openOp, setupEditView } from './support/app'
import { expectHistoryContains, selectAllPoints } from './support/ops'

test.describe('commit a QC session', () => {
  test('Save is enabled only while there are unsaved changes', async ({ page }) => {
    await installMocks(page, { qcHistories: true })
    await setupEditView(page)
    const save = page.getByTestId('exit-save-btn')
    await expect(save).toBeDisabled()

    await selectAllPoints(page)
    await openOp(page, 'changeValues')
    const value = page.getByLabel('Value')
    await value.fill('1')
    await value.press('Enter')
    await expectHistoryContains(page, 'Change Values')
    await expect(save).toBeEnabled()

    await save.click()
    await expect(page.getByText('Draft saved.')).toBeVisible()
    await expect(save).toBeDisabled()

    // Undoing a saved edit is a change that still needs saving.
    await page.getByTestId('history-undo-btn').click()
    await expect(save).toBeEnabled()
  })

  test('save then commit pushes a replace-mode payload', async ({ page }) => {
    const submissions: Array<{ mode: string | null; body: any }> = []
    const sessions: MockQcSession[] = []
    await installMocks(page, {
      qcHistories: true,
      submissions,
      qcSessionState: sessions,
    })
    await setupEditView(page)

    await selectAllPoints(page)
    await openOp(page, 'changeValues')
    const value = page.getByLabel('Value')
    await value.fill('1')
    await value.press('Enter')
    await expectHistoryContains(page, 'Change Values')

    const session = sessions.find((s) => s.status === 'in_progress')
    expect(session).toBeDefined()

    await page.getByTestId('exit-save-btn').click()
    await expect(page.getByText('Draft saved.')).toBeVisible()
    expect(session!.operations.map((o) => o.operationType)).toContain(
      'CHANGE_VALUES'
    )

    await page.getByTestId('exit-commit-btn').click()
    const dialog = page
      .locator('.v-overlay__content')
      .filter({ hasText: 'Commit session to datastream?' })
    await expect(dialog).toBeVisible()
    await dialog.getByLabel('Session description (optional)').fill('E2E pass')
    await dialog.getByRole('button', { name: 'Commit', exact: true }).click()

    await expect(page.getByText('Session committed.')).toBeVisible({
      timeout: 30_000,
    })
    await expect(page.getByTestId('exit-new-session-btn')).toBeVisible()

    expect(submissions).toHaveLength(1)
    const [submission] = submissions
    expect(submission!.mode).toBe('replace')
    expect(submission!.body?.fields).toEqual(['phenomenonTime', 'result'])
    expect(submission!.body?.data.length).toBeGreaterThan(0)

    expect(session!.status).toBe('committed')
    expect(session!.description).toBe('E2E pass')
  })
})
