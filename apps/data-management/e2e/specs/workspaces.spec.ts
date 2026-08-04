import { expect, test } from '@playwright/test'

import { authenticateSession } from '../support/auth'
import { fixtures, users } from '../support/fixtures'
import {
  chooseOverlayOption,
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
    await deleteDialog
      .getByRole('button', { name: 'Delete', exact: true })
      .click()
    await expect(page.getByText('Workspace name does not match.')).toBeVisible()

    await deleteDialog.getByLabel('Workspace name').fill(renamedWorkspaceName)
    await deleteDialog
      .getByRole('button', { name: 'Delete', exact: true })
      .click()
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

    await page.getByRole('tab', { name: 'Overview' }).click()
    await expect(page.getByTestId('overview-members-count')).toHaveText('2')
    await page.getByRole('tab', { name: 'Collaborators' }).click()

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

  test('owner can create, edit, regenerate, and delete an API key', async ({
    page,
  }) => {
    const keyName = `E2E API Key ${Date.now()}`
    const renamedKeyName = `${keyName} Renamed`

    await authenticateSession(page, users.owner.email, users.owner.password)
    await page.goto(
      `/workspaces?workspace=${fixtures.workspaces.public.id}&section=api-keys`
    )

    await page.getByRole('button', { name: 'Create API key' }).click()
    let dialog = page.getByRole('dialog')
    await dialog.getByLabel('Name *').fill(keyName)
    await dialog.getByTestId('api-key-role').click()
    await chooseOverlayOption(page, 'Data Loader')
    await dialog.getByRole('button', { name: 'Save', exact: true }).click()

    let keyRow = page.getByRole('row', { name: new RegExp(keyName) })
    await expect(keyRow).toBeVisible()
    await expect(
      page.getByText('Your API key has been generated.', { exact: false })
    ).toBeVisible()

    await keyRow.getByRole('button', { name: `Edit ${keyName}` }).click()
    dialog = page.getByRole('dialog')
    await dialog.getByLabel('Name *').fill(renamedKeyName)
    await dialog.getByRole('button', { name: 'Update', exact: true }).click()
    keyRow = page.getByRole('row', { name: new RegExp(renamedKeyName) })
    await expect(keyRow).toBeVisible()

    await keyRow
      .getByRole('button', { name: `Regenerate ${renamedKeyName}` })
      .click()
    dialog = page.getByRole('dialog')
    await dialog.getByRole('button', { name: 'Regenerate key' }).click()
    await expect(dialog).toHaveCount(0)
    await expect(keyRow).toBeVisible()

    await keyRow
      .getByRole('button', { name: `Delete ${renamedKeyName}` })
      .click()
    dialog = page.getByRole('dialog')
    await dialog.getByRole('button', { name: 'Delete', exact: true }).click()
    await expect(keyRow).toHaveCount(0)
    await expect(
      page.getByText('Your API key has been generated.', { exact: false })
    ).toHaveCount(0)
  })

  test('viewer sees read-only workspace management controls', async ({
    page,
  }) => {
    await authenticateSession(page, users.viewer.email, users.viewer.password)
    await page.goto('/workspaces')
    await workspaceListItem(page, fixtures.workspaces.private.name).click()

    await page.getByRole('tab', { name: 'Collaborators' }).click()
    await expect(page.getByTestId('add-collaborator-button')).toBeDisabled()

    const viewerRow = page.getByTestId(`collaborator-row-${users.viewer.email}`)
    await expect(
      viewerRow.getByTestId(`edit-collaborator-${users.viewer.email}`)
    ).toBeDisabled()
    await expect(
      viewerRow.getByTestId(`remove-collaborator-${users.viewer.email}`)
    ).toBeEnabled()

    const editorRow = page.getByTestId(`collaborator-row-${users.editor.email}`)
    await expect(
      editorRow.getByTestId(`edit-collaborator-${users.editor.email}`)
    ).toBeDisabled()
    await expect(
      editorRow.getByTestId(`remove-collaborator-${users.editor.email}`)
    ).toBeDisabled()

    await page.getByRole('tab', { name: 'API keys' }).click()
    await expect(
      page.getByRole('button', { name: 'Create API key' })
    ).toBeDisabled()
    await expect(
      page.getByText("You don't have permission to view API keys")
    ).toHaveCount(0)

    await page.getByRole('tab', { name: 'Metadata' }).click()
    await page.getByRole('tab', { name: 'Methods' }).click()
    await expect(page.getByTestId('add-workspace-metadata-item')).toHaveCount(0)
    await expect(
      page.getByTestId('edit-metadata-b2cc0c86-c131-4721-8080-9f5f722224ec')
    ).toHaveCount(0)
    await expect(
      page.getByTestId('delete-metadata-b2cc0c86-c131-4721-8080-9f5f722224ec')
    ).toHaveCount(0)
  })

  test('workspace selection carries into the rest of the management app', async ({
    page,
  }) => {
    await authenticateSession(page, users.owner.email, users.owner.password)
    await page.goto('/workspaces?workspace=missing&section=missing')
    await expect(page).toHaveURL(
      /\/workspaces\?workspace=(?!missing(?:&|$))[^&]+$/
    )
    const fallbackWorkspaceId = new URL(page.url()).searchParams.get(
      'workspace'
    )
    expect(fallbackWorkspaceId).toBeTruthy()
    await expect(
      page.getByTestId(`workspace-list-item-${fallbackWorkspaceId}`)
    ).toHaveClass(/selected/)

    await page.goto(
      `/workspaces?workspace=${fixtures.workspaces.public.id}&section=api-keys`
    )

    await expect(
      page.getByRole('heading', { name: fixtures.workspaces.public.name })
    ).toBeVisible()
    await expect(page.getByRole('tab', { name: 'API keys' })).toHaveAttribute(
      'aria-selected',
      'true'
    )
    await expect(
      page.getByRole('row', { name: /apikey Data Loader/ })
    ).toBeVisible()

    await page
      .getByRole('button', {
        name: `Select ${fixtures.workspaces.private.name} workspace`,
      })
      .click()
    await expect(page).toHaveURL(
      new RegExp(`workspace=${fixtures.workspaces.private.id}`)
    )

    await page.goto('/sites')
    await expect(page.getByTestId('workspace-selector')).toContainText(
      fixtures.workspaces.private.name
    )
  })

  test('limited users get useful empty-state guidance without a create action', async ({
    page,
  }) => {
    await authenticateSession(page, users.limited.email, users.limited.password)
    await page.goto('/workspaces')

    await expect(
      page.getByRole('heading', { name: 'No workspaces available' })
    ).toBeVisible()
    await expect(
      page.getByRole('button', { name: 'New workspace' })
    ).toBeDisabled()
    await expect(
      page.getByRole('button', { name: 'Add workspace', exact: true })
    ).toBeDisabled()
  })

  test('workspace list failures show a retry state instead of false onboarding', async ({
    page,
  }) => {
    let failWorkspaceRequests = true
    await page.route('**/api/data/workspaces?**', async (route) => {
      if (failWorkspaceRequests) {
        await route.fulfill({
          status: 503,
          contentType: 'application/json',
          body: JSON.stringify('Temporarily unavailable'),
        })
      } else await route.continue()
    })

    await authenticateSession(page, users.owner.email, users.owner.password)
    await page.goto('/workspaces')
    await expect(
      page.getByRole('heading', { name: 'Unable to load workspaces' })
    ).toBeVisible()
    await expect(
      page.getByRole('heading', { name: 'Create your first workspace' })
    ).toHaveCount(0)

    failWorkspaceRequests = false
    await page.getByRole('button', { name: 'Retry' }).click()
    await expect(
      workspaceListItem(page, fixtures.workspaces.private.name)
    ).toBeVisible()
    await expect(page.getByTestId('workspace-detail')).toBeVisible()
  })

  test('overview keeps healthy totals visible when one service is unavailable', async ({
    page,
  }) => {
    await page.route(
      `**/api/data/workspaces/${fixtures.workspaces.private.id}/api-keys?**`,
      (route) =>
        route.fulfill({
          status: 503,
          contentType: 'application/json',
          body: JSON.stringify('Temporarily unavailable'),
        })
    )
    await authenticateSession(page, users.owner.email, users.owner.password)
    await page.goto(`/workspaces?workspace=${fixtures.workspaces.private.id}`)

    await expect(page.getByTestId('overview-members-count')).toHaveText('3')
    await expect(page.getByTestId('overview-sites-count')).toHaveText('2')
    await expect(page.getByTestId('overview-api-keys-count')).toHaveText('—')
    await expect(page.getByTestId('overview-metadata-count')).toHaveText('9')
    await expect(
      page.getByText('Some totals could not be loaded.')
    ).toBeVisible()
  })

  test('a slow overview response cannot overwrite the newly selected workspace', async ({
    page,
  }) => {
    await page.route('**/api/data/things/site-summaries?**', async (route) => {
      const workspaceId = new URL(route.request().url()).searchParams.get(
        'workspace_id'
      )
      if (workspaceId === fixtures.workspaces.private.id)
        await new Promise((resolve) => setTimeout(resolve, 700))
      const count = workspaceId === fixtures.workspaces.private.id ? 2 : 3
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(
          Array.from({ length: count }, (_, index) => ({
            id: `site-${index}`,
          }))
        ),
      })
    })
    await authenticateSession(page, users.owner.email, users.owner.password)
    await page.goto(`/workspaces?workspace=${fixtures.workspaces.private.id}`)
    await page
      .getByRole('button', {
        name: `Select ${fixtures.workspaces.public.name} workspace`,
      })
      .click()

    await expect(
      page.getByRole('heading', { name: fixtures.workspaces.public.name })
    ).toBeVisible()
    await expect(page.getByTestId('overview-sites-count')).toHaveText('3')
    await page.waitForTimeout(900)
    await expect(page.getByTestId('overview-sites-count')).toHaveText('3')
  })

  test('workspace management remains usable on a phone-sized screen', async ({
    page,
  }) => {
    await page.setViewportSize({ width: 500, height: 900 })
    await authenticateSession(page, users.owner.email, users.owner.password)
    await page.goto('/workspaces')

    const sidebarBox = await page.getByTestId('workspace-sidebar').boundingBox()
    const detailBox = await page.getByTestId('workspace-detail').boundingBox()
    expect(sidebarBox).not.toBeNull()
    expect(detailBox).not.toBeNull()
    expect(sidebarBox!.width).toBeGreaterThanOrEqual(490)
    expect(detailBox!.width).toBeGreaterThanOrEqual(490)
    expect(detailBox!.y).toBeGreaterThan(sidebarBox!.y)
    expect(
      await page.evaluate(() => document.documentElement.scrollWidth)
    ).toBeLessThanOrEqual(500)
  })
})
