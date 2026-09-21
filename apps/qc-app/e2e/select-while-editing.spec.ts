/**
 * The Select view while an edit session is open:
 *   - the Select rail item keeps the session, the working copy and unsaved
 *     edits, and asks nothing
 *   - the edit panel says what is being edited and leads back
 *   - the round trip keeps the plot's zoom and the editor's staged range
 *   - checkboxes add context around the edit target, which stays plotted
 *   - the share URL keeps `ed` without `m`, and a reload restores Select
 *   - the row Edit button on the datastream being edited returns to the editor
 */

import { expect, test, type Page } from '@playwright/test'
import { installMocks } from './support/mocks'
import {
  gotoHome,
  openOp,
  setupEditView,
  startSessionFromRow,
  waitForEditorReady,
} from './support/app'
import { expectHistoryContains, selectAllPoints } from './support/ops'
import {
  DATASTREAM_ID,
  DATASTREAM_ID_B,
  MANAGED_DATASTREAM_ID,
  buildObservations,
  buildTemperatureObservations,
} from './support/fixtures'

const editPanel = (page: Page) => page.getByTestId('edit-target-panel')
/** The Select view's right column. The editor stays mounted behind it, so its
 *  own plotted list carries the same test ids. */
const sidePanel = (page: Page) => page.getByTestId('select-side-panel')

async function goToSelect(page: Page) {
  await page.getByTestId('nav-rail-item-select').click()
  await expect(page.getByTestId('datastreams-table')).toBeVisible({
    timeout: 30_000,
  })
}

async function goToEditor(page: Page) {
  await page.getByTestId('nav-rail-item-edit').click()
  await waitForEditorReady(page)
}

/** The live X range of the main plot, as `[loMs, hiMs]`. */
async function plotXRange(page: Page): Promise<[number, number]> {
  return page.evaluate(async () => {
    const wait = (ms: number) => new Promise((r) => setTimeout(r, ms))
    const start = Date.now()
    while (Date.now() - start < 10_000) {
      const gd = document.querySelector('[data-testid="main-plot"]') as
        | (HTMLElement & {
            _fullLayout?: {
              xaxis?: { range?: [number | string, number | string] }
            }
          })
        | null
      const range = gd?._fullLayout?.xaxis?.range
      if (range) {
        const toMs = (v: number | string) =>
          typeof v === 'string' ? Date.parse(v) : v
        return [toMs(range[0]), toMs(range[1])] as [number, number]
      }
      await wait(100)
    }
    throw new Error('plot never reported an x range')
  })
}

/** The staged filter band's x span on the live plot, or null when absent. */
async function stageBandSpan(page: Page): Promise<string | null> {
  return page.evaluate(() => {
    const gd = document.querySelector('[data-testid="main-plot"]') as
      | (HTMLElement & {
          layout?: { shapes?: { name?: string; x0?: unknown; x1?: unknown }[] }
        })
      | null
    const shape = (gd?.layout?.shapes ?? []).find((s) => s.name === 'stage')
    return shape ? `${String(shape.x0)}..${String(shape.x1)}` : null
  })
}

/** Ids of the traces currently drawn on the main plot. */
async function plottedTraceIds(page: Page): Promise<string[]> {
  return page.evaluate(() => {
    const gd = document.querySelector('[data-testid="main-plot"]') as
      | (HTMLElement & { data?: { id?: string }[] })
      | null
    return (gd?.data ?? [])
      .map((t) => t.id)
      .filter((id): id is string => !!id)
  })
}

