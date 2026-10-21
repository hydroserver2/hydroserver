import { expect, test } from '../support/test'
import { authenticateSession } from '../support/auth'
import { fixtures, users } from '../support/fixtures'
import { chooseAutocompleteOption } from '../support/ui'
import type { AppSettings } from '@/models/settings'
import { mapMarkerColors } from '@/utils/materialColors'

test('Browse keeps empty and filtered-out workspaces available', async ({
  page,
}) => {
  await authenticateSession(page, users.owner.email, users.owner.password)
  await page.goto('/browse')

  await chooseAutocompleteOption(
    page,
    'Workspaces',
    fixtures.workspaces.transfer.name
  )
  await expect(page.getByText('No sites match these filters.')).toBeVisible()
  await expect(page).toHaveURL(
    new RegExp(`workspaces=${fixtures.workspaces.transfer.id}`)
  )

  await page
    .getByRole('textbox', { name: 'Search sites' })
    .fill('No matching sites')
  const workspaceFilter = page.getByRole('combobox', {
    name: 'Workspaces',
    exact: true,
  })
  await page.locator('.workspace-filter .v-field').click()
  await expect(
    page.getByRole('option', {
      name: fixtures.workspaces.public.name,
      exact: true,
    })
  ).toBeVisible()
  await expect(
    page.getByRole('option', {
      name: fixtures.workspaces.transfer.name,
      exact: true,
    })
  ).toBeVisible()
  await workspaceFilter.press('Escape')
  await expect(page).toHaveURL(
    new RegExp(`workspaces=${fixtures.workspaces.transfer.id}`)
  )
})

