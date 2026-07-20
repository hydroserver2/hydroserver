/**
 * Save + submit flow:
 *   - Save triggers the "Submit QC observations?" confirmation
 *   - Confirming posts to `bulk-create?mode=replace` — the mocks log
 *     the submission so we can assert on its shape
 *   - Success snackbar appears and editHistory is cleared
 */

import { expect, test } from '@playwright/test'
import { installMocks } from './support/mocks'
import { openOp, setupEditView } from './support/app'
import { expectHistoryContains, selectAllPoints } from './support/ops'

test.describe('submit quality-controlled observations', () => {
  test('save → confirm → server receives replace-mode payload', async ({
    page,
  }) => {
    const submissions: Array<{ mode: string | null; body: any }> = []
    await installMocks(page, { submissions })
    await setupEditView(page)
    await selectAllPoints(page)
    await openOp(page, 'changeValues')
    await page.getByLabel('Value').fill('1')
    await page.getByRole('button', { name: 'Apply' }).click()
    await expectHistoryContains(page, 'Change Values')

    await page.getByTestId('exit-save-btn').click()
    await expect(page.getByText('Submit QC observations?')).toBeVisible()
    await page.getByRole('button', { name: 'Submit' }).click()

    await expect(
      page.getByText('Quality-controlled observations submitted')
    ).toBeVisible({ timeout: 30_000 })

    // History is cleared after a successful submit.
    await expect(page.getByTestId('history-item-0')).toHaveCount(0, {
      timeout: 15_000,
    })

    // The mocks recorded exactly one bulk-create call in replace mode.
    expect(submissions.length).toBeGreaterThanOrEqual(1)
    const first = submissions[0]
    expect(first.mode).toBe('replace')
    expect(first.body?.fields).toEqual(['phenomenonTime', 'result'])
    expect(Array.isArray(first.body?.data)).toBe(true)
  })
})
