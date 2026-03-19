import { expect, test, type Page } from '@playwright/test'

import { authenticateSession } from '../support/auth'
import { fixtures, users } from '../support/fixtures'

async function createWorkspace(page: Page, name: string) {
  await page.getByRole('button', { name: 'Manage workspaces' }).click()
  await page.getByRole('button', { name: 'Add workspace' }).click()
  await page.getByLabel('Name *').fill(name)
  await page.getByRole('button', { name: 'Save' }).click()
  await expect(page.getByRole('cell', { name, exact: true })).toBeVisible()
}

async function openWorkspaceTransfer(page: Page, name: string) {
  const workspaceRow = page.getByRole('row', { name: new RegExp(name) })
  await expect(workspaceRow).toBeVisible()
  await workspaceRow.locator('[data-testid^="workspace-access-control-"]').click()
  await page.getByText('Transfer ownership', { exact: true }).click()
}

async function initiateTransfer(
  page: Page,
  workspaceName: string,
  newOwnerEmail: string
) {
  await openWorkspaceTransfer(page, workspaceName)
  await page.getByLabel("New owner's email").fill(newOwnerEmail)
  await page.getByRole('button', { name: 'Submit' }).click()
  await page.getByRole('button', { name: 'Confirm' }).click()
  await expect(page.getByText(/An ownership transfer is pending to/)).toBeVisible()
  await page.getByRole('button', { name: 'Close' }).click()
}

async function deleteWorkspace(page: Page, name: string) {
  const workspaceRow = page.getByRole('row', { name: new RegExp(name) })
  await expect(workspaceRow).toBeVisible()
  await workspaceRow.locator('[data-testid^="workspace-delete-"]').click()
  await page.getByLabel('Workspace name').fill(name)
  await page.getByRole('button', { name: 'Delete' }).click()
  await expect(page.getByRole('cell', { name, exact: true })).toHaveCount(0)
}

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

  test('a pending workspace transfer can be cancelled by the destination user', async ({
    page,
    browser,
  }) => {
    const workspaceName = `E2E Transfer Cancel ${Date.now()}`

    await authenticateSession(page, users.owner.email, users.owner.password)
    await page.goto(`/orchestration?workspaceId=${fixtures.workspaces.private.id}`)
    await createWorkspace(page, workspaceName)
    await initiateTransfer(page, workspaceName, users.unaffiliated.email)

    const targetContext = await browser.newContext()
    const targetPage = await targetContext.newPage()

    await authenticateSession(
      targetPage,
      users.unaffiliated.email,
      users.unaffiliated.password
    )
    await targetPage.goto(`/orchestration?workspaceId=${fixtures.workspaces.transfer.id}`)
    await targetPage.getByRole('button', { name: 'Pending workspace transfer' }).click()

    const pendingRow = targetPage.getByRole('row', {
      name: new RegExp(workspaceName),
    })
    await expect(pendingRow).toBeVisible()
    await pendingRow.getByRole('button', { name: 'Cancel transfer' }).click()
    await expect(pendingRow).toHaveCount(0)

    await page.reload()
    await page.getByRole('button', { name: 'Manage workspaces' }).click()
    await deleteWorkspace(page, workspaceName)

    await targetContext.close()
  })

  test('a pending workspace transfer can be accepted and ownership moves to the destination user', async ({
    page,
    browser,
  }) => {
    const workspaceName = `E2E Transfer Accept ${Date.now()}`

    await authenticateSession(page, users.owner.email, users.owner.password)
    await page.goto(`/orchestration?workspaceId=${fixtures.workspaces.private.id}`)
    await createWorkspace(page, workspaceName)
    await initiateTransfer(page, workspaceName, users.unaffiliated.email)

    const targetContext = await browser.newContext()
    const targetPage = await targetContext.newPage()

    await authenticateSession(
      targetPage,
      users.unaffiliated.email,
      users.unaffiliated.password
    )
    await targetPage.goto(`/orchestration?workspaceId=${fixtures.workspaces.transfer.id}`)
    await targetPage.getByRole('button', { name: 'Pending workspace transfer' }).click()

    const pendingRow = targetPage.getByRole('row', {
      name: new RegExp(workspaceName),
    })
    await expect(pendingRow).toBeVisible()
    await pendingRow.getByRole('button', { name: 'Accept transfer' }).click()
    await expect(pendingRow).toHaveCount(0)

    await targetPage.getByRole('button', { name: 'Manage workspaces' }).click()
    const ownedRow = targetPage.getByRole('row', { name: new RegExp(workspaceName) })
    await expect(ownedRow).toBeVisible()
    await expect(ownedRow).toContainText('Owner')

    await page.reload()
    await page.getByRole('button', { name: 'Manage workspaces' }).click()
    await expect(page.getByRole('cell', { name: workspaceName, exact: true })).toHaveCount(0)

    await deleteWorkspace(targetPage, workspaceName)
    await targetContext.close()
  })
})
