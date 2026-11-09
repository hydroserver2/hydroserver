import { expect, test } from '../support/test'
import { authenticateSession } from '../support/auth'
import { users } from '../support/fixtures'
import type { AppSettings } from '@/models/settings'

test('Map layers honor visibility and opacity, load lazily, and retain choices when changing basemaps', async ({
  page,
}) => {
  const apiBaseUrl = process.env.E2E_API_BASE_URL || 'http://127.0.0.1:18000'
  const tileBaseUrl = process.env.E2E_APP_BASE_URL || 'http://127.0.0.1:14173'
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
            source: `${tileBaseUrl}/overlay-test/base/{z}/{x}/{y}.png`,
            attribution: '',
          }))
          settings.mapConfiguration.overlayLayers = [
            {
              name: 'Flowlines',
              source: `${tileBaseUrl}/overlay-test/flowlines/{z}/{x}/{y}.png`,
              attribution: 'Flowline provider',
              priority: 1000,
              visibleByDefault: false,
            },
            {
              name: 'Watersheds',
              source: `${tileBaseUrl}/overlay-test/watersheds/{z}/{x}/{y}.png`,
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
  const setOpacity = async (name: string, opacity: number) => {
    const slider = page.getByRole('slider', { name, exact: true })
    await slider.focus()
    await slider.press('Home')
    for (let step = 0; step < opacity / 10; step++) await slider.press('PageUp')
    await expect(slider).toHaveAttribute('aria-valuenow', String(opacity))
    await expect(slider).toHaveAttribute('aria-valuetext', `${opacity}%`)
  }
  const rasterAlpha = () =>
    page
      .locator('.ol-layer canvas')
      .first()
      .evaluate((element) => {
        const canvas = element as HTMLCanvasElement
        return canvas
          .getContext('2d')!
          .getImageData(canvas.width / 2, canvas.height / 2, 1, 1).data[3]
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

  await page.locator('.basemap-select').click()
  await setOpacity('Base map opacity', 40)
  await page.keyboard.press('Escape')

  await page.getByRole('button', { name: 'Overlays', exact: true }).click()
  await expect(
    page.getByRole('button', { name: 'Overlays', exact: true })
  ).toBeVisible()
  const watersheds = page.getByRole('checkbox', {
    name: 'Watersheds',
    exact: true,
  })
  const flowlines = page.getByRole('checkbox', {
    name: 'Flowlines',
    exact: true,
  })
  const flowlinesOpacity = page.getByRole('slider', {
    name: 'Flowlines opacity',
    exact: true,
  })
  await expect(watersheds).toBeChecked()
  await expect(flowlines).not.toBeChecked()
  await expect(flowlinesOpacity).toBeDisabled()
  await expect(flowlinesOpacity).toHaveAttribute('tabindex', '-1')
  await expect(flowlinesOpacity).toHaveAttribute('aria-valuenow', '100')
  expect(tileRequests.some((url) => url.includes('/flowlines/'))).toBe(false)
  await setOpacity('Watersheds opacity', 80)
  await flowlines.check()
  await expect(flowlinesOpacity).toBeEnabled()
  await setOpacity('Flowlines opacity', 60)
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
  // A 40% base under a 60% overlay produces 76% alpha (194/255).
  await expect.poll(rasterAlpha).toBe(194)
  await flowlines.uncheck()
  await expect(flowlinesOpacity).toBeDisabled()
  await expect(flowlinesOpacity).toHaveAttribute('aria-valuenow', '60')
  await expect.poll(rasterAlpha).toBe(102)
  await flowlines.check()
  await expect(flowlinesOpacity).toBeEnabled()
  await expect(flowlinesOpacity).toHaveAttribute('aria-valuenow', '60')
  await page.keyboard.press('Escape')

  await page.locator('.basemap-select').click()
  await page.getByRole('option', { name: 'Satellite', exact: true }).click()
  await expect(page.locator('.ol-attribution')).toContainText(
    'Flowline provider'
  )
  await expect(page.locator('.ol-attribution')).not.toContainText(
    'Watershed provider'
  )
  await page.locator('.basemap-select').click()
  await expect(
    page.getByRole('slider', { name: 'Base map opacity', exact: true })
  ).toHaveAttribute('aria-valuenow', '40')
  await page.keyboard.press('Escape')
  await page.getByRole('button', { name: 'Overlays', exact: true }).click()
  await expect(flowlines).toBeChecked()
  await expect(watersheds).not.toBeChecked()
  await expect(
    page.getByRole('slider', { name: 'Flowlines opacity', exact: true })
  ).toHaveAttribute('aria-valuenow', '60')
  await expect(
    page.getByRole('slider', { name: 'Watersheds opacity', exact: true })
  ).toHaveAttribute('aria-valuenow', '80')

  await page.reload()
  await expect(page.locator('.ol-attribution')).toContainText(
    'Watershed provider'
  )
  await expect(page.locator('.ol-attribution')).not.toContainText(
    'Flowline provider'
  )
  await page.locator('.basemap-select').click()
  await expect(
    page.getByRole('slider', { name: 'Base map opacity', exact: true })
  ).toHaveAttribute('aria-valuenow', '100')
  await page.keyboard.press('Escape')
  await page.getByRole('button', { name: 'Overlays', exact: true }).click()
  await expect(
    page.getByRole('slider', { name: 'Flowlines opacity', exact: true })
  ).toHaveAttribute('aria-valuenow', '100')
  await expect(
    page.getByRole('slider', { name: 'Watersheds opacity', exact: true })
  ).toHaveAttribute('aria-valuenow', '100')
})
