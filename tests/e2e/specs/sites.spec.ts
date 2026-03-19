import { expect, test } from '@playwright/test'

import { authenticateSession } from '../support/auth'
import { fixtures, users } from '../support/fixtures'
import {
  chooseAutocompleteOption,
  fillCombobox,
  selectWorkspace,
} from '../support/ui'

test.describe('sites and workspaces', () => {
  const apiBaseUrl = process.env.E2E_API_BASE_URL || 'http://127.0.0.1:18000'
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

  test('viewer can access a private-workspace site in read-only mode', async ({
    page,
  }) => {
    await authenticateSession(page, users.viewer.email, users.viewer.password)
    await page.goto(`/sites/${fixtures.things.privateWorkspacePublic.id}`)

    await expect(
      page.getByRole('heading', {
        name: fixtures.things.privateWorkspacePublic.name,
        exact: true,
      })
    ).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Site information' })).toBeVisible()
    await expect(page.getByTestId('edit-site-button')).toHaveCount(0)
    await expect(page.getByTestId('site-access-control-button')).toHaveCount(0)
    await expect(page.getByTestId('add-datastream-button')).toHaveCount(0)
  })

  test('sites page search and metadata filters narrow the selected workspace site list', async ({
    page,
  }) => {
    await authenticateSession(page, users.owner.email, users.owner.password)
    await page.goto('/sites')
    await selectWorkspace(page, fixtures.workspaces.public.name)

    const publicThingRow = page.locator('tr').filter({
      hasText: fixtures.things.public.name,
    })
    const privateWorkspaceRow = page.locator('tr').filter({
      hasText: 'Private Thing Public Workspace',
    })
    const mutableThingRow = page.locator('tr').filter({
      hasText: fixtures.things.mutablePublic.name,
    })

    const searchBox = page.getByRole('textbox', { name: 'Search' }).first()
    await expect(searchBox).toBeVisible()

    await searchBox.fill(fixtures.things.public.siteCode)
    await expect(publicThingRow).toBeVisible()
    await expect(privateWorkspaceRow).toHaveCount(0)
    await expect(mutableThingRow).toHaveCount(0)

    await searchBox.clear()
    await expect(publicThingRow).toBeVisible()
    await expect(privateWorkspaceRow).toBeVisible()
    await expect(mutableThingRow).toBeVisible()

    await page.getByRole('button', { name: 'Filter sites' }).click()
    await chooseAutocompleteOption(page, 'Key', 'E2E')
    await chooseAutocompleteOption(page, 'Value', 'Mutable')

    await expect(mutableThingRow).toBeVisible()
    await expect(publicThingRow).toHaveCount(0)
    await expect(privateWorkspaceRow).toHaveCount(0)

    await page.getByRole('button', { name: 'Clear filters' }).click()
    await expect(publicThingRow).toBeVisible()
    await expect(privateWorkspaceRow).toBeVisible()
    await expect(mutableThingRow).toBeVisible()
  })

  test('owner can register a site with metadata and see the saved values on site details', async ({
    page,
  }) => {
    const stamp = Date.now()
    const siteCode = `E2E-REG-${stamp}`
    const siteName = `E2E Registered Site ${stamp}`

    await authenticateSession(page, users.owner.email, users.owner.password)
    await page.goto('/sites')
    await selectWorkspace(page, fixtures.workspaces.public.name)
    await page.getByRole('button', { name: 'Register a new site' }).click()

    await page.getByLabel('Site Code *').fill(siteCode)
    await page.getByLabel('Site Name *').fill(siteName)
    await page
      .getByLabel('Site Description *')
      .fill('Temporary site created by the Playwright release coverage suite.')
    await fillCombobox(page, 'Select Site Type *', 'Lake')
    await page.getByLabel('Latitude *').fill('41.7501')
    await page.getByLabel('Longitude *').fill('-111.8102')
    await page.getByLabel('Elevation (m) *').fill('1380')
    await fillCombobox(page, 'Key', 'E2E')
    await fillCombobox(page, 'Value', 'Registration')
    await page.getByRole('button', { name: 'Add' }).click()
    await page.getByRole('button', { name: 'Save' }).click()

    const siteRow = page.locator('tr').filter({ hasText: siteName }).first()
    await expect(siteRow).toBeVisible()
    await siteRow.click()

    await expect(page.getByRole('heading', { name: siteName, exact: true })).toBeVisible()
    await expect(page.getByText(siteCode, { exact: true })).toBeVisible()
    await expect(page.getByText('E2E: Registration')).toBeVisible()

    await page.getByTestId('delete-site-button').click()
    await page.getByLabel('Site name').fill(siteName)
    await page.getByRole('button', { name: 'Delete', exact: true }).last().click()
    await expect(page).toHaveURL(/\/sites$/)
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

  test('owner privacy toggles affect anonymous site and datastream metadata access', async ({
    page,
    browser,
  }) => {
    await authenticateSession(page, users.owner.email, users.owner.password)
    await page.goto(`/sites/${fixtures.things.public.id}`)

    const anonymousContext = await browser.newContext()
    const anonymousPage = await anonymousContext.newPage()

    const siteHeading = anonymousPage.getByRole('heading', {
      name: fixtures.things.public.name,
      exact: true,
    })
    const datastreamPrivacyToggle = page.getByTestId(
      `datastream-privacy-toggle-${fixtures.datastreams.public.id}`
    )
    const dataVisibilityToggle = page.getByTestId(
      `data-visibility-toggle-${fixtures.datastreams.public.id}`
    )

    await expect(datastreamPrivacyToggle).toBeVisible()
    await expect(dataVisibilityToggle).toBeVisible()

    await page.getByTestId('site-access-control-button').click()
    await page.getByTestId('site-privacy-checkbox').click()
    await expect
      .poll(async () => {
        const response = await page.request.get(
          `${apiBaseUrl}/api/data/things/${fixtures.things.public.id}`
        )
        const thing = await response.json()
        return thing.isPrivate
      })
      .toBe(true)
    await page.getByRole('button', { name: 'Close' }).click()

    const blockedThingRequest = anonymousPage.waitForResponse((response) =>
      response.url().includes(`/api/data/things/${fixtures.things.public.id}`)
    )
    await anonymousPage.goto(`/sites/${fixtures.things.public.id}`)
    const blockedThingResponse = await blockedThingRequest
    expect([403, 404]).toContain(blockedThingResponse.status())
    await expect(siteHeading).toHaveCount(0)

    await page.getByTestId('site-access-control-button').click()
    await page.getByTestId('site-privacy-checkbox').click()
    await expect
      .poll(async () => {
        const response = await page.request.get(
          `${apiBaseUrl}/api/data/things/${fixtures.things.public.id}`
        )
        const thing = await response.json()
        return thing.isPrivate
      })
      .toBe(false)
    await page.getByRole('button', { name: 'Close' }).click()

    await anonymousPage.goto(`/sites/${fixtures.things.public.id}`)
    await expect(siteHeading).toBeVisible()

    await datastreamPrivacyToggle.click()
    await expect
      .poll(async () => {
        const response = await page.request.get(
          `${apiBaseUrl}/api/data/datastreams/${fixtures.datastreams.public.id}`
        )
        const datastream = await response.json()
        return datastream.isPrivate
      })
      .toBe(true)
    await anonymousPage.goto(`/sites/${fixtures.things.public.id}`)
    await expect(
      anonymousPage.locator('tr, .datastream-card').filter({
        hasText: fixtures.datastreams.public.name,
      })
    ).toHaveCount(0)
    await datastreamPrivacyToggle.click()
    await expect
      .poll(async () => {
        const response = await page.request.get(
          `${apiBaseUrl}/api/data/datastreams/${fixtures.datastreams.public.id}`
        )
        const datastream = await response.json()
        return datastream.isPrivate
      })
      .toBe(false)

    await dataVisibilityToggle.click()
    await expect
      .poll(async () => {
        const response = await page.request.get(
          `${apiBaseUrl}/api/data/datastreams/${fixtures.datastreams.public.id}`
        )
        const datastream = await response.json()
        return datastream.isVisible
      })
      .toBe(false)
    await anonymousPage.goto(`/sites/${fixtures.things.public.id}`)
    const anonymousPublicDatastreamRow = anonymousPage
      .locator('tr, .datastream-card')
      .filter({
        hasText: fixtures.datastreams.public.name,
      })
    await expect(anonymousPublicDatastreamRow).toHaveCount(1)
    await dataVisibilityToggle.click()
    await expect
      .poll(async () => {
        const response = await page.request.get(
          `${apiBaseUrl}/api/data/datastreams/${fixtures.datastreams.public.id}`
        )
        const datastream = await response.json()
        return datastream.isVisible
      })
      .toBe(true)

    await anonymousPage.goto(`/sites/${fixtures.things.public.id}`)
    await expect(
      anonymousPage.locator('tr, .datastream-card').filter({
        hasText: fixtures.datastreams.public.name,
      })
    ).toHaveCount(1)

    await anonymousContext.close()
  })

  test('owner can download data from a datastream actions menu', async ({
    page,
  }) => {
    await authenticateSession(page, users.owner.email, users.owner.password)
    await page.goto(`/sites/${fixtures.things.public.id}`)

    const datastreamRow = page
      .locator('tr, .datastream-card')
      .filter({ hasText: fixtures.datastreams.public.name })
      .first()
    await expect(datastreamRow).toBeVisible()

    await datastreamRow
      .locator('[data-testid^="datastream-actions-"]')
      .click()

    const downloadPromise = page.waitForEvent('download')
    await page.getByText('Download data').click()
    const download = await downloadPromise

    expect(download.suggestedFilename()).toMatch(/\.(csv|zip)$/)
  })

  test('site datastream metadata modal exposes sections and csv download', async ({
    page,
  }) => {
    await authenticateSession(page, users.owner.email, users.owner.password)
    await page.goto(`/sites/${fixtures.things.public.id}`)

    await page.getByTestId(`datastream-metadata-${fixtures.datastreams.public.id}`).click()
    const metadataDialog = page.getByRole('dialog')
    await expect(metadataDialog.getByText('Datastream information')).toBeVisible()
    await expect(metadataDialog.getByText('General', { exact: true })).toBeVisible()
    await metadataDialog.getByText('Observed Property', { exact: true }).click()
    await expect(metadataDialog.getByText('Code')).toBeVisible()

    const csvDownload = page.waitForEvent('download')
    await metadataDialog.getByRole('button', { name: 'Download' }).click()
    const download = await csvDownload
    expect(download.suggestedFilename()).toBe(
      `datastream_${fixtures.datastreams.public.id}.csv`
    )
  })

  test('site links into visualization preserve site and datastream selection', async ({
    page,
  }) => {
    await page.setViewportSize({ width: 500, height: 900 })
    await authenticateSession(page, users.owner.email, users.owner.password)
    await page.goto(`/sites/${fixtures.things.public.id}`)

    await page
      .getByRole('link', { name: 'View on Data Visualization Page' })
      .click()
    await expect(page).toHaveURL(
      new RegExp(`/visualize-data\\?sites=${fixtures.things.public.id}`)
    )
    await expect(page.getByText(fixtures.datastreams.public.name, { exact: true })).toBeVisible()

    await page.goto(`/sites/${fixtures.things.public.id}`)
    const datastreamRow = page
      .locator('tr, .datastream-card')
      .filter({ hasText: fixtures.datastreams.public.name })
      .first()
    await datastreamRow
      .locator('[data-testid^="datastream-actions-"]')
      .click()
    await page.getByTestId(`visualize-datastream-${fixtures.datastreams.public.id}`).click()

    await expect(page).toHaveURL(
      new RegExp(
        `/visualize-data\\?sites=${fixtures.things.public.id}&datastreams=${fixtures.datastreams.public.id}`
      )
    )
    await expect(page.getByRole('button', { name: 'Copy State as URL' })).toBeVisible()
    await expect(page.getByText(fixtures.datastreams.public.name, { exact: true })).toBeVisible()
  })
})
