/**
 * Hovering a data table cell draws the edit affordance only when the cell
 * can be edited. While a committed session is on screen its cells are
 * read-only. Switching back to the plot keeps the selection.
 */

import { expect, test } from '@playwright/test'
import { installMocks } from './support/mocks'
import { COMMITTED_SESSION_ID } from './support/fixtures'
import { openOp, setupEditView } from './support/app'
import { selectAllPoints } from './support/ops'

test('a read-only cell does not look editable on hover', async ({ page }) => {
  await installMocks(page, { qcHistories: true })
  await setupEditView(page)
  await page.getByTestId(`session-header-${COMMITTED_SESSION_ID}`).click()
  await expect(page.getByTestId('session-return-current')).toBeVisible()
  await page.getByRole('button', { name: 'Table' }).click()

  const cell = page.locator('.editable-cell__display--readonly').first()
  await cell.hover()

  await expect(cell).toHaveCSS('border-top-color', 'rgba(0, 0, 0, 0)')
  await expect(cell).toHaveCSS('background-color', 'rgba(0, 0, 0, 0)')
})

test('an editable cell shows the edit affordance on hover', async ({ page }) => {
  await installMocks(page, { qcHistories: true })
  await setupEditView(page)
  await page.getByRole('button', { name: 'Table' }).click()

  const cell = page
    .locator('.editable-cell__display:not(.editable-cell__display--readonly)')
    .first()
  await cell.hover()

  await expect(cell).not.toHaveCSS('border-top-color', 'rgba(0, 0, 0, 0)')
})

test('an operation run from the drawer drops staged table edits', async ({
  page,
}) => {
  await installMocks(page, { qcHistories: true })
  await setupEditView(page)
  await page.getByRole('button', { name: 'Table' }).click()

  // Each row renders its datetime cell, then its value cell.
  await page
    .locator('.editable-cell__display:not(.editable-cell__display--readonly)')
    .nth(1)
    .click()
  const input = page.locator('.editable-cell__input')
  await input.fill('12345')
  await input.press('Enter')
  await expect(page.getByText('1 unsaved')).toBeVisible()

  await openOp(page, 'addPoints')
  const panel = page.getByTestId('operation-panel-addPoints')
  await panel.getByRole('spinbutton', { name: 'Value' }).fill('5')
  await panel.getByRole('button', { name: /^Add \d+ point/ }).click()

  await expect(
    page.getByText('1 unsaved table edit was discarded because the data changed.')
  ).toBeVisible()
  await expect(page.getByText(/\d+ unsaved/)).toHaveCount(0)
})

test('the selection is still shown after a trip to the table', async ({
  page,
}) => {
  await installMocks(page, { qcHistories: true })
  await setupEditView(page)
  await selectAllPoints(page)
  const selectedOnPlot = () =>
    page.evaluate(() => {
      const gd = document.querySelector('[data-testid="main-plot"]') as any
      return Math.max(
        0,
        ...(gd?.data ?? []).map((t: any) => t.selectedpoints?.length ?? 0)
      )
    })
  const before = await selectedOnPlot()
  expect(before).toBeGreaterThan(0)

  await page.getByRole('button', { name: 'Table' }).click()
  await page.getByRole('button', { name: 'Plot', exact: true }).click()

  await expect.poll(selectedOnPlot).toBe(before)
})
