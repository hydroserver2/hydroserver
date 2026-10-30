import { expect, test } from '../support/test'
import { authenticateSession } from '../support/auth'
import { fixtures, users } from '../support/fixtures'
import {
  chooseOverlayOption,
  deleteWorkspaceFromManagePage,
  fillCombobox,
  selectWorkspace,
  workspaceListItem,
} from '../support/ui'

test('admin workspace refresh waits for a slow app bootstrap', async ({
  page,
}) => {
  await authenticateSession(page, users.admin.email, users.admin.password)
  let requests = 0
  let bootstrapComplete = false
  let refreshedBeforeBootstrap = false
  const associationFilters: Array<string | null> = []
  await page.route(
    '**/api/ogc/collections/workspaces/items?**',
    async (route) => {
      associationFilters.push(
        new URL(route.request().url()).searchParams.get('isAssociated')
      )
      requests += 1
      if (requests === 1) {
        const response = await route.fetch()
        // Simulate a slow initial list while the Workspaces page mounts.
        await new Promise((resolve) => setTimeout(resolve, 500))
        bootstrapComplete = true
        await route.fulfill({ response })
      } else {
        if (!bootstrapComplete) refreshedBeforeBootstrap = true
        await route.continue()
      }
    }
  )

  await page.goto('/workspaces')
  await expect(
    workspaceListItem(page, fixtures.workspaces.private.name)
  ).toBeVisible()
  expect(requests).toBe(3)
  expect(refreshedBeforeBootstrap).toBe(false)
  expect(associationFilters).toEqual(['true', null, null])
})

test('admin can manage unaffiliated workspaces and keep them selected across pages', async ({
  page,
}) => {
  await authenticateSession(page, users.admin.email, users.admin.password)
  await page.goto('/workspaces')

  for (const workspace of Object.values(fixtures.workspaces)) {
    const item = workspaceListItem(page, workspace.name)
    await expect(item).toBeVisible()
    await expect(item.locator('[data-testid^="workspace-edit-"]')).toBeEnabled()
    await expect(
      item.locator('[data-testid^="workspace-delete-"]')
    ).toBeEnabled()
  }

  const workspace = fixtures.workspaces.private
  await workspaceListItem(page, workspace.name).click()
  await page.getByRole('tab', { name: 'Collaborators' }).click()
  await expect(page.getByTestId('add-collaborator-button')).toBeEnabled()
  await page.getByTestId('add-collaborator-button').click()
  await page.getByLabel("New collaborator's email").fill(users.admin.email)
  await page.getByTestId('new-collaborator-role').click()
  await chooseOverlayOption(page, 'Viewer')
  await page.getByTestId('submit-collaborator-button').click()

  const adminRow = page.getByTestId(`collaborator-row-${users.admin.email}`)
  await expect(adminRow).toContainText('Viewer (Admin)')
  await expect(
    page.getByTestId(`collaborator-row-${users.viewer.email}`)
  ).not.toContainText('(Admin)')
  await page.getByTestId(`edit-collaborator-${users.admin.email}`).click()
  await adminRow.getByRole('combobox').first().click()
  await chooseOverlayOption(page, 'Editor')
  await page.getByTestId(`save-collaborator-${users.admin.email}`).click()
  await expect(adminRow).toContainText('Editor (Admin)')

  await page.getByRole('tab', { name: 'Service accounts' }).click()
  await expect(
    page.getByRole('button', { name: 'Create service account' })
  ).toBeEnabled()
  await page.getByRole('tab', { name: 'Privacy' }).click()
  await expect(page.getByLabel('Make this workspace private')).toBeEnabled()
  await expect(page.getByRole('tab', { name: 'Ownership' })).toBeVisible()

  const renamed = `${workspace.name} renamed by admin`
  await workspaceListItem(page, workspace.name)
    .locator('[data-testid^="workspace-edit-"]')
    .click()
  await page.getByRole('dialog').getByLabel('Name').fill(renamed)
  await page.getByRole('button', { name: 'Update', exact: true }).click()
  await expect(workspaceListItem(page, renamed)).toBeVisible()

  await page
    .getByRole('link', { name: 'Job orchestration', exact: true })
    .click()
  await expect(page.getByTestId('workspace-selector')).toContainText(renamed)
  await selectWorkspace(page, fixtures.workspaces.public.name)
  await selectWorkspace(page, renamed)
  await expect(page.getByText(fixtures.orchestration.taskName)).toBeVisible()
  await page.getByText(fixtures.orchestration.taskName).click()
  await expect(
    page.getByRole('button', { name: 'Edit', exact: true })
  ).toBeEnabled()

  await page.goto('/workspaces')
  await expect(workspaceListItem(page, renamed)).toBeVisible()
  await deleteWorkspaceFromManagePage(page, fixtures.workspaces.transfer.name)
  await expect(workspaceListItem(page, renamed)).toBeVisible()
})

