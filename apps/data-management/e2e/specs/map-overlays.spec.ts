import { expect, test } from '../support/test'
import { authenticateSession } from '../support/auth'
import { users } from '../support/fixtures'
import type { AppSettings } from '@/models/settings'

test('Map overlays honor defaults, load lazily, and keep visibility when changing basemaps', async ({
  page,
}) => {
  const apiBaseUrl = process.env.E2E_API_BASE_URL || 'http://127.0.0.1:18000'
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
          settings.mapConfiguration.defaultBaseLayer = 'Streets'
          settings.mapConfiguration.basemapLayers = [
            'Streets',
            'Satellite',
          ].map((name) => ({
            name,
            source: `${apiBaseUrl}/overlay-test/base/{z}/{x}/{y}.png`,
            attribution: '',
          }))
          settings.mapConfiguration.overlayLayers = [
            {
              name: 'Flowlines',
              source: `${apiBaseUrl}/overlay-test/flowlines/{z}/{x}/{y}.png`,
              attribution: 'Flowline provider',
              priority: 1000,
              visibleByDefault: false,
            },
            {
              name: 'Watersheds',
              source: `${apiBaseUrl}/overlay-test/watersheds/{z}/{x}/{y}.png`,
              attribution: 'Watershed provider',
              priority: -1000,
              visibleByDefault: true,
            },
          ]
          return open + JSON.stringify(settings) + close
        }
      )
      await route.fulfill({ response, body })
    }
  )
  const tileRequests: string[] = []
  await page.route('**/overlay-test/**', (route) => {
    tileRequests.push(route.request().url())
    return route.fulfill({
      contentType: 'image/png',
      body: Buffer.from(
        'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9sW1l7kAAAAASUVORK5CYII=',
        'base64'
      ),
    })
  })
  await authenticateSession(page, users.owner.email, users.owner.password)
  await page.goto('/browse')
  await expect(page.locator('.ol-attribution')).toContainText(
    'Watershed provider'
  )
  await expect
    .poll(() => tileRequests.some((url) => url.includes('/watersheds/')))
    .toBe(true)
  expect(tileRequests.some((url) => url.includes('/flowlines/'))).toBe(false)

  await page.getByRole('button', { name: 'Overlays', exact: true }).click()
  const watersheds = page.getByRole('checkbox', {
    name: 'Watersheds',
    exact: true,
  })
  const flowlines = page.getByRole('checkbox', {
    name: 'Flowlines',
    exact: true,
  })
  await expect(watersheds).toBeChecked()
  await expect(flowlines).not.toBeChecked()
  await flowlines.check()
  await expect
    .poll(() => tileRequests.some((url) => url.includes('/flowlines/')))
    .toBe(true)
  await expect(page.locator('.ol-attribution')).toContainText(
    'Flowline provider'
  )
  await watersheds.uncheck()
  await expect(page.locator('.ol-attribution')).not.toContainText(
    'Watershed provider'
  )
  await page.keyboard.press('Escape')

  await page.locator('.basemap-select').click()
  await page.getByRole('option', { name: 'Satellite', exact: true }).click()
  await expect(page.locator('.ol-attribution')).toContainText(
    'Flowline provider'
  )
  await expect(page.locator('.ol-attribution')).not.toContainText(
    'Watershed provider'
  )
  await page.getByRole('button', { name: 'Overlays', exact: true }).click()
  await expect(flowlines).toBeChecked()
  await expect(watersheds).not.toBeChecked()

  await page.reload()
  await expect(page.locator('.ol-attribution')).toContainText(
    'Watershed provider'
  )
  await expect(page.locator('.ol-attribution')).not.toContainText(
    'Flowline provider'
  )
})
