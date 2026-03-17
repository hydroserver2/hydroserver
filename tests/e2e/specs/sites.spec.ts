import { expect, test } from '@playwright/test'

import { authenticateSession } from '../support/auth'
import { fixtures, users } from '../support/fixtures'
import { chooseAutocompleteOption, fillCombobox } from '../support/ui'

test.describe('sites and workspaces', () => {
  const sitePhotoPng = Buffer.from(
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9sW1l7kAAAAASUVORK5CYII=',
    'base64'
  )

  test('owner can create a workspace from the shared workspace toolbar', async ({ page }) => {
    const workspaceName = `E2E Workspace ${Date.now()}`

    await authenticateSession(page, users.owner.email, users.owner.password)
    await page.goto(`/orchestration?workspaceId=${fixtures.workspaces.private.id}`)
    await page.getByRole('button', { name: 'Manage workspaces' }).click()
    await page.getByRole('button', { name: 'Add workspace' }).click()

    await page.getByLabel('Name *').fill(workspaceName)
    await page.getByRole('button', { name: 'Save' }).click()

    await expect(
      page.getByRole('cell', { name: workspaceName, exact: true })
    ).toBeVisible()
  })

  test('public site details render seeded datastreams', async ({ page }) => {
    await page.goto(`/sites/${fixtures.things.public.id}`)

    await expect(
      page.getByRole('heading', { name: fixtures.things.public.name })
    ).toBeVisible()
    await expect(
      page.getByRole('heading', { name: 'Site information' })
    ).toBeVisible()
    await expect(
      page.getByRole('heading', { name: 'Datastreams available at this site' })
    ).toBeVisible()
    await expect(page.getByText(fixtures.datastreams.public.name)).toBeVisible()
    await expect(
      page.getByRole('link', { name: 'View on Data Visualization Page' })
    ).toBeVisible()
  })

  test('owner can edit, toggle privacy for, and delete a site with datastream CRUD', async ({
    page,
    browser,
  }) => {
    const stamp = Date.now()
    const renamedSiteName = `Workspace Site ${stamp}`
    const datastreamName = `E2E Datastream ${stamp}`
    const renamedDatastreamName = `${datastreamName} Updated`

    await authenticateSession(page, users.owner.email, users.owner.password)
    const anonymousContext = await browser.newContext()
    const anonymousPage = await anonymousContext.newPage()
    await anonymousPage.goto(`/sites/${fixtures.things.mutablePublic.id}`)
    await expect(
      anonymousPage.getByRole('heading', {
        name: fixtures.things.mutablePublic.name,
        exact: true,
      })
    ).toBeVisible()
    await anonymousContext.close()

    await page.goto(`/sites/${fixtures.things.mutablePublic.id}`)

    await expect(
      page.getByRole('heading', {
        name: fixtures.things.mutablePublic.name,
        exact: true,
      })
    ).toBeVisible()

    await page.getByTestId('edit-site-button').click()
    await page.getByLabel('Site Name *').fill(renamedSiteName)
    await page.getByRole('button', { name: 'Save' }).click()

    await expect(
      page.getByRole('heading', { name: renamedSiteName, exact: true })
    ).toBeVisible()

    await page.getByTestId('site-access-control-button').click()
    await page.getByTestId('site-privacy-checkbox').click()
    await page.getByRole('button', { name: 'Close' }).click()
    await expect(
      page.getByRole('row', { name: /Privacy Private/ })
    ).toBeVisible()

    await page.getByTestId('site-access-control-button').click()
    await page.getByTestId('site-privacy-checkbox').click()
    await page.getByRole('button', { name: 'Close' }).click()
    await expect(
      page.getByRole('row', { name: /Privacy Public/ })
    ).toBeVisible()

    await page.getByTestId('edit-site-button').click()
    await page.getByTestId('site-photo-input').setInputFiles({
      name: 'site-photo.png',
      mimeType: 'image/png',
      buffer: sitePhotoPng,
    })
    await expect(page.getByTestId('site-photo-preview-0')).toBeVisible()
    await page.getByRole('button', { name: 'Save' }).click()

    await expect(page.getByText('1 photos')).toBeVisible()

    await page.getByTestId('edit-site-button').click()
    await page.getByTestId('delete-existing-photo-0').click()
    await page.getByRole('button', { name: 'Save' }).click()

    await expect(page.getByText('No photos added yet.')).toBeVisible()

    await page.getByTestId('add-datastream-button').click()
    await chooseAutocompleteOption(
      page,
      'Select sensor *',
      'Public Assigned Sensor'
    )
    await chooseAutocompleteOption(
      page,
      'Select observed property *',
      'Public Assigned Observed Property'
    )
    await chooseAutocompleteOption(
      page,
      'Select unit *',
      'Public Assigned Unit'
    )
    await chooseAutocompleteOption(
      page,
      'Select processing level *',
      'Public Assigned Processing Level'
    )
    await page.getByLabel('Time aggregation interval *').fill('1')
    await page.locator('button').filter({ hasText: 'hours' }).first().click()
    await fillCombobox(page, 'Medium *', 'Surface Water')
    await fillCombobox(page, 'Aggregation statistic *', 'Continuous')
    await page.getByLabel('No data value *').fill('-9999')

    await page.getByLabel('Datastream name *').fill(datastreamName)
    await page
      .getByLabel('Datastream description *')
      .fill('Temporary datastream created by the Playwright CRUD suite.')
    await page.getByRole('button', { name: 'Create datastream' }).click()

    const datastreamRow = page
      .locator('tr, .datastream-card')
      .filter({ hasText: datastreamName })
      .first()
    await expect(datastreamRow).toBeVisible()

    await datastreamRow.locator('[data-testid^="datastream-actions-"]').click()
    await page.getByText('Edit datastream metadata').click()
    await page.getByLabel('Datastream name *').fill(renamedDatastreamName)
    await page.getByRole('button', { name: 'Update datastream' }).click()

    const renamedDatastreamRow = page
      .locator('tr, .datastream-card')
      .filter({ hasText: renamedDatastreamName })
      .first()
    await expect(renamedDatastreamRow).toBeVisible()

    await renamedDatastreamRow
      .locator('[data-testid^="datastream-actions-"]')
      .click()
    await page.getByText('Delete datastream').click()
    await page.locator('input').last().fill('Delete')
    await page.getByRole('button', { name: 'Confirm' }).click()
    await expect(
      page.locator('tr, .datastream-card').filter({
        hasText: renamedDatastreamName,
      })
    ).toHaveCount(0)

    await page.getByTestId('delete-site-button').click()
    await page.getByLabel('Site name').fill(renamedSiteName)
    await page.getByRole('button', { name: 'Delete', exact: true }).last().click()

    await expect(page).toHaveURL(/\/sites$/)
  })
})
