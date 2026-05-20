/**
 * Documentation screenshot capture.
 *
 * Drives the mocked-backend e2e harness through every notable UI state
 * (workspaces, home/select, plot, edit view, each filter/edit/add
 * panel, edit history, submit dialog) and writes one PNG per state to
 * `docs/images/`. Re-run when the UI changes substantively so the
 * USER_GUIDE.md figures stay in sync.
 *
 * Run with: `npx playwright test screenshots --project=chromium`.
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
  waitForHomeReady,
} from './support/app'
import { selectAllPoints } from './support/ops'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const OUT = path.resolve(__dirname, '..', 'docs', 'images')

async function snapPage(page: Page, name: string) {
  await page.waitForTimeout(250)
  await page.screenshot({ path: path.join(OUT, name), fullPage: false })
}

async function snapEl(loc: Locator, name: string) {
  await loc.waitFor({ state: 'visible' })
  // Small settle to let Vuetify finish transitions before capture.
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

test.describe('docs screenshots', () => {
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
    await panel
      .getByRole('button', { name: /enable date range mask/i })
      .click()
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
