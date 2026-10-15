/**
 * The sessions timeline in the editor: each session row is a button the
 * keyboard can reach, and opening another session over unsaved edits asks
 * first.
 */

import { expect, test } from '@playwright/test'
import { installMocks } from './support/mocks'
import { COMMITTED_SESSION_ID } from './support/fixtures'
import { setupEditView } from './support/app'
import { applyChangeValues } from './support/ops'

test('opens a session from the keyboard', async ({ page }) => {
  await installMocks(page, { qcHistories: true })
  await setupEditView(page)

  const header = page.getByTestId(`session-header-${COMMITTED_SESSION_ID}`)
  await expect(header).toHaveRole('button')
  await header.focus()
  await page.keyboard.press('Enter')

  await expect(page.getByTestId('session-return-current')).toBeVisible()
})

test('asks before viewing another session over unsaved edits', async ({
  page,
}) => {
  await installMocks(page, { qcHistories: true })
  await setupEditView(page)
  await applyChangeValues(page)

  const header = page.getByTestId(`session-header-${COMMITTED_SESSION_ID}`)
  const confirm = page.getByTestId('view-session-confirm')
  await header.click()
  await expect(confirm).toBeVisible()
  await confirm.getByRole('button', { name: 'Cancel' }).click()
  await expect(confirm).toBeHidden()
  await expect(page.getByTestId('session-return-current')).toBeHidden()

  await header.click()
  await page.getByTestId('confirm-view-session-btn').click()
  await expect(page.getByTestId('session-return-current')).toBeVisible()
})
