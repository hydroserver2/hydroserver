/**
 * Opening a session fits the plot's y axis to the edit target's data. The
 * editor first draws the grey source context alone, then adds the working
 * copy on the same axis; the axis must refit to it rather than keep the range
 * fitted to the context, which clipped the series.
 */

import { expect, test } from '@playwright/test'
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

// The context before the window sits near 10; the session's data reaches 500.
const WINDOW_START = 40
const PEAK = 500

const session: MockQcSession = {
  id: 'qcs-open',
  historyId: QC_HISTORY_ID,
  status: 'in_progress',
  description: null,
  phenomenonTimeStart: at(WINDOW_START),
  phenomenonTimeEnd: FIXTURE_OBS_END_ISO,
  sourceChecksum: QC_SOURCE_CHECKSUM,
  createdAt: at(WINDOW_START),
  committedAt: null,
  createdBy: { name: 'Test User', email: 'test@example.com' },
  dependencyIds: [],
  operations: [],
}

test('the edit target is not clipped by a range fitted to other data', async ({
  page,
}) => {
  await installMocks(page, {
    qcHistories: true,
    qcSessionState: [session],
    observationsById: {
      [DATASTREAM_ID]: series(0, 120, (i) => (i < WINDOW_START ? 10 : PEAK)),
      [MANAGED_DATASTREAM_ID]: series(0, WINDOW_START, () => 10),
    },
  })
  await gotoHome(page)

  // The raw source is already plotted, zoomed onto its low start.
  await page.getByTestId(`plot-checkbox-${DATASTREAM_ID}`).click()
  await page.getByTestId(`plot-option-${DATASTREAM_ID}`).click()
  await page.getByTestId('plot-source-apply').click()
  await page
    .getByTestId('data-loading-indicator')
    .waitFor({ state: 'hidden', timeout: 30_000 })
  const plotArea = page.locator('.js-plotly-plot .nsewdrag').first()
  const box = (await plotArea.boundingBox())!
  await page.mouse.move(box.x + box.width * 0.1, box.y + box.height / 2)
  for (let k = 0; k < 6; k++) await page.mouse.wheel(0, -300)

  await page.getByTestId(`edit-datastream-${DATASTREAM_ID}`).click()
  await page.getByRole('button', { name: /continue/i }).first().click()
  await expect(page.getByTestId('open-editor-btn')).toBeVisible({
    timeout: 30_000,
  })

  await expect
    .poll(
      () =>
        page.evaluate((id) => {
          const gd = document.querySelector('.js-plotly-plot') as any
          const edit = gd?.data?.find((t: any) => t.id === id)
          return edit?.y?.length ? (gd.layout.yaxis.range[1] as number) : null
        }, MANAGED_DATASTREAM_ID),
      { timeout: 15_000 }
    )
    .toBeGreaterThanOrEqual(PEAK)
})
