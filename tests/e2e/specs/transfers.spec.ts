import { expect, test } from '@playwright/test'

import { authenticateSession } from '../support/auth'
import { fixtures, users } from '../support/fixtures'

test.describe('workspace transfers', () => {
  test.use({ storageState: { cookies: [], origins: [] } })

  test('pending workspace transfers are visible to the destination user', async ({
    page,
  }) => {
    await authenticateSession(page, users.unaffiliated.email, users.unaffiliated.password)
    await page.goto(`/orchestration?workspaceId=${fixtures.workspaces.transfer.id}`)

    await expect(
      page.getByRole('button', { name: 'Pending workspace transfer' })
    ).toBeVisible()

    await page.getByRole('button', { name: 'Pending workspace transfer' }).click()

    await expect(
      page.getByRole('cell', { name: fixtures.workspaces.transfer.name, exact: true })
    ).toBeVisible()
    await expect(
      page.getByRole('button', { name: 'Accept transfer' })
    ).toBeVisible()
    await expect(
      page.getByRole('button', { name: 'Cancel transfer' })
    ).toBeVisible()
  })
})
