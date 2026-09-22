/**
 * Plotting a source datastream that has managed (QC) datastreams opens a
 * chooser instead of toggling straight to the plot.
 *
 * Layout is asserted here rather than in the jsdom component test: jsdom has
 * no layout engine, so a dialog that collapses to a one-character column
 * still passes there.
 */

import { expect, test } from '@playwright/test'
import { installMocks } from './support/mocks'
import { seedWorkspaceSelection, waitForHomeReady } from './support/app'
import { DATASTREAM_ID, MANAGED_DATASTREAM_ID } from './support/fixtures'

test.describe('plot source chooser', () => {
  test.beforeEach(async ({ page }) => {
    await installMocks(page, { qcHistories: true })
    await seedWorkspaceSelection(page)
    await page.goto('/')
    await waitForHomeReady(page)
  })

  const openChooser = async (page: any) => {
    await page.getByTestId(`plot-checkbox-${DATASTREAM_ID}`).click()
    await expect(page.getByTestId('plot-source-dialog')).toBeVisible()
  }

  test('lists the raw datastream and its managed version', async ({ page }) => {
    await openChooser(page)
    await expect(page.getByTestId(`plot-option-${DATASTREAM_ID}`)).toBeVisible()
    await expect(
      page.getByTestId(`plot-option-${MANAGED_DATASTREAM_ID}`)
    ).toBeVisible()
    await expect(page.getByTestId('plot-source-dialog')).toContainText(
      'Raw data'
    )
    await expect(page.getByTestId('plot-source-dialog')).toContainText(
      'Streamflow Datastream (QC)'
    )
    await expect(page.getByTestId('plot-source-dialog')).toContainText(
      'Level: Quality controlled'
    )
  })

  // Regression: with `max-width` and no `width` the dialog was shrink-to-fit
  // and the `min-width: 0` label wrappers collapsed it to a thin column.
  test('renders at a readable width, not a collapsed column', async ({
    page,
  }) => {
    await openChooser(page)
    const box = await page.getByTestId('plot-source-dialog').boundingBox()
    expect(box).not.toBeNull()
    expect(box!.width).toBeGreaterThan(400)

    // Each row's text must sit on a line of its own, not wrap per character.
    const row = page.getByTestId(`plot-option-${MANAGED_DATASTREAM_ID}`)
    const rowBox = await row.boundingBox()
    expect(rowBox!.width).toBeGreaterThan(300)
    expect(rowBox!.height).toBeLessThan(100)
  })

  test('hides the managed datastream from the table but counts it on the row', async ({
    page,
  }) => {
    await expect(
      page.getByTestId(`plot-checkbox-${MANAGED_DATASTREAM_ID}`)
    ).toHaveCount(0)
    await expect(page.getByTitle(/1 managed \(QC\) datastream/)).toBeVisible()
  })

  test('plots the picked series and leaves the raw one off', async ({
    page,
  }) => {
    await openChooser(page)
    await page
      .getByTestId(`plot-option-${MANAGED_DATASTREAM_ID}`)
      .locator('input')
      .check()
    await page.getByTestId('plot-source-apply').click()
    await expect(page.getByTestId('plot-source-dialog')).toBeHidden()

    // The row reads as partially selected: something from the group is
    // plotted, but not the raw datastream.
    const checkbox = page.getByTestId(`plot-checkbox-${DATASTREAM_ID}`)
    await expect(checkbox).toHaveAttribute('aria-pressed', 'true')
    await expect(checkbox.locator('.mdi-checkbox-intermediate')).toBeVisible()
  })

  test('reopens with the current selection and can clear it', async ({
    page,
  }) => {
    await openChooser(page)
    await page
      .getByTestId(`plot-option-${DATASTREAM_ID}`)
      .locator('input')
      .check()
    await page.getByTestId('plot-source-apply').click()
    await expect(page.getByTestId('plot-source-dialog')).toBeHidden()

    await openChooser(page)
    await expect(
      page.getByTestId(`plot-option-${DATASTREAM_ID}`).locator('input')
    ).toBeChecked()

    await page
      .getByTestId(`plot-option-${DATASTREAM_ID}`)
      .locator('input')
      .uncheck()
    await page.getByTestId('plot-source-apply').click()
    await expect(page.getByTestId('plot-source-dialog')).toBeHidden()
    await expect(
      page.getByTestId(`plot-checkbox-${DATASTREAM_ID}`)
    ).toHaveAttribute('aria-pressed', 'false')
  })
})
