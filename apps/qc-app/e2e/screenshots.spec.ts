/**
 * Documentation screenshot capture.
 *
 * Drives the mocked-backend e2e harness through every notable UI state
 * (workspaces, home/select, plot, edit view, each filter/edit/add
 * panel, edit history, submit dialog) and writes one PNG per state to
 * `docs/images/`.
 *
 * Skipped by default so a normal `npx playwright test` run doesn't
 * touch the on-disk PNGs (otherwise every CI / local run produces a
 * noisy diff of regenerated screenshots). Set `CAPTURE_SCREENSHOTS=1`
 * to opt in:
 *
 *     CAPTURE_SCREENSHOTS=1 npx playwright test screenshots --project=chromium
 *
 * Most captures use a Locator so each PNG is tightly cropped to the
 * region the doc actually references. The viewport is intentionally
 * tall so operation panels render their full body without internal
 * scroll — the locator screenshot would otherwise clip whatever fell
 * outside the panel's visible area.
 */

import { test, expect, type Page, type Locator } from '@playwright/test'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { installMocks } from './support/mocks'
import {
  gotoHome,
  setupEditView,
  openOp,
  plotFirstDatastream,
  plotDatastreamById,
  waitForHomeReady,
} from './support/app'
import { selectAllPoints } from './support/ops'
import {
  DATASTREAM_ID,
  DATASTREAM_ID_B,
  buildObservations,
  buildTemperatureObservations,
} from './support/fixtures'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const OUT = path.resolve(__dirname, '..', 'docs', 'images')

/**
 * Wait for the Plotly chart in the page (if any) to finish its
 * post-mount layout. `handleNewPlot` runs inside a 200 ms setTimeout
 * in `Plot.vue`'s mount hook, and a ResizeObserver fires a frame
 * later to size the canvas to its container — both happen *after*
 * `setupEditView`'s "Filter Data is visible" gate. Without this
 * extra wait the screenshot captures the initial undersized layout,
 * leaving an empty stripe between the right edge of the plotting
 * area and the v-card edge. We poll `_fullLayout.width` against the
 * gd element's actual `offsetWidth` and bail out (no chart on the
 * page) when the selector doesn't resolve.
 */
async function waitForPlotLayoutSettled(page: Page) {
  await page.waitForFunction(
    () => {
      const gd = document.querySelector('[data-testid="main-plot"]') as
        | (HTMLElement & { _fullLayout?: { width: number } })
        | null
      if (!gd) return true
      // The plot div stays in the DOM behind the Table tab but its
      // offsetWidth collapses to 0 — treat that as settled too.
      if (gd.offsetWidth === 0) return true
      const layout = gd._fullLayout
      if (!layout?.width) return false
      // Allow a few pixels of slop — Plotly rounds.
      return Math.abs(layout.width - gd.offsetWidth) <= 4
    },
    undefined,
    { timeout: 5_000 }
  )
}

async function snapPage(page: Page, name: string) {
  await waitForPlotLayoutSettled(page)
  await page.waitForTimeout(250)
  await page.screenshot({ path: path.join(OUT, name), fullPage: false })
}

async function snapEl(loc: Locator, name: string) {
  await loc.waitFor({ state: 'visible' })
  await waitForPlotLayoutSettled(loc.page())
  await loc.page().waitForTimeout(250)
  await loc.screenshot({ path: path.join(OUT, name) })
}

/**
 * Tall viewport so the aux column fits the tallest operation panel
 * (Fill Gaps with all its sections) without internal scroll. Width is
 * the standard 1440 our specs use elsewhere so chrome metrics stay
 * consistent.
 */
const TALL_VIEWPORT = { width: 1440, height: 1800 }

/** Standard viewport for "overview" shots (login, workspaces, full edit view). */
const STD_VIEWPORT = { width: 1440, height: 900 }

const SHOULD_CAPTURE = process.env.CAPTURE_SCREENSHOTS === '1'

