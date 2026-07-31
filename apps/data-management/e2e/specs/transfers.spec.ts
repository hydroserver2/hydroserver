import { expect, test, type Page } from '@playwright/test'

import { authenticateSession } from '../support/auth'
import { fixtures, users } from '../support/fixtures'
import {
  createWorkspaceFromManagePage,
  deleteWorkspaceFromManagePage,
  workspaceListItem,
} from '../support/ui'

async function initiateTransfer(
  page: Page,
  workspaceName: string,
  newOwnerEmail: string
) {
  await workspaceListItem(page, workspaceName).click()
  await page.getByRole('tab', { name: 'Ownership' }).click()
  await page.getByLabel("New owner's email").fill(newOwnerEmail)
  await page.getByRole('button', { name: 'Begin transfer' }).click()
  await page.getByRole('button', { name: 'Confirm transfer' }).click()
  await expect(
    page.getByText(/An ownership transfer is pending to/)
  ).toBeVisible()
}

function pendingTransferBanner(page: Page) {
  return page.getByTestId('pending-transfers-banner')
}

test.describe('workspace transfers', () => {
  test.use({ storageState: { cookies: [], origins: [] } })

  test('pending workspace transfers are visible to the destination user', async ({
    page,
  }) => {
    await authenticateSession(
      page,
      users.unaffiliated.email,
      users.unaffiliated.password
    )
    await page.goto('/workspaces')

    const banner = pendingTransferBanner(page)
    await expect(banner).toBeVisible()
    await expect(banner).toContainText(fixtures.workspaces.transfer.name)
    await expect(
      banner.getByRole('button', { name: 'Accept transfer' })
    ).toBeVisible()
    await expect(banner.getByRole('button', { name: 'Decline' })).toBeVisible()
  })

  test('a pending workspace transfer can be declined by the destination user', async ({
    page,
    browser,
  }) => {
    const workspaceName = `E2E Transfer Cancel ${Date.now()}`

    await authenticateSession(page, users.owner.email, users.owner.password)
    await page.goto('/workspaces')
    await createWorkspaceFromManagePage(page, workspaceName)
    await initiateTransfer(page, workspaceName, users.unaffiliated.email)

    const targetContext = await browser.newContext()
    const targetPage = await targetContext.newPage()

    await authenticateSession(
      targetPage,
      users.unaffiliated.email,
      users.unaffiliated.password
    )
    await targetPage.goto('/workspaces')

    const banner = pendingTransferBanner(targetPage)
    await expect(banner).toContainText(workspaceName)
    await banner
      .locator('div')
      .filter({ hasText: workspaceName })
      .getByRole('button', { name: 'Decline' })
      .first()
      .click()
    await expect(banner.getByText(workspaceName)).toHaveCount(0)

    await page.reload()
    await deleteWorkspaceFromManagePage(page, workspaceName)

    await targetContext.close()
  })

  test('a pending workspace transfer can be accepted and ownership moves to the destination user', async ({
    page,
    browser,
  }) => {
    const workspaceName = `E2E Transfer Accept ${Date.now()}`

    await authenticateSession(page, users.owner.email, users.owner.password)
    await page.goto('/workspaces')
    await createWorkspaceFromManagePage(page, workspaceName)
    await initiateTransfer(page, workspaceName, users.unaffiliated.email)

    const targetContext = await browser.newContext()
    const targetPage = await targetContext.newPage()

    await authenticateSession(
      targetPage,
      users.unaffiliated.email,
      users.unaffiliated.password
    )
    await targetPage.goto('/workspaces')

    const banner = pendingTransferBanner(targetPage)
    await expect(banner).toContainText(workspaceName)
    await banner
      .locator('div')
      .filter({ hasText: workspaceName })
      .getByRole('button', { name: 'Accept transfer' })
      .first()
      .click()

    const ownedItem = workspaceListItem(targetPage, workspaceName)
    await expect(ownedItem).toBeVisible()
    await expect(ownedItem).toContainText('Owner')

    await page.reload()
    await expect(workspaceListItem(page, workspaceName)).toHaveCount(0)

    await deleteWorkspaceFromManagePage(targetPage, workspaceName)
    await targetContext.close()
  })
})
