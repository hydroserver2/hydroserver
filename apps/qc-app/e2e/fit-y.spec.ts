/**
 * Fit Y fits the primary axis to the edit target's points on screen. A
 * fit replaces the live y axis, so a second fit must read the live range,
 * not one left over from before the first. A fit leaves the last point on
 * the edge, so fitting again changes nothing.
 */

import { expect, test, type Page } from '@playwright/test'
import { installMocks, type MockQcSession } from './support/mocks'
import { gotoHome } from './support/app'
import {
  DATASTREAM_ID,
  FIXTURE_OBS_END_ISO,
  FIXTURE_OBS_SPACING_MS,
  FIXTURE_OBS_START_MS,
  MANAGED_DATASTREAM_ID,
  QC_HISTORY_ID,
  QC_SOURCE_CHECKSUM,
} from './support/fixtures'

const at = (i: number) =>
  new Date(FIXTURE_OBS_START_MS + i * FIXTURE_OBS_SPACING_MS).toISOString()

const series = (from: number, to: number, value: (i: number) => number) => {
  const idx = Array.from({ length: to - from }, (_, k) => from + k)
  return { phenomenonTime: idx.map(at), result: idx.map(value) }
}

const session: MockQcSession = {
  id: 'qcs-open',
  historyId: QC_HISTORY_ID,
  status: 'in_progress',
  description: null,
  phenomenonTimeStart: at(0),
  phenomenonTimeEnd: FIXTURE_OBS_END_ISO,
  sourceChecksum: QC_SOURCE_CHECKSUM,
  createdAt: at(0),
  committedAt: null,
  createdBy: { name: 'Test User', email: 'test@example.com' },
  dependencyIds: [],
  operations: [],
}

const yRange = (page: Page) =>
  page.evaluate(() => {
    const gd = document.querySelector('[data-testid="main-plot"]') as any
    return gd.layout.yaxis.range as [number, number]
  })

const clickFit = (page: Page, title: string) =>
  page.evaluate(
    (t) =>
      (
        document.querySelector(`.modebar-btn[data-title="${t}"]`) as HTMLElement
      ).click(),
    title
  )

const fitY = async (page: Page) => {
  const before = await yRange(page)
  await clickFit(page, 'Fit Y to visible')
  await expect.poll(() => yRange(page)).not.toEqual(before)
}

const openEditor = async (page: Page) => {
  await installMocks(page, {
    qcHistories: true,
    qcCommittedSession: false,
    qcSessionState: [session],
    observationsById: {
      [DATASTREAM_ID]: series(0, 120, (i) => (i < 40 ? 10 + (i % 5) : 500)),
      [MANAGED_DATASTREAM_ID]: series(0, 0, () => 10),
    },
  })
  await gotoHome(page)
  await page.getByTestId(`edit-datastream-${DATASTREAM_ID}`).click()
  await page.getByRole('button', { name: /continue/i }).first().click()
  await expect(page.getByTestId('open-editor-btn')).toBeVisible({
    timeout: 30_000,
  })
  await expect
    .poll(() =>
      page.evaluate((id) => {
        const gd = document.querySelector('[data-testid="main-plot"]') as any
        return gd?.data?.find((t: any) => t.id === id)?.y?.length ?? 0
      }, MANAGED_DATASTREAM_ID)
    )
    .toBeGreaterThan(0)
}

test('a second Fit Y fits only the points on screen', async ({ page }) => {
  await openEditor(page)

  await fitY(page)
  expect(await yRange(page)).toEqual([10, 500])

  // Zoom onto the low run: its x window still holds the 500s, off screen.
  await page.evaluate(async () => {
    const gd = document.querySelector('[data-testid="main-plot"]') as any
    const xs = gd.data.find((t: any) => t.id && t.y?.length).x
    const fmt = (v: number) =>
      new Date(v).toISOString().replace('T', ' ').replace('Z', '')
    await (window as any).Plotly.relayout(gd, {
      'xaxis.range': [fmt(xs[0]), fmt(xs[50])],
      'yaxis.range': [0, 30],
    })
  })

  await fitY(page)
  expect(await yRange(page)).toEqual([10, 14])
})

test('fitting X twice keeps the range', async ({ page }) => {
  await openEditor(page)
  const xRange = () =>
    page.evaluate(() => {
      const gd = document.querySelector('[data-testid="main-plot"]') as any
      return gd.layout.xaxis.range as [string, string]
    })
  // Zoom to a window whose edges fall between points.
  await page.evaluate(async () => {
    const gd = document.querySelector('[data-testid="main-plot"]') as any
    const xs = gd.data.find((t: any) => t.id && t.y?.length).x
    const fmt = (v: number) =>
      new Date(v).toISOString().replace('T', ' ').replace('Z', '')
    const pad = (xs[1] - xs[0]) / 2
    await (window as any).Plotly.relayout(gd, {
      'xaxis.range': [fmt(xs[10] - pad), fmt(xs[50] + pad)],
    })
  })
  const before = await xRange()
  await clickFit(page, 'Fit X to visible')
  await expect.poll(xRange).not.toEqual(before)
  const fitted = await xRange()

  await clickFit(page, 'Fit X to visible')
  await page.waitForTimeout(500)
  expect(await xRange()).toEqual(fitted)
})