test.describe('docs screenshots', () => {
  test.skip(
    !SHOULD_CAPTURE,
    'Opt-in only — set CAPTURE_SCREENSHOTS=1 to regenerate docs/images/ PNGs.'
  )

  test('login page', async ({ page }) => {
    await page.setViewportSize(STD_VIEWPORT)
    await installMocks(page, { authenticated: false })
    await page.goto('/login')
    const card = page.locator('.login-card')
    await expect(card).toBeVisible({ timeout: 15_000 })
    await snapEl(card, 'login.png')
  })

  test('workspaces picker', async ({ page }) => {
    await page.setViewportSize(STD_VIEWPORT)
    await installMocks(page)
    await page.goto('/workspaces')
    const container = page.locator('.v-container').filter({
      hasText: 'Select a workspace',
    })
    await expect(container).toBeVisible({ timeout: 15_000 })
    await snapEl(container, 'workspaces.png')
  })

  test('home (select view, no datastream plotted)', async ({ page }) => {
    await page.setViewportSize(STD_VIEWPORT)
    await installMocks(page)
    await gotoHome(page)
    await snapPage(page, 'home-select.png')
  })

  test('home (datastream plotted in context)', async ({ page }) => {
    await page.setViewportSize(STD_VIEWPORT)
    await installMocks(page)
    await gotoHome(page)
    await plotFirstDatastream(page)
    await waitForHomeReady(page)
    await snapPage(page, 'home-plotted.png')
  })

  test('edit view (full layout)', async ({ page }) => {
    await page.setViewportSize(STD_VIEWPORT)
    await installMocks(page)
    await setupEditView(page)
    await snapPage(page, 'edit-view.png')
  })

  test('home (two datastreams on independent y-axes)', async ({ page }) => {
    await page.setViewportSize(STD_VIEWPORT)
    await installMocks(page, {
      observationsById: {
        [DATASTREAM_ID]: buildObservations(),
        [DATASTREAM_ID_B]: buildTemperatureObservations(),
      },
    })
    await gotoHome(page)
    await plotDatastreamById(page, DATASTREAM_ID)
    await plotDatastreamById(page, DATASTREAM_ID_B)
    // Plot redraws asynchronously after the second add; give Plotly
    // a beat to layout both Y axes + chips before we capture.
    await page.waitForTimeout(800)
    await snapPage(page, 'home-multi-datastreams.png')
  })

  test('edit view (two datastreams, secondary axis visible)', async ({
    page,
  }) => {
    await page.setViewportSize(STD_VIEWPORT)
    await installMocks(page, {
      observationsById: {
        [DATASTREAM_ID]: buildObservations(),
        [DATASTREAM_ID_B]: buildTemperatureObservations(),
      },
    })
    await gotoHome(page)
    await plotDatastreamById(page, DATASTREAM_ID)
    await plotDatastreamById(page, DATASTREAM_ID_B)
    await page.getByTestId('nav-rail-item-edit').click()
    await expect(page.getByText('Filter Data')).toBeVisible()
    await page.waitForTimeout(800)
    await snapPage(page, 'edit-view-multi.png')
  })

  test('data points mode menu (auto, threshold visible)', async ({ page }) => {
    await page.setViewportSize(STD_VIEWPORT)
    await installMocks(page)
    await setupEditView(page)
    await page.getByTestId('tooltips-mode-btn').click()
    const menu = page.getByTestId('tooltips-mode-menu')
    await expect(menu).toBeVisible({ timeout: 5_000 })
    await snapEl(menu, 'data-points-menu.png')
  })

  test('table view (observations editable rows)', async ({ page }) => {
    await page.setViewportSize(STD_VIEWPORT)
    await installMocks(page)
    await setupEditView(page)
    // Plot tab is the default; switch to Table.
    await page.getByRole('button', { name: /^Table$/ }).click()
    // Give the virtualised table a beat to render its first slice.
    await page.waitForTimeout(500)
    await snapPage(page, 'table-view.png')
  })

  test('plot help menu (open)', async ({ page }) => {
    await page.setViewportSize(STD_VIEWPORT)
    await installMocks(page)
    await setupEditView(page)
    // The help button is the only `?` icon in the toolbar.
    await page.getByRole('button', { name: /plot controls/i }).click()
    const menu = page.locator('.plot-help').first()
    await expect(menu).toBeVisible({ timeout: 5_000 })
    await snapEl(menu, 'plot-help-menu.png')
  })

  test('plotted datastreams list (multiple rows)', async ({ page }) => {
    await page.setViewportSize(STD_VIEWPORT)
    await installMocks(page, {
      observationsById: {
        [DATASTREAM_ID]: buildObservations(),
        [DATASTREAM_ID_B]: buildTemperatureObservations(),
      },
    })
    await gotoHome(page)
    await plotDatastreamById(page, DATASTREAM_ID)
    await plotDatastreamById(page, DATASTREAM_ID_B)
    await page.waitForTimeout(600)
    const list = page.locator('.select-view__plotted').first()
    await snapEl(list, 'plotted-datastreams-list.png')
  })

  const filterOps = [
    'valueThreshold',
    'datetimeRange',
    'change',
    'rateOfChange',
    'gaps',
    'persistence',
  ] as const

  for (const id of filterOps) {
    test(`filter panel — ${id}`, async ({ page }) => {
      await page.setViewportSize(TALL_VIEWPORT)
      await installMocks(page)
      await setupEditView(page)
      await openOp(page, id)
      const panel = page.getByTestId(`operation-panel-${id}`)
      await snapEl(panel, `panel-${id}.png`)
    })
  }

  const editOps = [
    'driftCorrection',
    'interpolate',
    'changeValues',
    'shiftDatetimes',
    'deletePoints',
  ] as const

  for (const id of editOps) {
    test(`edit panel — ${id}`, async ({ page }) => {
      await page.setViewportSize(TALL_VIEWPORT)
      await installMocks(page)
      await setupEditView(page)
      // Edit ops require a selection; seed one with a wide value
      // threshold so the panel renders its real body.
      await selectAllPoints(page)
      await openOp(page, id)
      const panel = page.getByTestId(`operation-panel-${id}`)
      await snapEl(panel, `panel-${id}.png`)
    })
  }

  test('date range mask (filter panel, mask enabled)', async ({ page }) => {
    await page.setViewportSize(TALL_VIEWPORT)
    await installMocks(page)
    await setupEditView(page)
    await openOp(page, 'valueThreshold')
    const panel = page.getByTestId('operation-panel-valueThreshold')
    await panel.getByRole('button', { name: /enable date range mask/i }).click()
    // Let RangeStager wire up its bounds + plot overlay before capture.
    await page.waitForTimeout(400)
    await snapEl(panel, 'panel-date-range-mask.png')
  })

  test('add panel — qualifyingComments', async ({ page }) => {
    await page.setViewportSize(TALL_VIEWPORT)
    await installMocks(page)
    await setupEditView(page)
    await selectAllPoints(page)
    await openOp(page, 'qualifyingComments')
    const panel = page.getByTestId('operation-panel-qualifyingComments')
    await snapEl(panel, 'panel-qualifyingComments.png')
  })

  test('add panel — addPoints', async ({ page }) => {
    await page.setViewportSize(TALL_VIEWPORT)
    await installMocks(page)
    await setupEditView(page)
    await openOp(page, 'addPoints')
    const panel = page.getByTestId('operation-panel-addPoints')
    await snapEl(panel, 'panel-addPoints.png')
  })

  test('add panel — fillGaps', async ({ page }) => {
    await page.setViewportSize(TALL_VIEWPORT)
    await installMocks(page)
    await setupEditView(page)
    await openOp(page, 'fillGaps')
    const panel = page.getByTestId('operation-panel-fillGaps')
    await snapEl(panel, 'panel-fillGaps.png')
  })

  test('edit history with entries', async ({ page }) => {
    await page.setViewportSize(STD_VIEWPORT)
    await installMocks(page)
    await setupEditView(page)
    await selectAllPoints(page)
    await openOp(page, 'changeValues')
    const opPanel = page.getByTestId('operation-panel-changeValues')
    await opPanel.getByLabel('Value').fill('1')
    await opPanel.getByRole('button', { name: /^apply$/i }).click()
    // Wait for the history row to appear before capturing.
    await expect(
      page.locator('[data-testid^="history-item-"]').first()
    ).toBeVisible({ timeout: 10_000 })
    const history = page.locator('.edit-history').first()
    await snapEl(history, 'edit-history.png')
  })

  test('submit confirmation dialog', async ({ page }) => {
    await page.setViewportSize(STD_VIEWPORT)
    await installMocks(page)
    await setupEditView(page)
    await selectAllPoints(page)
    await openOp(page, 'changeValues')
    const opPanel = page.getByTestId('operation-panel-changeValues')
    await opPanel.getByLabel('Value').fill('1')
    await opPanel.getByRole('button', { name: /^apply$/i }).click()
    await page.getByTestId('exit-save-btn').click()
    const dialog = page
      .locator('.v-overlay__content')
      .filter({ hasText: 'Submit QC observations?' })
    await expect(dialog).toBeVisible({ timeout: 5_000 })
    await snapEl(dialog, 'submit-dialog.png')
  })
})
