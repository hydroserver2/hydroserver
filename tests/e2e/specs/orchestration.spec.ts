import { expect, test } from '@playwright/test'

import { authenticateSession } from '../support/auth'
import { fixtures, users } from '../support/fixtures'
import { chooseOverlayOption } from '../support/ui'

test.describe('orchestration', () => {
  test('orchestration page loads seeded workspace orchestration data', async ({
    page,
  }) => {
    await authenticateSession(page, users.owner.email, users.owner.password)

    await page.goto(`/orchestration?workspaceId=${fixtures.workspaces.private.id}`)

    await expect(page.getByText('Job orchestration', { exact: true })).toBeVisible()
    await expect(page.getByText(fixtures.orchestration.systemName)).toBeVisible()
    await page
      .getByRole('button', { name: new RegExp(fixtures.orchestration.systemName) })
      .click()
    await expect(
      page.getByText(fixtures.orchestration.taskName)
    ).toBeVisible()
  })

  test('orchestration status filters narrow the task list', async ({
    page,
  }) => {
    await authenticateSession(page, users.owner.email, users.owner.password)

    await page.goto(`/orchestration?workspaceId=${fixtures.workspaces.private.id}`)

    await expect(page.getByText('Job orchestration', { exact: true })).toBeVisible()

    const statusFilter = page.getByRole('combobox', { name: 'Status filters' }).first()
    await expect(statusFilter).toBeVisible()

    await statusFilter.click()
    await chooseOverlayOption(page, 'OK')
    await expect(statusFilter).toContainText('OK')

    await statusFilter.click()
    await chooseOverlayOption(page, 'Needs attention')
    await expect(statusFilter).toContainText('Needs attention')
  })
})
