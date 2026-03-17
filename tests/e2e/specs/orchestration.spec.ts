import { expect, test } from '@playwright/test'

import { authenticateSession } from '../support/auth'
import { fixtures, users } from '../support/fixtures'

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
})
