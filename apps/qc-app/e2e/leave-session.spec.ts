/**
 * Leaving an edit session. One dialog, one decision function, three cases:
 *   - unsaved edits: save, discard, or stay
 *   - a session with nothing in it: keep it, or delete it from the server
 *   - everything saved: a notice that the session stays in progress
 * plus the exits that all run it: the footer Close, the Home logo, the
 * workspace switch (through the router guard), Log out, and the row Edit
 * button on another datastream. Viewing committed history leaves silently.
 */

import { expect, test, type Page } from '@playwright/test'
import { installMocks, type MockQcSession } from './support/mocks'
import {
  gotoHome,
  openOp,
  setupEditView,
  waitForEditorReady,
} from './support/app'
import { expectHistoryContains, selectAllPoints } from './support/ops'
import { DATASTREAM_ID_B } from './support/fixtures'

const leaveDialog = (page: Page) => page.getByTestId('leave-session-dialog')
const editPanel = (page: Page) => page.getByTestId('edit-target-panel')

const inProgress = (sessions: MockQcSession[]) =>
  sessions.find((s) => s.status === 'in_progress')

async function applyChangeValues(page: Page) {
  await selectAllPoints(page)
  await openOp(page, 'changeValues')
  await page.getByLabel('Value').fill('1')
  await page.getByRole('button', { name: 'Apply' }).click()
  await expectHistoryContains(page, 'Change Values')
}

async function goToSelect(page: Page) {
  await page.getByTestId('nav-rail-item-select').click()
  await expect(page.getByTestId('datastreams-table')).toBeVisible({
    timeout: 30_000,
  })
}

/** The editor is closed: the Select view is showing with nothing being edited. */
async function expectClosed(page: Page) {
  await expect(page.getByTestId('datastreams-table')).toBeVisible({
    timeout: 30_000,
  })
  await expect(editPanel(page)).toHaveCount(0)
  await expect(page.getByTestId('nav-rail-item-edit')).toHaveAttribute(
    'aria-disabled',
    'true'
  )
}

