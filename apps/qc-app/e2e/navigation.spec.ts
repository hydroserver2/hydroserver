/**
 * Workspace picker + navigation rail flows:
 *   - fresh browser redirects to /workspaces
 *   - picking a workspace navigates to Home
 *   - the nav-rail workspace-switch button offers to revisit the picker
 *   - the edit rail item is enabled only while editing
 *   - leaving Edit with edits not saved to the session asks first
 */

import { expect, test, type Page } from '@playwright/test'
import { installMocks, type MockQcSession } from './support/mocks'
import {
  gotoHome,
  openOp,
  plotDatastreamById,
  setupEditView,
  startSessionFromRow,
} from './support/app'
import { expectHistoryContains, selectAllPoints } from './support/ops'
import { DATASTREAM_ID_B, WORKSPACE_ID } from './support/fixtures'

async function applyChangeValues(page: Page) {
  await selectAllPoints(page)
  await openOp(page, 'changeValues')
  await page.getByLabel('Value').fill('1')
  await page.getByRole('button', { name: 'Apply' }).click()
  await expectHistoryContains(page, 'Change Values')
}

function exitDialog(page: Page) {
  return page.getByRole('dialog').filter({ hasText: 'Unsaved edits' })
}

test.describe('navigation', () => {
  test.beforeEach(async ({ page }) => {
    await installMocks(page, { qcHistories: true })
  })

  test('fresh browser redirects to the workspace picker', async ({ page }) => {
    await page.goto('/')
    // Either still /workspaces, or the picker's select button is visible.
    await expect(
      page
        .getByRole('listitem')
        .filter({ hasText: 'E2E Test Workspace' })
        .getByRole('button', { name: /^Select$/ })
    ).toBeVisible({ timeout: 15_000 })
  })

  test('picking a workspace lands the user on Home', async ({ page }) => {
    // Don't use `gotoHome` here — it pre-seeds localStorage and skips
    // the picker. We want to exercise the actual pick flow.
    await page.goto('/')
    const pickButton = page
      .getByRole('listitem')
      .filter({ hasText: 'E2E Test Workspace' })
      .getByRole('button', { name: /^Select$/ })
    await expect(pickButton).toBeVisible({ timeout: 30_000 })
    // `force: true` keeps Firefox from stalling on Vuetify's v-list-item
    // + inner button actionability check (the row itself also carries
    // a @click handler, which sometimes confuses the stability poll).
    await pickButton.click({ force: true })
    await expect(page.getByTestId('datastreams-table')).toBeVisible({
      timeout: 30_000,
    })
  })

  test('the current workspace offers Continue back to Home', async ({
    page,
  }) => {
    await gotoHome(page)
    await page.getByTestId('nav-rail-workspaces').click()
    await expect(page.getByTestId('workspace-current-hint')).toContainText(
      'E2E Test Workspace'
    )
    const button = page.getByTestId(`workspace-pick-${WORKSPACE_ID}`)
    await expect(button).toHaveText(/Continue/)
    await button.click({ force: true })
    await expect(page.getByTestId('datastreams-table')).toBeVisible({
      timeout: 30_000,
    })
  })

  test('Edit rail item is disabled outside the editor', async ({ page }) => {
    test.slow()
    await gotoHome(page)
    const editRail = page.getByTestId('nav-rail-item-edit')
    await expect(editRail).toHaveAttribute('aria-disabled', 'true')
    // Plotting never picks an edit target.
    await plotDatastreamById(page, DATASTREAM_ID_B)
    await expect(editRail).toHaveAttribute('aria-disabled', 'true')
    await startSessionFromRow(page)
    await expect(editRail).toHaveAttribute('aria-disabled', 'false')
  })
})

test.describe('navigation: leaving a QC session', () => {
  let submissions: Array<{ mode: string | null; body: any }>
  let sessions: MockQcSession[]

  test.beforeEach(async ({ page }) => {
    // Entering through the row Edit flow and starting a session is slow
    // enough to outrun the default budget when these run in parallel.
    test.slow()
    submissions = []
    sessions = []
    await installMocks(page, {
      qcHistories: true,
      submissions,
      qcSessionState: sessions,
    })
    await setupEditView(page)
  })

  test('Save & continue saves the draft without posting observations', async ({
    page,
  }) => {
    await applyChangeValues(page)

    await page.getByTestId('nav-rail-item-select').click()
    const dialog = exitDialog(page)
    await expect(dialog).toBeVisible()
    await dialog.getByRole('button', { name: /save & continue/i }).click()

    await expect(page.getByTestId('datastreams-table')).toBeVisible({
      timeout: 30_000,
    })
    const session = sessions.find((s) => s.status === 'in_progress')
    expect(session!.operations.map((o) => o.operationType)).toContain(
      'CHANGE_VALUES'
    )
    expect(submissions).toHaveLength(0)
  })

  test('Discard continues without saving', async ({ page }) => {
    await applyChangeValues(page)

    await page.getByTestId('nav-rail-item-select').click()
    const dialog = exitDialog(page)
    await expect(dialog).toBeVisible()
    await dialog.getByRole('button', { name: /discard/i }).click()

    await expect(page.getByTestId('datastreams-table')).toBeVisible({
      timeout: 30_000,
    })
    const session = sessions.find((s) => s.status === 'in_progress')
    expect(session!.operations).toHaveLength(0)
    expect(submissions).toHaveLength(0)
  })

  test('saved edits leave without asking', async ({ page }) => {
    await applyChangeValues(page)
    await page.getByTestId('exit-save-btn').click()
    await expect(page.getByText('Draft saved.')).toBeVisible()

    await page.getByTestId('nav-rail-item-select').click()
    await expect(page.getByTestId('datastreams-table')).toBeVisible({
      timeout: 30_000,
    })
    await expect(exitDialog(page)).toHaveCount(0)
  })
})