test('admin can create, edit, and delete sites in another user’s private workspace', async ({
  page,
}) => {
  await authenticateSession(page, users.admin.email, users.admin.password)
  await page.goto('/browse')
  const existingSite = page.locator(
    `[data-site-id="${fixtures.monitoringSites.private.id}"]`
  )
  await expect(existingSite).toBeVisible()
  await existingSite.hover()
  await expect(
    existingSite.getByRole('button', {
      name: `Edit ${fixtures.monitoringSites.private.name}`,
    })
  ).toBeVisible()
  await expect(
    existingSite.getByRole('button', {
      name: `Delete ${fixtures.monitoringSites.private.name}`,
    })
  ).toBeVisible()

  // Instance-wide management must not turn every site into one of "My sites".
  await page.getByTestId('my-sites-filter').click()
  await expect(existingSite).toHaveCount(0)
  await page.getByTestId('my-sites-filter').click()

  await page.getByTestId('register-site-button').click()
  await page.getByTestId('registration-workspace-select').click()
  await chooseOverlayOption(page, fixtures.workspaces.private.name)
  const dialog = page.getByRole('dialog')
  const siteName = 'Admin created site'
  await dialog.getByLabel('Site Code').fill('ADMIN-NEW')
  await dialog.getByLabel('Site Name').fill(siteName)
  await dialog
    .getByLabel('Site Description')
    .fill('Created by an unaffiliated instance admin.')
  await fillCombobox(page, 'Select Site Type', 'Lake')
  await dialog.getByLabel('Latitude').fill('41.7501')
  await dialog.getByLabel('Longitude').fill('-111.8102')
  await dialog.getByRole('button', { name: 'Save', exact: true }).click()

  const siteRow = page.locator('.site-row').filter({ hasText: siteName })
  await expect(siteRow).toBeVisible()
  await siteRow.hover()
  await siteRow.getByRole('button', { name: `Edit ${siteName}` }).click()
  await dialog.getByLabel('Site Name').fill(`${siteName} updated`)
  await dialog.getByRole('button', { name: 'Save', exact: true }).click()
  await expect(siteRow).toContainText(`${siteName} updated`)
  await siteRow.hover()
  await siteRow
    .getByRole('button', { name: `Delete ${siteName} updated` })
    .click()
  await dialog.getByLabel('Site name').fill(`${siteName} updated`)
  await dialog.getByRole('button', { name: 'Delete', exact: true }).click()
  await expect(siteRow).toHaveCount(0)
})

test('admin can view and cancel another user’s pending workspace transfer', async ({
  page,
}) => {
  await authenticateSession(page, users.admin.email, users.admin.password)
  await page.goto(
    `/workspaces?workspace=${fixtures.workspaces.transfer.id}&section=ownership`
  )

  await expect(
    page.getByText('An ownership transfer is pending to')
  ).toBeVisible()
  await expect(
    page.getByRole('button', { name: 'Begin transfer' })
  ).toHaveCount(0)
  await expect(page.getByTestId('pending-transfers-banner')).toHaveCount(0)
  await page
    .getByRole('button', { name: 'Cancel transfer', exact: true })
    .click()
  await expect(
    page.getByRole('button', { name: 'Begin transfer' })
  ).toBeVisible()
  await expect(
    page.getByText('An ownership transfer is pending to')
  ).toHaveCount(0)

  await page.reload()
  await expect(
    page.getByRole('button', { name: 'Begin transfer' })
  ).toBeVisible()
})
