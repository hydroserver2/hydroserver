import { expect, test } from '@playwright/test'

import { authenticateSession } from '../support/auth'
import { fixtures, users } from '../support/fixtures'

test.describe('workspace management', () => {
  test('owner can create, validate, update, privatize, and delete a workspace', async ({
    page,
    browser,
  }) => {
    const workspaceName = `E2E Workspace ${Date.now()}`
    const renamedWorkspaceName = `${workspaceName} Renamed`

    await authenticateSession(page, users.owner.email, users.owner.password)
    await page.goto(`/orchestration?workspaceId=${fixtures.workspaces.private.id}`)
    await page.getByRole('button', { name: 'Manage workspaces' }).click()
    await page.getByRole('button', { name: 'Add workspace' }).click()

    await page.getByLabel('Name *').fill(workspaceName)
    await page.getByRole('button', { name: 'Save' }).click()

    const workspaceRow = page.getByRole('row', { name: new RegExp(workspaceName) })
    await expect(workspaceRow).toBeVisible()

    await workspaceRow.getByRole('button').nth(1).click()
    await page.getByLabel('Name *').fill('')
    await page.getByRole('button', { name: 'Update' }).click()
    await expect(page.getByText('This field is required.')).toBeVisible()

    await page.getByLabel('Name *').fill(renamedWorkspaceName)
    await page.getByRole('button', { name: 'Update' }).click()
    const renamedRow = page.getByRole('row', {
      name: new RegExp(renamedWorkspaceName),
    })
    await expect(renamedRow).toBeVisible()

    await renamedRow.getByRole('button').nth(0).click()
    await page.getByText('Workspace privacy').click()
    await page.getByLabel('Make this workspace private').click()
    await page.getByRole('button', { name: 'Close' }).click()

    const anonymousContext = await browser.newContext()
    const anonymousPage = await anonymousContext.newPage()
    await anonymousPage.goto('/browse')
    await anonymousPage.getByRole('combobox', { name: 'Workspaces' }).click()
    await expect(anonymousPage.getByText(renamedWorkspaceName)).toHaveCount(0)
    await anonymousContext.close()

    await renamedRow.getByRole('button').nth(2).click()
    await page.getByLabel('Workspace name').fill('wrong name')
    await page.getByRole('button', { name: 'Delete' }).click()
    await expect(page.getByText('Workspace name does not match.')).toBeVisible()

    await page.getByLabel('Workspace name').fill(renamedWorkspaceName)
    await page.getByRole('button', { name: 'Delete' }).click()
    await expect(
      page.getByRole('cell', { name: renamedWorkspaceName, exact: true })
    ).toHaveCount(0)
  })

  test('owner can add, update, and remove collaborators through workspace access control', async ({
    page,
  }) => {
    const workspaceName = `E2E Collaborators ${Date.now()}`

    await authenticateSession(page, users.owner.email, users.owner.password)
    await page.goto(`/orchestration?workspaceId=${fixtures.workspaces.private.id}`)
    await page.getByRole('button', { name: 'Manage workspaces' }).click()
    await page.getByRole('button', { name: 'Add workspace' }).click()

    await page.getByLabel('Name *').fill(workspaceName)
    await page.getByRole('button', { name: 'Save' }).click()

    const workspaceRow = page.getByRole('row', { name: new RegExp(workspaceName) })
    await expect(workspaceRow).toBeVisible()
    await workspaceRow
      .locator('[data-testid^="workspace-access-control-"]')
      .click()

    await page.getByTestId('add-collaborator-button').click()
    await page.getByLabel("New collaborator's email").fill(users.viewer.email)
    await page.getByTestId('new-collaborator-role').click()
    await page.getByRole('option', { name: /Viewer/ }).click()
    await page.getByRole('button', { name: 'Add collaborator' }).last().click()

    const collaboratorRow = page.getByTestId(
      `collaborator-row-${users.viewer.email}`
    )
    await expect(collaboratorRow).toBeVisible()
    await expect(collaboratorRow).toContainText('Viewer')

    await collaboratorRow.click()
    await page
      .getByTestId(`edit-collaborator-${users.viewer.email}`)
      .click()
    await collaboratorRow.getByRole('combobox').first().click()
    await page.getByRole('option', { name: /Editor/ }).click()
    await page
      .getByTestId(`save-collaborator-${users.viewer.email}`)
      .click()
    await expect(collaboratorRow).toContainText('Editor')

    await page
      .getByTestId(`remove-collaborator-${users.viewer.email}`)
      .click()
    await expect(collaboratorRow).toHaveCount(0)

    await page.getByRole('button', { name: 'Close' }).click()
    await workspaceRow.locator('[data-testid^="workspace-delete-"]').click()
    await page.getByLabel('Workspace name').fill(workspaceName)
    await page.getByRole('button', { name: 'Delete' }).click()
    await expect(
      page.getByRole('cell', { name: workspaceName, exact: true })
    ).toHaveCount(0)
  })
})