test.describe('Select while editing', () => {
  test.beforeEach(async ({ page }) => {
    test.slow()
    await installMocks(page, {
      qcHistories: true,
      observationsById: {
        [DATASTREAM_ID]: buildObservations(),
        [DATASTREAM_ID_B]: buildTemperatureObservations(),
      },
    })
  })

  test('keeps unsaved edits and leads back to the editor', async ({ page }) => {
    await setupEditView(page)
    await selectAllPoints(page)
    await openOp(page, 'changeValues')
    await page.getByLabel('Value').fill('1')
    await page.getByRole('button', { name: 'Apply' }).click()
    await expectHistoryContains(page, 'Change Values')

    await goToSelect(page)

    // No prompt: nothing is being left behind.
    await expect(
      page.getByRole('dialog').filter({ hasText: 'Unsaved edits' })
    ).toHaveCount(0)
    await expect(editPanel(page)).toBeVisible()
    await expect(editPanel(page)).toContainText('Streamflow Datastream (QC)')
    await expect(page.getByTestId('edit-target-unsaved')).toContainText(
      'unsaved edit'
    )

    // The edit target is still drawn, so the user sees what they changed.
    expect(await plottedTraceIds(page)).toContain(MANAGED_DATASTREAM_ID)

    await page.getByTestId('open-editor-btn').click()
    await waitForEditorReady(page)
    await expectHistoryContains(page, 'Change Values')
  })

  test('keeps the plot zoom and a staged range across the round trip', async ({
    page,
  }) => {
    await setupEditView(page)
    // Staging a filter window draws an editable band over the plot.
    await openOp(page, 'persistence')
    await page.getByTestId('filter-range-enable-btn').click()
    await expect(page.getByTestId('filter-range-panel')).toBeVisible()
    const fromField = page
      .getByTestId('filter-range-panel')
      .getByPlaceholder('MM/DD/YYYY')
      .first()
    const stagedFrom = await fromField.inputValue()
    const stagedBand = await stageBandSpan(page)
    expect(stagedBand).not.toBeNull()

    const before = await plotXRange(page)

    await goToSelect(page)
    await goToEditor(page)

    const after = await plotXRange(page)
    expect(after[0]).toBeCloseTo(before[0], -4)
    expect(after[1]).toBeCloseTo(before[1], -4)

    expect(await stageBandSpan(page)).toBe(stagedBand)
    await expect(page.getByTestId('filter-range-panel')).toBeVisible()
    await expect(fromField).toHaveValue(stagedFrom)
  })

  test('plots context around the edit target from the table', async ({
    page,
  }) => {
    await setupEditView(page)
    await goToSelect(page)

    await page.getByTestId(`plot-checkbox-${DATASTREAM_ID_B}`).click()
    await page
      .getByTestId('data-loading-indicator')
      .waitFor({ state: 'hidden', timeout: 30_000 })

    const ids = await plottedTraceIds(page)
    expect(ids).toContain(DATASTREAM_ID_B)
    expect(ids).toContain(MANAGED_DATASTREAM_ID)

    // The edit target is pinned in the plotted list. Its source is drawn as
    // context, which the Context menu switches, so it gets no row.
    await expect(
      sidePanel(page).getByTestId(`plotted-item-${MANAGED_DATASTREAM_ID}`)
    ).toBeVisible()
    await expect(
      sidePanel(page).getByTestId(`plotted-item-${DATASTREAM_ID}`)
    ).toHaveCount(0)
  })

  test('keeps ed in the share URL and restores Select on reload', async ({
    page,
  }) => {
    await setupEditView(page)
    await goToSelect(page)

    const params = new URLSearchParams(
      await page.evaluate(() => window.location.search)
    )
    expect(params.get('ed')).toBe(MANAGED_DATASTREAM_ID)
    expect(params.has('m')).toBe(false)

    await page.reload()
    await expect(page.getByTestId('datastreams-table')).toBeVisible({
      timeout: 30_000,
    })
    await expect(editPanel(page)).toBeVisible({ timeout: 30_000 })
    await expect(page.getByTestId('nav-rail-item-edit')).toHaveAttribute(
      'aria-disabled',
      'false'
    )
  })

  test('the edited row offers Close, which ends the session', async ({
    page,
  }) => {
    await gotoHome(page)
    await startSessionFromRow(page)
    await goToSelect(page)

    await expect(page.getByTestId(`edit-datastream-${DATASTREAM_ID}`)).toHaveCount(0)
    await expect(page.getByTestId('editing-chip')).toBeVisible()
    await page.getByTestId(`close-datastream-${DATASTREAM_ID}`).click()
    // The fresh session holds no edits, so leaving asks what to do with it.
    await page.getByTestId('leave-keep-btn').click()
    await expect(page.getByTestId('editing-chip')).toHaveCount(0)
    await expect(page.getByTestId(`edit-datastream-${DATASTREAM_ID}`)).toBeVisible()
  })

  test('plotting the raw source keeps the grey context beside it', async ({
    page,
  }) => {
    await gotoHome(page)
    await startSessionFromRow(page)
    await goToSelect(page)

    await page.getByTestId(`plot-checkbox-${DATASTREAM_ID}`).click()
    await expect(page.getByTestId('plot-source-dialog')).toBeVisible()
    // The edit target is already on the plot, so it is not offered.
    await expect(
      page.getByTestId(`plot-option-editing-${MANAGED_DATASTREAM_ID}`)
    ).toBeVisible()
    await page.getByTestId(`plot-option-${DATASTREAM_ID}`).locator('input').check()
    await page.getByTestId('plot-source-apply').click()

    await expect
      .poll(() => plottedTraceIds(page))
      .toEqual(expect.arrayContaining([DATASTREAM_ID, `ctx:${DATASTREAM_ID}`]))
    // The plotted source is an ordinary row; the grey context gets none.
    await expect(
      sidePanel(page).getByTestId(`plotted-item-${DATASTREAM_ID}`)
    ).toBeVisible()
  })

  test('Clear plot closes the edited datastream and unplots everything', async ({
    page,
  }) => {
    await gotoHome(page)
    await startSessionFromRow(page)
    await goToSelect(page)
    await page.getByTestId(`plot-checkbox-${DATASTREAM_ID_B}`).click()
    await expect
      .poll(() => plottedTraceIds(page))
      .toEqual(expect.arrayContaining([DATASTREAM_ID_B]))

    await page.getByTestId('clear-plot-btn').click()
    // The fresh session holds no edits, so closing asks what to do with it.
    await page.getByTestId('leave-keep-btn').click()

    await expect(page.getByTestId('editing-chip')).toHaveCount(0)
    await expect(page.getByTestId('clear-plot-btn')).toHaveCount(0)
    await expect(page.getByText('No datastream plotted')).toBeVisible()
  })
})
