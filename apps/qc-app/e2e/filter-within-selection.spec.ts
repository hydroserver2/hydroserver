/**
 * Filtering within the selection: a filter run with "Search only the
 * selected points" on keeps only its matches among those points, so two
 * one-sided thresholds make a range. The fixture is y = 10 + 5*sin(i/5).
 */

import { expect, test, type Page } from '@playwright/test'
import { installMocks } from './support/mocks'
import { openOp, setupEditView, waitForSelection } from './support/app'

const section = (page: Page) => page.getByTestId('filter-within-section')

/** The count the switch names: the selection, or the base while it's on. */
async function namedCount(page: Page): Promise<number> {
  const text = await section(page).innerText()
  return Number(text.match(/only the ([\d,]+) selected/)![1]!.replace(/,/g, ''))
}

async function addThreshold(page: Page, operator: string, value: string) {
  await page
    .getByTestId('operation-panel-valueThreshold')
    .locator('.v-select')
    .click()
  await page.getByRole('option', { name: operator, exact: true }).click()
  await page.getByLabel('Value').fill(value)
  await page.getByRole('button', { name: /add filter/i }).click()
}

async function clearThresholds(page: Page) {
  await page.getByRole('button', { name: 'Clear all' }).click()
}

test('a filter within the selection keeps only matches among those points', async ({
  page,
}) => {
  await installMocks(page, { qcHistories: true })
  await setupEditView(page)
  await openOp(page, 'valueThreshold')

  await addThreshold(page, 'Greater than', '10')
  await waitForSelection(page, 1)
  const aboveTen = await namedCount(page)

  await page.getByTestId('filter-within-switch').getByRole('checkbox').check()
  await clearThresholds(page)
  await addThreshold(page, 'Less than', '13')
  await waitForSelection(page, 1)

  await page.getByTestId('filter-within-switch').getByRole('checkbox').uncheck()
  const between = await namedCount(page)
  expect(between).toBeGreaterThan(0)
  expect(between).toBeLessThan(aboveTen)

  // Without it, "less than 13" also takes the points at 10 and below.
  await clearThresholds(page)
  await addThreshold(page, 'Less than', '13')
  await waitForSelection(page, 1)
  expect(await namedCount(page)).toBeGreaterThan(between)
})