test.describe('leaving a session', () => {
  let sessions: MockQcSession[]

  test.beforeEach(async ({ page }) => {
    test.slow()
    sessions = []
    await installMocks(page, {
      qcHistories: true,
      qcSessionState: sessions,
    })
    await setupEditView(page)
  })

  test('an untouched session offers keep or discard, and Cancel stays', async ({
    page,
  }) => {
    await page.getByTestId('exit-close-btn').click()
    await expect(leaveDialog(page)).toContainText('This session has no edits')

    await page.getByTestId('leave-cancel-btn').click()
    await expect(leaveDialog(page)).toHaveCount(0)
    await waitForEditorReady(page)
    expect(inProgress(sessions)).toBeDefined()

    await page.getByTestId('exit-close-btn').click()
    await page.getByTestId('leave-keep-btn').click()

    await expectClosed(page)
    expect(inProgress(sessions)).toBeDefined()
  })

  test('discarding an untouched session deletes it from the server', async ({
    page,
  }) => {
    const sessionId = inProgress(sessions)!.id

    await page.getByTestId('exit-close-btn').click()
    await page.getByTestId('leave-discard-session-btn').click()

    await expect(page.getByText('Session discarded.')).toBeVisible()
    await expectClosed(page)
    expect(sessions.some((s) => s.id === sessionId)).toBe(false)
  })

  test('unsaved edits can be saved on the way out', async ({ page }) => {
    await applyChangeValues(page)

    await page.getByTestId('exit-close-btn').click()
    await expect(leaveDialog(page)).toContainText('Unsaved edits')
    await page.getByTestId('leave-save-btn').click()

    await expectClosed(page)
    expect(inProgress(sessions)!.operations.map((o) => o.operationType)).toContain(
      'CHANGE_VALUES'
    )
  })

  test('discarding the edits asks about the now empty session', async ({
    page,
  }) => {
    await applyChangeValues(page)

    await page.getByTestId('exit-close-btn').click()
    await page.getByTestId('leave-discard-edits-btn').click()

    // Nothing was ever saved, so the session is empty now.
    await expect(leaveDialog(page)).toContainText('This session has no edits')
    await page.getByTestId('leave-keep-btn').click()

    await expectClosed(page)
    expect(inProgress(sessions)!.operations).toHaveLength(0)
  })

  test('a fully saved session only confirms', async ({ page }) => {
    await applyChangeValues(page)
    await page.getByTestId('exit-save-btn').click()
    await expect(page.getByText('Draft saved.')).toBeVisible()

    await page.getByTestId('exit-close-btn').click()
    await expect(leaveDialog(page)).toContainText('Close this session?')
    await expect(leaveDialog(page)).toContainText('stays in progress')
    await page.getByTestId('leave-close-btn').click()

    await expectClosed(page)
    expect(inProgress(sessions)!.operations.length).toBeGreaterThan(0)
  })

  test('viewing committed history closes without a question', async ({
    page,
  }) => {
    await page.getByTestId('session-header-qcs-e2e-1').click()
    await expect(page.getByTestId('session-return-current')).toBeVisible()

    await page.getByTestId('exit-close-btn').click()

    await expect(leaveDialog(page)).toHaveCount(0)
    await expectClosed(page)
  })

  test('the Home logo asks first', async ({ page }) => {
    await page.getByRole('button', { name: 'Home' }).click()
    await expect(leaveDialog(page)).toBeVisible()

    await page.getByTestId('leave-cancel-btn').click()
    await waitForEditorReady(page)

    await page.getByRole('button', { name: 'Home' }).click()
    await page.getByTestId('leave-keep-btn').click()

    // Home reloads the app, and the session is no longer the one to resume.
    await expectClosed(page)
    expect(inProgress(sessions)).toBeDefined()
  })

  test('the workspace switch asks through the router guard', async ({
    page,
  }) => {
    await page.getByTestId('nav-rail-workspaces').click()
    await expect(leaveDialog(page)).toBeVisible()

    // Cancelling cancels the navigation too.
    await page.getByTestId('leave-cancel-btn').click()
    await waitForEditorReady(page)
    await expect(page.getByTestId('datastreams-table')).toHaveCount(0)

    await page.getByTestId('nav-rail-workspaces').click()
    await page.getByTestId('leave-keep-btn').click()

    await expect(page.getByTestId('workspace-current-hint')).toBeVisible({
      timeout: 30_000,
    })
  })

  test('logging out asks first', async ({ page }) => {
    await page.getByTestId('nav-rail-logout').click()
    await expect(leaveDialog(page)).toBeVisible()

    await page.getByTestId('leave-cancel-btn').click()
    await waitForEditorReady(page)
    expect(inProgress(sessions)).toBeDefined()
  })

  test('editing another datastream asks before anything is created', async ({
    page,
  }) => {
    await goToSelect(page)

    // Datastream B has no managed datastream yet, so Edit would create one.
    // Cancelling must leave nothing behind on the server.
    await page.getByTestId(`edit-datastream-${DATASTREAM_ID_B}`).click()
    await expect(leaveDialog(page)).toBeVisible()
    await page.getByTestId('leave-cancel-btn').click()

    await expect(page.getByTestId('create-confirm')).toHaveCount(0)
    // The original session is still the one being edited.
    await expect(editPanel(page)).toContainText('Streamflow Datastream (QC)')
  })

  test('answering the question opens the create step', async ({ page }) => {
    await goToSelect(page)

    await page.getByTestId(`edit-datastream-${DATASTREAM_ID_B}`).click()
    await page.getByTestId('leave-keep-btn').click()

    await expect(page.getByTestId('create-confirm')).toBeVisible()
    // The session was left the moment the user said so, not at the end.
    await expect(editPanel(page)).toHaveCount(0)
    expect(inProgress(sessions)).toBeDefined()
  })
})
