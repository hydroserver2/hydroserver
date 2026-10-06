/**
 * Reloading inside the editor lands back in it. While the session reopens
 * the plot shows a loading state and the address bar keeps the link as it
 * came in, so a second reload mid-load lands in the same place.
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

const editPlotVisible = (page: Page) =>
  page.evaluate(
    () =>
      !!document.querySelector('#qc-plot-host-edit')?.checkVisibility?.()
  )

test('a reload mid-load keeps the link and reopens the editor', async ({
  page,
}) => {
  test.slow()
  await installMocks(page, {
    qcHistories: true,
    qcCommittedSession: false,
    qcSessionState: [session],
    observationsById: {
      [DATASTREAM_ID]: series(0, 120, (i) => 10 + (i % 5)),
      [MANAGED_DATASTREAM_ID]: series(0, 0, () => 10),
    },
  })
  await gotoHome(page)
  await page.getByTestId(`edit-datastream-${DATASTREAM_ID}`).click()
  await page.getByRole('button', { name: /continue/i }).first().click()
  await expect(page.getByTestId('open-editor-btn')).toBeVisible({
    timeout: 30_000,
  })
  await page.getByTestId('open-editor-btn').click()
  await page.getByRole('button', { name: /^Table$/ }).click()
  await expect.poll(() => new URL(page.url()).searchParams.get('tab')).toBe('t')
  await expect.poll(() => new URL(page.url()).searchParams.get('z')).toBeTruthy()
  const link = page.url()

  // Slow the API so the restore is observable.
  await page.route('**/api/**', async (route) => {
    await new Promise((r) => setTimeout(r, 1000))
    await route.fallback()
  })
  await page.reload()

  await expect(page.getByText('Opening the edit session…')).toBeVisible({
    timeout: 30_000,
  })
  expect(await editPlotVisible(page)).toBe(true)
  expect(page.url()).toBe(link)

  await expect(page.getByText('Opening the edit session…')).toBeHidden({
    timeout: 60_000,
  })
  expect(await editPlotVisible(page)).toBe(true)
  await expect(page.getByRole('button', { name: /^Table$/ })).toHaveClass(
    /v-btn--active/
  )
  const params = new URL(page.url()).searchParams
  const linked = new URL(link).searchParams
  expect(params.get('m')).toBe('e')
  expect(params.get('tab')).toBe('t')
  expect(params.get('z')).toBe(linked.get('z'))
})
