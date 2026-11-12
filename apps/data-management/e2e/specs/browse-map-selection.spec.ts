import { createHash } from 'node:crypto'
import type { Locator } from '@playwright/test'
import { expect, test } from '../support/test'
import { authenticateSession } from '../support/auth'
import { fixtures, users } from '../support/fixtures'
import type { AppSettings } from '@/models/settings'

async function rasterFrame(canvas: Locator) {
  const frame = await canvas.evaluate((element) => {
    const canvas = element as HTMLCanvasElement
    return [canvas.toDataURL(), canvas.style.transform]
  })
  return createHash('sha256').update(JSON.stringify(frame)).digest('hex')
}

async function settledRasterFrame(canvas: Locator) {
  let previous = ''
  let lastChange = Date.now()
  await expect
    .poll(async () => {
      const current = await rasterFrame(canvas)
      if (current !== previous) {
        previous = current
        lastChange = Date.now()
      }
      return Date.now() - lastChange
    })
    .toBeGreaterThan(800)
  return previous
}

for (const dismissal of ['close button', 'map click', 'Escape'] as const) {
  test(`Browse preserves the map view when deselecting with ${dismissal}`, async ({
    page,
  }, testInfo) => {
    const apiBaseUrl = process.env.E2E_API_BASE_URL || 'http://127.0.0.1:18000'
    const appBaseUrl = process.env.E2E_APP_BASE_URL || 'http://127.0.0.1:14173'
    await page.context().grantPermissions(['local-network-access'])
    await page.route(
      (url) => url.href === `${apiBaseUrl}/` || url.pathname === '/browse',
      async (route) => {
        const response = await route.fetch()
        const html = await response.text()
        await route.fulfill({
          response,
          body: html.replace(
            /(<script id="app-settings" type="application\/json">)([\s\S]*?)(<\/script>)/,
            (_, open, json, close) => {
              if (!json.trim()) return open + json + close
              const settings = JSON.parse(json) as AppSettings
              settings.mapConfiguration.defaultBaseLayer = 'Test map'
              settings.mapConfiguration.basemapLayers = [
                {
                  name: 'Test map',
                  source: `${appBaseUrl}/map-view-test/{z}/{x}/{y}.svg`,
                  attribution: '',
                },
              ]
              settings.mapConfiguration.overlayLayers = []
              return open + JSON.stringify(settings) + close
            }
          ),
        })
      }
    )
    // Distinct local tiles make the rendered geographic view deterministic,
    // independent of internet tile services and marker/card visibility.
    await page.route('**/map-view-test/**', (route) => {
      const [z, x, y] = new URL(route.request().url()).pathname
        .match(/\d+/g)!
        .map(Number)
      return route.fulfill({
        contentType: 'image/svg+xml',
        body: `<svg xmlns="http://www.w3.org/2000/svg" width="256" height="256"><rect width="256" height="256" fill="hsl(${(x * 17 + y * 31 + z * 43) % 360},40%,85%)" stroke="black"/><text x="20" y="128" font-size="24">${z}/${x}/${y}</text></svg>`,
      })
    })

    await authenticateSession(page, users.owner.email, users.owner.password)
    await page.goto('/browse')
    const map = page.locator('.browse-map .ol-viewport')
    const canvas = map.locator('.ol-layer canvas').first()
    await expect(canvas).toBeVisible()
    const initialView = await settledRasterFrame(canvas)
    const selectSite = (id: string) =>
      page.locator(`[data-site-id="${id}"] .site-row-main`).click()
    const card = page.locator('.site-detail-card')
    await selectSite(fixtures.monitoringSites.public.id)
    await expect(card).toContainText(fixtures.monitoringSites.public.name)
    await expect(page).toHaveURL(
      new RegExp(`selectedSite=${fixtures.monitoringSites.public.id}`)
    )
    const selectedView = await settledRasterFrame(canvas)
    expect(selectedView).not.toBe(initialView)

    // Preserve the user's own pan and zoom as well as the selection's fly-to.
    await map.locator('.ol-zoom-in').click()
    const box = (await map.boundingBox())!
    await page.mouse.move(box.x + box.width * 0.6, box.y + box.height * 0.3)
    await page.mouse.down()
    await page.mouse.move(
      box.x + box.width * 0.6 + 70,
      box.y + box.height * 0.3 + 40,
      { steps: 8 }
    )
    await page.mouse.up()
    const beforeDismiss = await settledRasterFrame(canvas)

    if (dismissal === 'close button')
      await card.getByRole('button', { name: 'Close', exact: true }).click()
    else if (dismissal === 'Escape') await page.keyboard.press('Escape')
    else
      await map.click({ position: { x: box.width * 0.8, y: box.height * 0.2 } })
    await expect(card).toBeHidden()
    await expect(page).not.toHaveURL(/selectedSite=/)
    expect(await settledRasterFrame(canvas)).toBe(beforeDismiss)
    await page.screenshot({
      path: testInfo.outputPath('deselected-map.png'),
      animations: 'disabled',
    })

    await selectSite(fixtures.monitoringSites.private.id)
    await expect(card).toContainText(fixtures.monitoringSites.private.name)
    expect(await settledRasterFrame(canvas)).not.toBe(beforeDismiss)
  })
}