test('Browse shows untagged sites for a key and filters them out when values are selected', async ({
  page,
}) => {
  await page.route(
    '**/api/ogc/collections/monitoring-sites/site-summaries*',
    async (route) => {
      const response = await route.fetch()
      const summaries = await response.json()
      for (const site of summaries) {
        delete site.tags.Network
        if (site.id === fixtures.monitoringSites.public.id)
          site.tags.Network = 'Primary'
        if (site.id === fixtures.monitoringSites.mutablePublic.id)
          site.tags.Network = 'Secondary'
      }
      await route.fulfill({ response, json: summaries })
    }
  )
  await authenticateSession(page, users.owner.email, users.owner.password)
  await page.goto('/browse?tagKey=Network')

  const legend = page.getByTestId('map-marker-legend')
  await expect(legend.locator('h3')).toHaveText('Network')
  await expect(legend).toContainText('Primary')
  await expect(legend).toContainText('Secondary')
  const untagged = legend.locator('li').filter({ hasText: 'Untagged' })
  await expect(untagged).toHaveCount(1)
  const primary = page.locator(
    `[data-site-id="${fixtures.monitoringSites.public.id}"]`
  )
  const secondary = page.locator(
    `[data-site-id="${fixtures.monitoringSites.mutablePublic.id}"]`
  )
  const untaggedSite = page.locator(
    `[data-site-id="${fixtures.monitoringSites.privatePublic.id}"]`
  )
  await expect(primary).toBeVisible()
  await expect(secondary).toBeVisible()
  await expect(untaggedSite).toBeVisible()
  const neutralColor = await page
    .locator('.v-application')
    .evaluate((element) =>
      getComputedStyle(element)
        .getPropertyValue('--v-theme-default')
        .replace(/\s/g, '')
    )
  const markerColor = await untagged
    .locator('.v-icon')
    .evaluate((element) => getComputedStyle(element).color.replace(/\s/g, ''))
  expect(markerColor).toBe(`rgb(${neutralColor})`)
  for (const [value, color] of [
    ['Primary', mapMarkerColors[1].background],
    ['Secondary', mapMarkerColors[0].background],
  ]) {
    const colors = await legend
      .locator('li')
      .filter({ hasText: value })
      .locator('.v-icon')
      .evaluate((element, expectedColor) => {
        const probe = document.createElement('span')
        probe.style.color = expectedColor
        return {
          actual: getComputedStyle(element).color,
          expected: probe.style.color,
        }
      }, color)
    expect(colors.actual).toBe(colors.expected)
  }
  await test.info().attach('Metadata key with untagged markers', {
    body: await page.screenshot(),
    contentType: 'image/png',
  })

  const search = page.getByRole('textbox', { name: 'Search sites' })
  await search.fill(fixtures.monitoringSites.privatePublic.siteCode)
  await expect(untaggedSite).toBeVisible()
  await expect(legend.locator('li')).toHaveCount(1)
  await expect(untagged).toHaveCount(1)
  await search.clear()
  await expect(legend.locator('li')).toHaveCount(3)

  await chooseAutocompleteOption(page, 'Value', 'Primary')
  await expect(primary).toBeVisible()
  await expect(secondary).toHaveCount(0)
  await expect(untaggedSite).toHaveCount(0)
  await expect(legend.locator('li')).toHaveCount(1)
  await expect(legend).toContainText('Primary')
  await expect(untagged).toHaveCount(0)

  await search.fill(fixtures.monitoringSites.privatePublic.siteCode)
  await expect(page.getByText('No sites match these filters.')).toBeVisible()
  await expect(untaggedSite).toHaveCount(0)
  await expect(legend).toHaveCount(0)
  await search.clear()
  await expect(primary).toBeVisible()
  await expect(secondary).toHaveCount(0)
  await expect(untaggedSite).toHaveCount(0)

  await chooseAutocompleteOption(page, 'Value', 'Secondary')
  await expect(primary).toBeVisible()
  await expect(secondary).toBeVisible()
  await expect(untaggedSite).toHaveCount(0)
  await expect(legend.locator('li')).toHaveCount(2)
  await expect(untagged).toHaveCount(0)
  await expect(legend).toContainText('Secondary')

  await page.reload()
  await expect(primary).toBeVisible()
  await expect(secondary).toBeVisible()
  await expect(untaggedSite).toHaveCount(0)
  await expect(untagged).toHaveCount(0)

  await page
    .locator('.metadata-filter-row .metadata-filter')
    .nth(1)
    .locator('.v-field__clearable')
    .click()
  await expect(untaggedSite).toBeVisible()
  await expect(untagged).toHaveCount(1)
  await expect(legend.locator('li')).toHaveCount(3)

  await chooseAutocompleteOption(page, 'Key', 'E2E')
  await expect(legend.locator('h3')).toHaveText('E2E')

  await page.getByRole('button', { name: 'Metadata', exact: true }).click()
  await expect(legend).toHaveCount(0)
  await expect(page).toHaveURL(/colorBy=none/)
  await page.reload()
  await expect(
    page.getByRole('button', { name: 'Metadata', exact: true })
  ).toHaveAttribute('aria-pressed', 'false')

  await chooseAutocompleteOption(page, 'Key', 'Network')
  await expect(legend.locator('h3')).toHaveText('Network')
})

test('Browse clears automatic metadata coloring with the key and Reset', async ({
  page,
}) => {
  await authenticateSession(page, users.owner.email, users.owner.password)
  await page.goto('/browse?tagKey=E2E')
  const legend = page.getByTestId('map-marker-legend')
  await expect(legend.locator('h3')).toHaveText('E2E')

  await page
    .locator('.metadata-filter-row .metadata-filter')
    .first()
    .locator('.v-field__clearable')
    .click()
  await expect(legend).toHaveCount(0)
  await expect(page).not.toHaveURL(/tagKey=|colorTagKey=|colorBy=metadata/)
  await page.reload()
  await expect(legend).toHaveCount(0)

  // Choosing a key deliberately replaces another marker coloring mode.
  await page.getByRole('button', { name: 'Workspace', exact: true }).click()
  await chooseAutocompleteOption(page, 'Key', 'E2E')
  await expect(legend.locator('h3')).toHaveText('E2E')
  await page.getByRole('button', { name: 'Reset', exact: true }).click()
  await expect(legend).toHaveCount(0)
  await expect(page).not.toHaveURL(/tagKey=|colorTagKey=|colorBy=/)
  await page.reload()
  await expect(legend).toHaveCount(0)
})

