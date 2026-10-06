/**
 * Dates show in the zone the user picks from the nav rail, whatever zone
 * the browser is in, and the editor still zooms to the real session window.
 * The browser runs in Tokyo so a browser-local slip would show.
 */

import { expect, test, type Page } from '@playwright/test'
import { installMocks } from './support/mocks'
import { setupEditView } from './support/app'
import { FIXTURE_OBS_START_MS, MANAGED_DATASTREAM_ID } from './support/fixtures'

test.use({ timezoneId: 'Asia/Tokyo' })

/** How the table shows a data point's time in `timeZone`. */
const pointText = (ms: number, timeZone: string) =>
  new Intl.DateTimeFormat('en-US', {
    year: 'numeric',
    month: 'short',
    day: '2-digit',
    hour: '2-digit',
    hour12: false,
    minute: '2-digit',
    second: '2-digit',
    timeZone,
  }).format(ms)

/** The main plot's x range as instants, read from Plotly's UTC strings
 *  and moved back by the zone's offset at each end. */
const plotRangeWall = (page: Page) =>
  page.evaluate(() => {
    const gd = document.querySelector('[data-testid="main-plot"]') as any
    const r = gd?._fullLayout?.xaxis?.range as string[] | undefined
    return r?.map((v) => Date.parse(`${v.replace(' ', 'T')}Z`)) ?? null
  })

const firstTableTime = (page: Page) =>
  page.locator('.editable-cell__display').first().innerText()

async function pickUtc(page: Page) {
  await page.getByTestId('nav-rail-time-zone').click()
  await page.getByTestId('time-zone-mode').click()
  await page.getByRole('option', { name: 'UTC', exact: true }).click()
  await page.keyboard.press('Escape')
}

test.beforeEach(async ({ page }) => {
  await installMocks(page, { qcHistories: true })
})

test('opens zoomed to the session window, in the chosen zone', async ({
  page,
}) => {
  const created = page.waitForResponse(
    (r) =>
      r.request().method() === 'POST' &&
      /\/sessions$/.test(new URL(r.url()).pathname)
  )
  await setupEditView(page)
  const { data } = await (await created).json()
  const begin = Date.parse(data.phenomenonTimeStart)
  const end = Date.parse(data.phenomenonTimeEnd)
  const tokyo = 9 * 3_600_000

  // In the browser's zone the plot's clock runs 9 hours ahead of UTC.
  await expect
    .poll(async () => (await plotRangeWall(page))?.map((w) => w - tokyo))
    .toEqual([begin, end])

  await pickUtc(page)
  await expect.poll(() => plotRangeWall(page)).toEqual([begin, end])
})

test('shows times in the chosen zone, and keeps the choice', async ({
  page,
}) => {
  await setupEditView(page)
  await page.getByRole('button', { name: 'Table' }).click()
  await expect
    .poll(() => firstTableTime(page))
    .toBe(pointText(FIXTURE_OBS_START_MS, 'Asia/Tokyo'))

  await pickUtc(page)
  await expect
    .poll(() => firstTableTime(page))
    .toBe(pointText(FIXTURE_OBS_START_MS, 'UTC'))
  await expect(page.getByTestId('nav-rail-time-zone')).toContainText('UTC')

  await page.reload()
  await expect(page.getByTestId('nav-rail-time-zone')).toContainText('UTC', {
    timeout: 30_000,
  })
})

/** Points of the edit target Plotly draws inside the live x range, from its
 *  own computed positions, beside the visible-points counter. */
const drawnAndCounted = (page: Page) =>
  page.evaluate((id) => {
    const gd = document.querySelector('[data-testid="main-plot"]') as any
    const parse = (v: string) => Date.parse(`${v.replace(' ', 'T')}Z`)
    const [lo, hi] = (gd.layout.xaxis.range as string[]).map(parse)
    const i = gd.data.findIndex((t: any) => t.id === id)
    const drawn = (gd.calcdata[i]?.[0]?.t?.x ?? []) as number[]
    const counter = document
      .querySelector('[data-testid="tooltips-counter"]')
      ?.textContent?.split('/')[0]
      ?.replace(/\D/g, '')
    return {
      drawn: drawn.filter((x) => x >= lo! && x <= hi!).length,
      counted: Number(counter),
    }
  }, MANAGED_DATASTREAM_ID)

// Plotly reads a trace's numeric x as the browser's local clock; the points
// it draws must be the ones the app counts against the view.
test('counts the points it draws, in any zone', async ({ page }) => {
  await setupEditView(page)
  const zoomToHalf = () =>
    page.evaluate(async () => {
      const gd = document.querySelector('[data-testid="main-plot"]') as any
      const [lo, hi] = (gd.layout.xaxis.range as string[]).map((v) =>
        Date.parse(`${v.replace(' ', 'T')}Z`)
      )
      const fmt = (v: number) =>
        new Date(v).toISOString().replace('T', ' ').replace('Z', '')
      await (window as any).Plotly.relayout(gd, {
        'xaxis.range': [fmt(lo!), fmt(lo! + (hi! - lo!) / 2)],
      })
    })

  await zoomToHalf()
  await expect
    .poll(async () => {
      const { drawn, counted } = await drawnAndCounted(page)
      return drawn > 0 && drawn === counted
    })
    .toBe(true)

  await pickUtc(page)
  await zoomToHalf()
  await expect
    .poll(async () => {
      const { drawn, counted } = await drawnAndCounted(page)
      return drawn > 0 && drawn === counted
    })
    .toBe(true)
})
