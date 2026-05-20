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
 */

import { test, expect, type Page } from '@playwright/test'
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

async function snap(page: Page, name: string) {
  await page.waitForTimeout(250)
  await page.screenshot({
    path: path.join(OUT, name),
    fullPage: false,
  })
}

test.describe('docs screenshots', () => {
  test.use({ viewport: { width: 1440, height: 900 } })

  test('login page', async ({ page }) => {
    await installMocks(page, { authenticated: false })
    await page.goto('/login')
    await expect(page.getByRole('button', { name: /log in/i }).first()).toBeVisible({
      timeout: 15_000,
    })
    await snap(page, 'login.png')
  })

  test('workspaces picker', async ({ page }) => {
    await installMocks(page)
    await page.goto('/workspaces')
    await expect(page.getByText('E2E Test Workspace')).toBeVisible({
      timeout: 15_000,
    })
    await snap(page, 'workspaces.png')
  })

  test('home (select view, no datastream plotted)', async ({ page }) => {
    await installMocks(page)
    await gotoHome(page)
    await snap(page, 'home-select.png')
  })

  test('home (datastream plotted in context)', async ({ page }) => {
    await installMocks(page)
    await gotoHome(page)
    await plotFirstDatastream(page)
    await waitForHomeReady(page)
    await snap(page, 'home-plotted.png')
  })

  test('edit view (full layout)', async ({ page }) => {
    await installMocks(page)
    await setupEditView(page)
    await snap(page, 'edit-view.png')
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
      await installMocks(page)
      await setupEditView(page)
      await openOp(page, id)
      await page.waitForTimeout(400)
      await snap(page, `panel-${id}.png`)
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
      await installMocks(page)
      await setupEditView(page)
      // Edit ops require a selection; seed one with a wide value
      // threshold so the panel renders its real body.
      await selectAllPoints(page)
      await openOp(page, id)
      await page.waitForTimeout(400)
      await snap(page, `panel-${id}.png`)
    })
  }

  test('add panel — qualifyingComments', async ({ page }) => {
    await installMocks(page)
    await setupEditView(page)
    await selectAllPoints(page)
    await openOp(page, 'qualifyingComments')
    await page.waitForTimeout(400)
    await snap(page, 'panel-qualifyingComments.png')
  })

  test('add panel — addPoints', async ({ page }) => {
    await installMocks(page)
    await setupEditView(page)
    await openOp(page, 'addPoints')
    await page.waitForTimeout(400)
    await snap(page, 'panel-addPoints.png')
  })

  test('add panel — fillGaps', async ({ page }) => {
    await installMocks(page)
    await setupEditView(page)
    await openOp(page, 'fillGaps')
    await page.waitForTimeout(400)
    await snap(page, 'panel-fillGaps.png')
  })

  test('edit history with entries', async ({ page }) => {
    await installMocks(page)
    await setupEditView(page)
    await selectAllPoints(page)
    await openOp(page, 'changeValues')
    const panel = page.getByTestId('operation-panel-changeValues')
    await panel.getByLabel('Value').fill('1')
    await panel.getByRole('button', { name: /^apply$/i }).click()
    await page.waitForTimeout(800)
    await snap(page, 'edit-history.png')
  })

  test('submit confirmation dialog', async ({ page }) => {
    await installMocks(page)
    await setupEditView(page)
    await selectAllPoints(page)
    await openOp(page, 'changeValues')
    const panel = page.getByTestId('operation-panel-changeValues')
    await panel.getByLabel('Value').fill('1')
    await panel.getByRole('button', { name: /^apply$/i }).click()
    await page.waitForTimeout(600)
    await page.getByTestId('exit-save-btn').click()
    await expect(page.getByText('Submit QC observations?')).toBeVisible({
      timeout: 5_000,
    })
    await snap(page, 'submit-dialog.png')
  })
})