for (const { siteType, values } of [
  { siteType: 'Stream', values: ['Shared', 'Public only'] },
  { siteType: 'Spring', values: ['Shared', 'Public only'] },
  { siteType: 'Stream', values: ['Public only'] },
]) {
  test(`Browse retains valid filters when switching workspaces with ${siteType} and ${values.join(', ')}`, async ({
    page,
  }) => {
    const keepsShared = values.includes('Shared')
    await page.route(
      '**/api/ogc/collections/monitoring-sites/site-summaries*',
      async (route) => {
        const response = await route.fetch()
        const summaries = await response.json()
        for (const site of summaries) {
          delete site.tags.Basin
          if (site.id === fixtures.monitoringSites.public.id) {
            site.type = siteType
            site.tags.Basin = 'Shared'
          }
          if (site.id === fixtures.monitoringSites.mutablePublic.id) {
            site.type = siteType
            site.tags.Basin = 'Public only'
          }
          if (site.id === fixtures.monitoringSites.privateWorkspacePublic.id) {
            site.type = 'Stream'
            site.tags.Basin = 'Shared'
          }
          if (site.id === fixtures.monitoringSites.private.id)
            site.type = 'Stream'
        }
        await route.fulfill({ response, json: summaries })
      }
    )
    await authenticateSession(page, users.owner.email, users.owner.password)
    const query = new URLSearchParams({
      workspaces: fixtures.workspaces.public.id,
      siteTypes: siteType,
      tagKey: 'Basin',
    })
    for (const value of values) query.append('tagValues', value)
    await page.goto(`/browse?${query}`)
    await expect(page.getByRole('button', { name: siteType, exact: true })).toHaveClass(/selected/)
    await expect(page).toHaveURL(/tagValues=Public\+only/)
    await expect(page).toHaveURL(new RegExp(`siteTypes=${siteType}`))

    await page.locator('.workspace-filter .v-field__clearable').click()
    await chooseAutocompleteOption(
      page,
      'Workspaces',
      fixtures.workspaces.private.name
    )
    await page
      .getByRole('combobox', { name: 'Workspaces', exact: true })
      .press('Escape')
    await expect(page).toHaveURL(
      new RegExp(`workspaces=${fixtures.workspaces.private.id}`)
    )
    if (keepsShared) await expect(page).toHaveURL(/tagValues=Shared/)
    else await expect(page).not.toHaveURL(/tagValues=/)
    await expect(page).not.toHaveURL(/Public\+only/)
    if (siteType === 'Stream') await expect(page).toHaveURL(/siteTypes=Stream/)
    else await expect(page).not.toHaveURL(/siteTypes=/)

    const sharedSite = page.locator(
      `[data-site-id="${fixtures.monitoringSites.privateWorkspacePublic.id}"]`
    )
    await expect(sharedSite).toBeVisible()
    const legend = page.getByTestId('map-marker-legend')
    await expect(legend.locator('h3')).toHaveText('Basin')
    await expect(legend.locator('li')).toHaveCount(keepsShared ? 1 : 2)
    await expect(legend).toContainText('Shared')
    if (!keepsShared) await expect(legend).toContainText('Untagged')
    const valueFilter = page.getByRole('combobox', {
      name: 'Value',
      exact: true,
    })
    await valueFilter.click()
    await expect(
      page.getByRole('option', { name: 'Shared', exact: true })
    ).toBeVisible()
    await expect(
      page.getByRole('option', { name: 'Public only', exact: true })
    ).toHaveCount(0)
    await valueFilter.press('Escape')
    await page.reload()
    await expect(sharedSite).toBeVisible()
    if (keepsShared) await expect(page).toHaveURL(/tagValues=Shared/)
    else await expect(page).not.toHaveURL(/tagValues=/)
    await expect(page).not.toHaveURL(/Public\+only/)
  })
}

