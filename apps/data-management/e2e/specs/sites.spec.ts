import { expect, test, type Page } from '../support/test'

import { authenticateSession } from '../support/auth'
import { fixtures, users } from '../support/fixtures'
import {
  chooseAutocompleteOption,
  chooseOverlayOption,
  createWorkspaceFromManagePage,
  deleteWorkspaceFromManagePage,
  fillCombobox,
} from '../support/ui'

const datastreamEntriesByName = (page: Page, name: string) =>
  page.locator('[data-datastream-id]').filter({ hasText: name })

test.describe('sites and workspaces', () => {
  const apiBaseUrl = process.env.E2E_API_BASE_URL || 'http://127.0.0.1:18000'
  const sitePhotoPng = Buffer.from(
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9sW1l7kAAAAASUVORK5CYII=',
    'base64'
  )

  test('owner can use the top-level workspace and monitoring-site links', async ({
    page,
  }) => {
    const workspaceName = `E2E Workspace ${Date.now()}`

    await authenticateSession(page, users.owner.email, users.owner.password)
    await page.goto('/browse')
    await page
      .getByRole('link', { name: 'Manage workspaces', exact: true })
      .click()
    await expect(page).toHaveURL(/\/workspaces/)

    await createWorkspaceFromManagePage(page, workspaceName)
    await deleteWorkspaceFromManagePage(page, workspaceName)

    await page
      .getByRole('link', { name: 'Browse monitoring sites', exact: true })
      .click()
    await expect(page).toHaveURL(/\/browse$/)
    await expect(
      page.getByRole('heading', { name: 'Monitoring sites', level: 1 })
    ).toBeVisible()
  })

  test('public site details render seeded datastreams', async ({ page }) => {
    await page.goto(`/sites/${fixtures.monitoringSites.public.id}`)

    await expect(
      page.getByRole('heading', { name: fixtures.monitoringSites.public.name })
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
    await page.goto(`/sites/${fixtures.monitoringSites.privateWorkspacePublic.id}`)

    await expect(
      page.getByRole('heading', {
        name: fixtures.monitoringSites.privateWorkspacePublic.name,
        exact: true,
      })
    ).toBeVisible()
    await expect(
      page.getByRole('heading', { name: 'Site information' })
    ).toBeVisible()
    await expect(page.getByTestId('edit-site-button')).toHaveCount(0)
    await expect(page.getByTestId('site-access-control-button')).toHaveCount(0)
    await expect(page.getByTestId('add-datastream-button')).toHaveCount(0)
  })

  test('Browse search, workspace, and metadata filters narrow the site list', async ({
    page,
  }) => {
    await authenticateSession(page, users.owner.email, users.owner.password)
    await page.goto('/browse')
    await chooseAutocompleteOption(
      page,
      'Workspaces',
      fixtures.workspaces.public.name
    )

    const publicMonitoringSiteRow = page.getByRole('button', {
      name: `${fixtures.monitoringSites.public.name} ${fixtures.monitoringSites.public.siteCode} ${fixtures.workspaces.public.name}`,
      exact: true,
    })
    const privateWorkspaceRow = page
      .locator(`[data-site-id="${fixtures.monitoringSites.privatePublic.id}"]`)
      .locator('.site-row-main')
    const mutableMonitoringSiteRow = page
      .locator(`[data-site-id="${fixtures.monitoringSites.mutablePublic.id}"]`)
      .locator('.site-row-main')

    const searchBox = page.getByRole('textbox', { name: 'Search sites' })
    await expect(searchBox).toBeVisible()

    await searchBox.fill(fixtures.monitoringSites.public.siteCode)
    await expect(publicMonitoringSiteRow).toBeVisible()
    await expect(privateWorkspaceRow).toHaveCount(0)
    await expect(mutableMonitoringSiteRow).toHaveCount(0)

    await searchBox.clear()
    await expect(publicMonitoringSiteRow).toBeVisible()
    await expect(privateWorkspaceRow).toBeVisible()
    await expect(mutableMonitoringSiteRow).toBeVisible()

    await chooseAutocompleteOption(page, 'Key', 'E2E')
    await chooseAutocompleteOption(page, 'Value', 'Mutable')

    await expect(mutableMonitoringSiteRow).toBeVisible()
    await expect(publicMonitoringSiteRow).toHaveCount(0)
    await expect(privateWorkspaceRow).toHaveCount(0)

    await page.getByRole('button', { name: 'Reset', exact: true }).click()
    await expect(publicMonitoringSiteRow).toBeVisible()
    await expect(privateWorkspaceRow).toBeVisible()
    await expect(mutableMonitoringSiteRow).toBeVisible()

    await publicMonitoringSiteRow.click()
    const sidebarSiteTypeIconPath = await publicMonitoringSiteRow
      .locator('.site-row-icon path')
      .getAttribute('d')
    const selectedSiteTypeIcon = page.getByTestId('selected-site-type-icon')
    await expect(selectedSiteTypeIcon).toBeVisible()
    await expect(selectedSiteTypeIcon.locator('path')).toHaveAttribute(
      'd',
      sidebarSiteTypeIconPath ?? ''
    )

    await page.getByRole('button', { name: 'Workspace', exact: true }).click()
    const markerLegend = page.getByTestId('map-marker-legend')
    await expect(markerLegend).toContainText(fixtures.workspaces.public.name)
    await expect(markerLegend).toContainText(fixtures.workspaces.private.name)

    await page.getByRole('button', { name: 'Site type', exact: true }).click()
    await expect(markerLegend).toContainText('Public')
    await expect(markerLegend).toContainText('Private')

    await page.getByRole('button', { name: 'Metadata', exact: true }).click()
    await chooseAutocompleteOption(page, 'Metadata tag', 'E2E')
    await expect(markerLegend).toContainText('Mutable')

    await page.getByRole('button', { name: 'Metadata', exact: true }).click()
    await expect(markerLegend).toHaveCount(0)
  })

  test('Browse only offers the My sites filter to authenticated users', async ({
    page,
  }) => {
    await page.goto('/browse')
    await expect(page.getByTestId('my-sites-filter')).toHaveCount(0)

    await authenticateSession(
      page,
      users.unaffiliated.email,
      users.unaffiliated.password
    )
    await page.goto('/browse')

    const mySitesFilter = page.getByTestId('my-sites-filter')
    const publicMonitoringSiteRow = page.getByRole('button', {
      name: `${fixtures.monitoringSites.public.name} ${fixtures.monitoringSites.public.siteCode} ${fixtures.workspaces.public.name}`,
      exact: true,
    })

    await expect(mySitesFilter).toBeVisible()
    await expect(mySitesFilter).toHaveAttribute('aria-pressed', 'false')
    await expect(publicMonitoringSiteRow).toBeVisible()

    await mySitesFilter.click()
    await expect(mySitesFilter).toHaveAttribute('aria-pressed', 'true')
    await expect(page).toHaveURL(/mySites=1/)
    await expect(page.getByText('0 sites', { exact: true })).toBeVisible()
    await expect(publicMonitoringSiteRow).toHaveCount(0)

    await mySitesFilter.click()
    await expect(mySitesFilter).toHaveAttribute('aria-pressed', 'false')
    await expect(page).not.toHaveURL(/mySites=/)
    await expect(publicMonitoringSiteRow).toBeVisible()
  })

  test('Browse provides filter visibility and owner site CRUD controls', async ({
    page,
  }) => {
    await authenticateSession(page, users.owner.email, users.owner.password)
    await page.goto('/browse')

    await expect(
      page.getByRole('button', { name: 'Create Site', exact: true })
    ).toBeVisible()

    const siteRow = page.locator(
      `[data-site-id="${fixtures.monitoringSites.public.id}"]`
    )
    const siteRowActions = siteRow.locator('.site-row-actions')
    await expect(siteRow).toBeVisible()
    await expect(siteRowActions).toHaveCSS('opacity', '0')

    await siteRow.hover()
    await expect(siteRowActions).toHaveCSS('opacity', '1')
    await expect(
      siteRow.getByRole('button', {
        name: `Edit ${fixtures.monitoringSites.public.name}`,
      })
    ).toBeVisible()
    await expect(
      siteRow.getByRole('button', {
        name: `Delete ${fixtures.monitoringSites.public.name}`,
      })
    ).toBeVisible()

    await siteRow.locator('.site-row-main').click()
    await page.getByRole('heading', { name: 'Monitoring sites' }).hover()
    await expect(siteRow).toHaveClass(/selected/)
    await expect(siteRowActions).toHaveCSS('opacity', '1')

    await page.getByRole('button', { name: 'Hide Filters' }).click()
    await expect(
      page.getByRole('textbox', { name: 'Search sites' })
    ).toBeHidden()
    await expect(siteRow).toBeVisible()
    await page.getByRole('button', { name: 'Show Filters' }).click()
    await expect(
      page.getByRole('textbox', { name: 'Search sites' })
    ).toBeVisible()

    await siteRow
      .getByRole('button', { name: `Edit ${fixtures.monitoringSites.public.name}` })
      .click()
    const editDialog = page.getByRole('dialog')
    await expect(
      editDialog.getByText('Edit Site', { exact: true })
    ).toBeVisible()
    await editDialog.getByRole('button', { name: 'Cancel' }).click()
    await expect(editDialog).toBeHidden()

    await siteRow
      .getByRole('button', { name: `Delete ${fixtures.monitoringSites.public.name}` })
      .click()
    const deleteDialog = page.getByRole('dialog')
    await expect(
      deleteDialog.getByText('Confirm Deletion', { exact: true })
    ).toBeVisible()
    await expect(
      deleteDialog.locator('.v-toolbar.bg-red-darken-4')
    ).toBeVisible()
    await deleteDialog.getByRole('button', { name: 'Cancel' }).click()
    await expect(deleteDialog).toBeHidden()
  })

  test('Browse hides site mutation controls from read-only collaborators', async ({
    page,
  }) => {
    await authenticateSession(page, users.viewer.email, users.viewer.password)
    await page.goto('/browse')

    const siteRow = page.locator(
      `[data-site-id="${fixtures.monitoringSites.privateWorkspacePublic.id}"]`
    )
    await expect(siteRow).toBeVisible()
    await expect(
      siteRow.getByRole('button', {
        name: `Edit ${fixtures.monitoringSites.privateWorkspacePublic.name}`,
      })
    ).toHaveCount(0)
    await expect(
      siteRow.getByRole('button', {
        name: `Delete ${fixtures.monitoringSites.privateWorkspacePublic.name}`,
      })
    ).toHaveCount(0)
  })

  test('Browse shows site mutation controls to editors with MonitoringSite permissions', async ({
    page,
  }) => {
    await authenticateSession(page, users.editor.email, users.editor.password)
    await page.goto('/browse')

    const siteRow = page.locator(
      `[data-site-id="${fixtures.monitoringSites.privateWorkspacePublic.id}"]`
    )
    await expect(siteRow).toBeVisible()
    await siteRow.hover()
    await expect(
      siteRow.getByRole('button', {
        name: `Edit ${fixtures.monitoringSites.privateWorkspacePublic.name}`,
      })
    ).toBeVisible()
    await expect(
      siteRow.getByRole('button', {
        name: `Delete ${fixtures.monitoringSites.privateWorkspacePublic.name}`,
      })
    ).toBeVisible()
  })

  test('Browse metadata controls stay on one line with multiple values', async ({
    page,
  }) => {
    await page.route('**/api/data/monitoring-sites/site-summaries*', async (route) => {
      const response = await route.fetch()
      const summaries = (await response.json()) as Array<{
        tags: Array<{ key: string; value: string }>
      }>
      summaries[0]?.tags.push({ key: 'E2E', value: 'Additional value' })
      await route.fulfill({ response, json: summaries })
    })

    await authenticateSession(page, users.owner.email, users.owner.password)
    await page.goto(
      '/browse?tagKey=E2E&tagValues=Mutable&tagValues=Additional%20value'
    )

    const metadataControls = page.locator(
      '.metadata-filter-row .metadata-filter'
    )
    await expect(metadataControls).toHaveCount(2)
    await expect(metadataControls.nth(1).getByText('+1')).toBeVisible()

    const controlHeights = await metadataControls.evaluateAll((controls) =>
      controls.map((control) => control.getBoundingClientRect().height)
    )
    expect(controlHeights).toEqual([40, 40])

    await expect(metadataControls.nth(1).locator('.v-field__input')).toHaveCSS(
      'flex-wrap',
      'nowrap'
    )
  })

  test('Browse preserves space for site selections on a compact screen', async ({
    page,
  }) => {
    await page.setViewportSize({ width: 500, height: 640 })
    await authenticateSession(page, users.owner.email, users.owner.password)
    await page.goto('/browse')

    const siteList = page.locator('.site-list')
    await expect(siteList).toBeVisible()
    const siteListBox = await siteList.boundingBox()
    expect(siteListBox?.height ?? 0).toBeGreaterThanOrEqual(120)

    const siteTypeChips = page.locator('.chip-grid')
    await expect(siteTypeChips).toBeVisible()
    const siteTypeChipsBox = await siteTypeChips.boundingBox()
    expect(siteTypeChipsBox?.height ?? 0).toBeLessThanOrEqual(102)

    const chipGridOverflow = await siteTypeChips.evaluate(
      (element) => getComputedStyle(element).overflowY
    )
    expect(chipGridOverflow).toBe('auto')

    const chipGridDimensions = await siteTypeChips.evaluate((element) => ({
      clientHeight: element.clientHeight,
      scrollHeight: element.scrollHeight,
    }))
    expect(chipGridDimensions.scrollHeight).toBeLessThanOrEqual(
      chipGridDimensions.clientHeight
    )

    await expect(
      page.getByRole('button', {
        name: `${fixtures.monitoringSites.public.name} ${fixtures.monitoringSites.public.siteCode} ${fixtures.workspaces.public.name}`,
        exact: true,
      })
    ).toBeVisible()
  })

  test('owner can create, edit, and delete a site from Browse', async ({
    page,
  }) => {
    const stamp = Date.now()
    const siteCode = `E2E-REG-${stamp}`
    const siteName = `E2E Registered Site ${stamp}`
    const updatedSiteName = `${siteName} Updated`

    await authenticateSession(page, users.owner.email, users.owner.password)
    await page.goto('/browse')
    await page.getByTestId('register-site-button').click()
    await page.getByTestId('registration-workspace-select').click()
    await chooseOverlayOption(page, fixtures.workspaces.public.name)
    const siteFormDialog = page.getByRole('dialog')

    await page.getByLabel('Site Code *').fill(siteCode)
    await page.getByLabel('Site Name *').fill(siteName)
    await page
      .getByLabel('Site Description *')
      .fill('Temporary site created by the Playwright release coverage suite.')
    await fillCombobox(page, 'Select Site Type *', 'Lake')
    await page.getByLabel('Latitude *').fill('41.7501')
    await page.getByLabel('Longitude *').fill('-111.8102')
    await page.getByLabel('Elevation (m)').fill('1380')
    const tagKey = siteFormDialog.getByRole('combobox', { name: 'Key' })
    await tagKey.fill('E2E')
    await tagKey.press('Enter')
    const tagValue = siteFormDialog.getByRole('combobox', { name: 'Value' })
    await tagValue.fill('Registration')
    await tagValue.press('Enter')
    await siteFormDialog
      .getByRole('button', { name: 'Add', exact: true })
      .click()
    await page.getByRole('button', { name: 'Save' }).click()

    const siteRow = page.locator('.site-row').filter({ hasText: siteName })
    await expect(siteRow).toBeVisible()
    await siteRow.locator('.site-row-main').click()
    await page.getByRole('link', { name: 'View details' }).click()

    await expect(
      page.getByRole('heading', { name: siteName, exact: true })
    ).toBeVisible()
    await expect(page.getByText(siteCode, { exact: true })).toBeVisible()
    await expect(page.getByText('E2E: Registration')).toBeVisible()

    await page.goto('/browse')
    const createdSiteRow = page
      .locator('.site-row')
      .filter({ hasText: siteName })
    await createdSiteRow.hover()
    await createdSiteRow
      .getByRole('button', { name: `Edit ${siteName}` })
      .click()
    await page.getByLabel('Site Name *').fill(updatedSiteName)
    await page.getByRole('button', { name: 'Save' }).click()

    const updatedSiteRow = page
      .locator('.site-row')
      .filter({ hasText: updatedSiteName })
    await expect(updatedSiteRow).toBeVisible()
    await updatedSiteRow.hover()
    await updatedSiteRow
      .getByRole('button', { name: `Delete ${updatedSiteName}` })
      .click()
    await page.getByLabel('Site name').fill(updatedSiteName)
    await page
      .getByRole('button', { name: 'Delete', exact: true })
      .last()
      .click()
    await expect(updatedSiteRow).toHaveCount(0)
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
    await anonymousPage.goto(`/sites/${fixtures.monitoringSites.mutablePublic.id}`)
    await expect(
      anonymousPage.getByRole('heading', {
        name: fixtures.monitoringSites.mutablePublic.name,
        exact: true,
      })
    ).toBeVisible()
    await anonymousContext.close()

    await page.goto(`/sites/${fixtures.monitoringSites.mutablePublic.id}`)

    await expect(
      page.getByRole('heading', {
        name: fixtures.monitoringSites.mutablePublic.name,
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
      'Select method *',
      fixtures.metadata.publicAssignedMethod.name
    )
    await chooseAutocompleteOption(
      page,
      'Select observed property *',
      fixtures.metadata.publicAssignedObservedProperty.name
    )
    await chooseAutocompleteOption(
      page,
      'Select unit *',
      fixtures.metadata.publicAssignedUnit.name
    )
    await chooseAutocompleteOption(
      page,
      'Select processing level *',
      fixtures.metadata.publicAssignedProcessingLevel.name
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

    const datastreamRow = datastreamEntriesByName(page, datastreamName).first()
    await expect(datastreamRow).toBeVisible()

    await datastreamRow.locator('[data-testid^="datastream-actions-"]').click()
    await page.getByText('Edit datastream metadata').click()
    await page.getByLabel('Datastream name *').fill(renamedDatastreamName)
    await page.getByRole('button', { name: 'Update datastream' }).click()

    const renamedDatastreamRow = datastreamEntriesByName(
      page,
      renamedDatastreamName
    ).first()
    await expect(renamedDatastreamRow).toBeVisible()

    await renamedDatastreamRow
      .locator('[data-testid^="datastream-actions-"]')
      .click()
    await page.getByText('Delete datastream').click()
    await page.locator('input').last().fill('Delete')
    await page.getByRole('button', { name: 'Confirm' }).click()
    await expect(
      datastreamEntriesByName(page, renamedDatastreamName)
    ).toHaveCount(0)

    await page.getByTestId('delete-site-button').click()
    await page.getByLabel('Site name').fill(renamedSiteName)
    await page
      .getByRole('button', { name: 'Delete', exact: true })
      .last()
      .click()

    await expect(page).toHaveURL(/\/browse$/)
  })

  test('owner privacy toggles affect anonymous site and datastream metadata access', async ({
    page,
    browser,
  }) => {
    await authenticateSession(page, users.owner.email, users.owner.password)
    await page.goto(`/sites/${fixtures.monitoringSites.public.id}`)

    const anonymousContext = await browser.newContext()
    const anonymousPage = await anonymousContext.newPage()

    const siteHeading = anonymousPage.getByRole('heading', {
      name: fixtures.monitoringSites.public.name,
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
          `${apiBaseUrl}/api/data/monitoring-sites/${fixtures.monitoringSites.public.id}`
        )
        const monitoringSite = await response.json()
        return monitoringSite.isPrivate
      })
      .toBe(true)
    await page.getByRole('button', { name: 'Close' }).click()

    const blockedMonitoringSiteRequest = anonymousPage.waitForResponse((response) =>
      response.url().includes(`/api/data/monitoring-sites/${fixtures.monitoringSites.public.id}`)
    )
    await anonymousPage.goto(`/sites/${fixtures.monitoringSites.public.id}`)
    const blockedMonitoringSiteResponse = await blockedMonitoringSiteRequest
    expect([403, 404]).toContain(blockedMonitoringSiteResponse.status())
    await expect(siteHeading).toHaveCount(0)

    await page.getByTestId('site-access-control-button').click()
    await page.getByTestId('site-privacy-checkbox').click()
    await expect
      .poll(async () => {
        const response = await page.request.get(
          `${apiBaseUrl}/api/data/monitoring-sites/${fixtures.monitoringSites.public.id}`
        )
        const monitoringSite = await response.json()
        return monitoringSite.isPrivate
      })
      .toBe(false)
    await page.getByRole('button', { name: 'Close' }).click()

    await anonymousPage.goto(`/sites/${fixtures.monitoringSites.public.id}`)
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
    await anonymousPage.goto(`/sites/${fixtures.monitoringSites.public.id}`)
    await expect(
      datastreamEntriesByName(anonymousPage, fixtures.datastreams.public.name)
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
    await expect
      .poll(async () => {
        const response = await page.request.get(
          `${apiBaseUrl}/api/data/datastreams/${fixtures.datastreams.public.id}`
        )
        const datastream = await response.json()
        return datastream.isVisible
      })
      .toBe(true)

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
    await anonymousPage.goto(`/sites/${fixtures.monitoringSites.public.id}`)
    const anonymousPublicDatastreamRow = datastreamEntriesByName(
      anonymousPage,
      fixtures.datastreams.public.name
    )
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

    await anonymousPage.goto(`/sites/${fixtures.monitoringSites.public.id}`)
    await expect(
      datastreamEntriesByName(anonymousPage, fixtures.datastreams.public.name)
    ).toHaveCount(1)

    await anonymousContext.close()
  })

  test('owner can download data from a datastream actions menu', async ({
    page,
  }) => {
    await authenticateSession(page, users.owner.email, users.owner.password)
    await page.goto(`/sites/${fixtures.monitoringSites.public.id}`)

    const datastreamRow = datastreamEntriesByName(
      page,
      fixtures.datastreams.public.name
    ).first()
    await expect(datastreamRow).toBeVisible()

    await datastreamRow.locator('[data-testid^="datastream-actions-"]').click()

    const downloadPromise = page.waitForEvent('download')
    await page.getByText('Download data').click()
    const download = await downloadPromise

    expect(download.suggestedFilename()).toMatch(/\.(csv|zip)$/)
  })

  test('site datastream metadata modal exposes sections and csv download', async ({
    page,
  }) => {
    await authenticateSession(page, users.owner.email, users.owner.password)
    await page.goto(`/sites/${fixtures.monitoringSites.public.id}`)

    await page
      .getByTestId(`datastream-metadata-${fixtures.datastreams.public.id}`)
      .click()
    const metadataDialog = page.getByRole('dialog')
    await expect(
      metadataDialog.getByText('Datastream information')
    ).toBeVisible()
    await expect(
      metadataDialog.getByText('General', { exact: true })
    ).toBeVisible()
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
    await page.goto(`/sites/${fixtures.monitoringSites.public.id}`)

    await page
      .getByRole('link', { name: 'View on Data Visualization Page' })
      .click()
    await expect(page).toHaveURL(
      new RegExp(`/visualize-data\\?sites=${fixtures.monitoringSites.public.id}`)
    )
    await expect(
      page.getByText(fixtures.datastreams.public.name, { exact: true })
    ).toBeVisible()

    await page.goto(`/sites/${fixtures.monitoringSites.public.id}`)
    const datastreamRow = datastreamEntriesByName(
      page,
      fixtures.datastreams.public.name
    ).first()
    await datastreamRow.locator('[data-testid^="datastream-actions-"]').click()
    await page
      .getByTestId(`visualize-datastream-${fixtures.datastreams.public.id}`)
      .click()

    await expect(page).toHaveURL(
      new RegExp(
        `/visualize-data\\?sites=${fixtures.monitoringSites.public.id}&datastreams=${fixtures.datastreams.public.id}`
      )
    )
    await expect(
      page.getByRole('button', { name: 'Copy State as URL' })
    ).toBeVisible()
    await expect(
      page.getByText(fixtures.datastreams.public.name, { exact: true })
    ).toBeVisible()
  })
})
