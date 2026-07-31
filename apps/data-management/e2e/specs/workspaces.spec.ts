import { expect, test } from '@playwright/test'

import { authenticateSession } from '../support/auth'
import { users } from '../support/fixtures'
import {
  createWorkspaceFromManagePage,
  deleteWorkspaceFromManagePage,
  workspaceListItem,
} from '../support/ui'

test.describe('workspace management', () => {
  test('owner can create, validate, update, privatize, and delete a workspace', async ({
    page,
    browser,
  }) => {
    const workspaceName = `E2E Workspace ${Date.now()}`
    const renamedWorkspaceName = `${workspaceName} Renamed`

    await authenticateSession(page, users.owner.email, users.owner.password)
    await page.goto('/workspaces')
    await createWorkspaceFromManagePage(page, workspaceName)

    const workspaceItem = workspaceListItem(page, workspaceName)
    await workspaceItem.locator('[data-testid^="workspace-edit-"]').click()
    await page.getByLabel('Name *').fill('')
    await page.getByRole('button', { name: 'Update' }).click()
    await expect(page.getByText('This field is required.')).toBeVisible()

    await page.getByLabel('Name *').fill(renamedWorkspaceName)
    await page.getByRole('button', { name: 'Update' }).click()
    const renamedItem = workspaceListItem(page, renamedWorkspaceName)
    await expect(renamedItem).toBeVisible()

    await renamedItem.click()
    await page.getByRole('tab', { name: 'Privacy' }).click()
    await page.getByLabel('Make this workspace private').click()

    const anonymousContext = await browser.newContext()
    const anonymousPage = await anonymousContext.newPage()
    await anonymousPage.goto('/browse')
    await anonymousPage.getByRole('combobox', { name: 'Workspaces' }).click()
    await expect(anonymousPage.getByText(renamedWorkspaceName)).toHaveCount(0)
    await anonymousContext.close()

    await renamedItem.locator('[data-testid^="workspace-delete-"]').click()
    const deleteDialog = page.getByRole('dialog')
    await deleteDialog.getByLabel('Workspace name').fill('wrong name')
    await deleteDialog.getByRole('button', { name: 'Delete', exact: true }).click()
    await expect(page.getByText('Workspace name does not match.')).toBeVisible()

    await deleteDialog.getByLabel('Workspace name').fill(renamedWorkspaceName)
    await deleteDialog.getByRole('button', { name: 'Delete', exact: true }).click()
    await expect(workspaceListItem(page, renamedWorkspaceName)).toHaveCount(0)
  })

  test('owner can add, update, and remove collaborators through the collaborators tab', async ({
    page,
  }) => {
    const workspaceName = `E2E Collaborators ${Date.now()}`

    await authenticateSession(page, users.owner.email, users.owner.password)
    await page.goto('/workspaces')
    await createWorkspaceFromManagePage(page, workspaceName)

    await workspaceListItem(page, workspaceName).click()
    await page.getByRole('tab', { name: 'Collaborators' }).click()

    await page.getByTestId('add-collaborator-button').click()
    await page.getByLabel("New collaborator's email").fill(users.viewer.email)
    await page.getByTestId('new-collaborator-role').click()
    await page.getByRole('option', { name: /Viewer/ }).click()
    await page.getByTestId('submit-collaborator-button').click()

    const collaboratorRow = page.getByTestId(
      `collaborator-row-${users.viewer.email}`
    )
    await expect(collaboratorRow).toBeVisible()
    await expect(collaboratorRow).toContainText('Viewer')

    await collaboratorRow.click()
    await page.getByTestId(`edit-collaborator-${users.viewer.email}`).click()
    await collaboratorRow.getByRole('combobox').first().click()
    await page.getByRole('option', { name: /Editor/ }).click()
    await page.getByTestId(`save-collaborator-${users.viewer.email}`).click()
    await expect(collaboratorRow).toContainText('Editor')

    await page.getByTestId(`remove-collaborator-${users.viewer.email}`).click()
    await expect(collaboratorRow).toHaveCount(0)

    await deleteWorkspaceFromManagePage(page, workspaceName)
  })
})