for (const viewport of [
  { width: 1280, height: 720 },
  { width: 500, height: 640 },
]) {
  test(`Browse site forms keep actions visible and allow click-away dismissal at ${viewport.width}px`, async ({
    page,
  }) => {
    // Exercise configured layers in both development and production builds.
    const apiBaseUrl = process.env.E2E_API_BASE_URL || 'http://127.0.0.1:18000'
    // Chromium treats a fulfilled document as public; allow the local test API.
    await page.context().grantPermissions(['local-network-access'])
    await page.route(
      (url) => url.href === `${apiBaseUrl}/` || url.pathname === '/browse',
      async (route) => {
        const response = await route.fetch()
        const html = await response.text()
        const body = html.replace(
          /(<script id="app-settings" type="application\/json">)([\s\S]*?)(<\/script>)/,
          (_, open, json, close) => {
            if (!json.trim()) return open + json + close
            const settings = JSON.parse(json) as AppSettings
            settings.mapConfiguration.defaultBaseLayer = 'Configured street map'
            settings.mapConfiguration.defaultSatelliteLayer =
              'Configured satellite map'
            settings.mapConfiguration.basemapLayers = [
              {
                name: 'Configured street map',
                source: `${apiBaseUrl}/e2e-map-tiles/{z}/{x}/{y}.png`,
                attribution: '',
              },
              {
                name: 'Configured satellite map',
                source: `${apiBaseUrl}/e2e-map-tiles/{z}/{x}/{y}.png`,
                attribution: '',
              },
            ]
            return open + JSON.stringify(settings) + close
          }
        )
        await route.fulfill({ response, body })
      }
    )
    await page.route('**/e2e-map-tiles/**', (route) =>
      route.fulfill({
        contentType: 'image/png',
        body: Buffer.from(
          'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9sW1l7kAAAAASUVORK5CYII=',
          'base64'
        ),
      })
    )
    await authenticateSession(page, users.owner.email, users.owner.password)
    await page.setViewportSize(viewport)
    await page.goto('/browse')
    await expect(
      page.locator('.browse-map .basemap-select-container')
    ).toContainText('Configured street map')
    await page.getByRole('button', { name: 'Create Site', exact: true }).click()

    const dialog = page.getByRole('dialog')
    await expect(dialog.getByText('Create Site', { exact: true })).toBeVisible()
    await expect(dialog.locator('.basemap-select-container')).toContainText(
      'Configured street map'
    )
    const save = dialog.getByRole('button', { name: 'Save', exact: true })
    const cancel = dialog.getByRole('button', { name: 'Cancel', exact: true })
    await expect(save).toBeInViewport()
    await expect(cancel).toBeInViewport()
    await test.info().attach('Create Site dialog', {
      body: await page.screenshot(),
      contentType: 'image/png',
    })

    const name = dialog.getByLabel('Site Name')
    await name.fill('In-progress site')
    await dialog.locator('.site-form-content').evaluate((element) => {
      element.scrollTop = element.scrollHeight
    })
    await expect(save).toBeInViewport()
    await expect(cancel).toBeInViewport()
    await page.mouse.click(2, 2)
    await expect(dialog).toBeHidden()

    await page.getByRole('button', { name: 'Create Site', exact: true }).click()
    await expect(dialog.getByLabel('Site Name')).toHaveValue('')
    await page.keyboard.press('Escape')
    await expect(dialog).toBeHidden()

    await page.getByRole('button', { name: 'Create Site', exact: true }).click()
    await cancel.click()
    await expect(dialog).toBeHidden()

    const site = page.locator(
      `[data-site-id="${fixtures.monitoringSites.public.id}"]`
    )
    await site.hover()
    await site
      .getByRole('button', {
        name: `Edit ${fixtures.monitoringSites.public.name}`,
      })
      .click()
    await expect(dialog.getByText('Edit Site', { exact: true })).toBeVisible()
    await expect(dialog.locator('.basemap-select-container')).toContainText(
      'Configured satellite map'
    )
    await expect(save).toBeInViewport()
    await expect(cancel).toBeInViewport()
    await page.mouse.click(2, 2)
    await expect(dialog).toBeHidden()
  })
}
