import { expect, test, type Page } from '@playwright/test'

import { authenticateSession } from '../support/auth'
import { fixtures, users } from '../support/fixtures'

test.describe('visualization', () => {
  async function plotPublicDatastream(page: Page) {
    await page
      .getByTestId(`plot-datastream-${fixtures.datastreams.public.id}`)
      .click()
    await expect(
      page.getByRole('button', { name: 'Download plot image' })
    ).toBeVisible()
  }

  test('visualization page renders filter controls and seeded datastream rows', async ({
    page,
  }) => {
    await page.goto(`/visualize-data?sites=${fixtures.things.public.id}`)

    await expect(
      page.getByRole('heading', { name: 'Datastreams' })
    ).toBeVisible()
    await expect(page.getByRole('combobox', { name: 'Sites' })).toBeVisible()
    await expect(
      page.getByRole('button', { name: 'Clear Selected' })
    ).toBeVisible()
    await expect(
      page.getByTestId(`plot-datastream-${fixtures.datastreams.public.id}`)
    ).toBeVisible()
    await expect(
      page.getByTestId(
        `plot-datastream-${fixtures.datastreams.publicSystemMetadata.id}`
      )
    ).toBeVisible()
  })

  test('visualization preserves selected datastream state in copied URLs and supports summary mode', async ({
    page,
    browser,
  }) => {
    await page.addInitScript(() => {
      const clipboard = navigator.clipboard
      if (!clipboard) return
      window.__e2eCopiedText = ''
      clipboard.writeText = async (text: string) => {
        window.__e2eCopiedText = text
      }
    })

    await authenticateSession(page, users.owner.email, users.owner.password)
    await page.goto(`/visualize-data?sites=${fixtures.things.public.id}`)

    await expect(
      page.getByTestId(`plot-datastream-${fixtures.datastreams.public.id}`)
    ).toBeVisible()
    await expect(
      page.getByTestId(
        `plot-datastream-${fixtures.datastreams.publicSystemMetadata.id}`
      )
    ).toBeVisible()

    await plotPublicDatastream(page)
    await page.getByTestId('toggle-selected-datastreams').click()

    await expect(
      page.getByTestId(`plot-datastream-${fixtures.datastreams.public.id}`)
    ).toBeVisible()
    await expect(
      page.getByTestId(
        `plot-datastream-${fixtures.datastreams.publicSystemMetadata.id}`
      )
    ).toHaveCount(0)

    await page.getByTestId('show-summary-view').click()
    await expect(page.getByText('Summary Statistics', { exact: true })).toBeVisible()

    await page.getByTestId('show-plot-view').click()
    await page.getByTestId('copy-visualization-state').click()
    const copiedUrl = await page.evaluate(() => window.__e2eCopiedText as string)

    expect(copiedUrl).toContain(`/visualize-data?sites=${fixtures.things.public.id}`)
    expect(copiedUrl).toContain(`datastreams=${fixtures.datastreams.public.id}`)

    const copiedContext = await browser.newContext()
    const copiedPage = await copiedContext.newPage()
    await copiedPage.goto(copiedUrl)

    await expect(
      copiedPage.getByRole('button', { name: 'Copy State as URL' })
    ).toBeVisible()
    await expect(
      copiedPage.getByText(fixtures.datastreams.public.name, { exact: true })
    ).toBeVisible()
    await copiedContext.close()
  })

  test('visualization clear selected deselects all datastreams', async ({
    page,
  }) => {
    await authenticateSession(page, users.owner.email, users.owner.password)
    await page.goto(`/visualize-data?sites=${fixtures.things.public.id}`)

    await expect(
      page.getByTestId(`plot-datastream-${fixtures.datastreams.public.id}`)
    ).toBeVisible()

    await plotPublicDatastream(page)
    await page.getByTestId('toggle-selected-datastreams').click()

    await expect(
      page.getByTestId(`plot-datastream-${fixtures.datastreams.public.id}`)
    ).toBeVisible()
    await expect(
      page.getByTestId(
        `plot-datastream-${fixtures.datastreams.publicSystemMetadata.id}`
      )
    ).toHaveCount(0)

    // clearSelected() resets showOnlySelected to false, so both rows are visible immediately
    await page.getByTestId('clear-selected-datastreams').click()

    await expect(
      page.getByTestId(`plot-datastream-${fixtures.datastreams.public.id}`)
    ).toBeVisible()
    await expect(
      page.getByTestId(
        `plot-datastream-${fixtures.datastreams.publicSystemMetadata.id}`
      )
    ).toBeVisible()
  })

  test('visualization quick-range date buttons update the time range', async ({
    page,
  }) => {
    await authenticateSession(page, users.owner.email, users.owner.password)
    await page.goto(`/visualize-data?sites=${fixtures.things.public.id}`)

    await expect(
      page.getByTestId(`plot-datastream-${fixtures.datastreams.public.id}`)
    ).toBeVisible()

    await plotPublicDatastream(page)

    // Date preset chips use abbreviated labels: 1m, 6m, YTD, 1y, all
    await expect(page.getByText('1m').first()).toBeVisible()
    await expect(page.getByText('6m').first()).toBeVisible()
    await expect(page.getByText('1y').first()).toBeVisible()

    await page.getByText('1m').first().click()
    await page.getByText('6m').first().click()
    await page.getByText('1y').first().click()
  })

  test('visualization custom date range can be set', async ({ page }) => {
    await authenticateSession(page, users.owner.email, users.owner.password)
    await page.goto(`/visualize-data?sites=${fixtures.things.public.id}`)

    await expect(
      page.getByTestId(`plot-datastream-${fixtures.datastreams.public.id}`)
    ).toBeVisible()

    await plotPublicDatastream(page)

    // DatePickerField uses placeholder "Begin Date" / "End Date" and M/D/YYYY format
    const startDate = page.locator('input[placeholder="Begin Date"]').first()
    const endDate = page.locator('input[placeholder="End Date"]').first()

    await expect(startDate).toBeVisible()
    await expect(endDate).toBeVisible()

    await startDate.fill('1/1/2020')
    await endDate.fill('1/1/2021')
    await endDate.press('Tab')

    await expect(startDate).toHaveValue('1/1/2020')
    await expect(endDate).toHaveValue('1/1/2021')
  })

  test('visualization exposes the plot image export action', async ({ page }) => {
    const pageErrors: string[] = []
    page.on('pageerror', (error) => pageErrors.push(error.message))

    await authenticateSession(page, users.owner.email, users.owner.password)
    await page.goto(`/visualize-data?sites=${fixtures.things.public.id}`)

    await plotPublicDatastream(page)

    const downloadButton = page.getByRole('button', { name: 'Download plot image' })
    await expect(downloadButton).toBeVisible()
    await expect(downloadButton).toBeEnabled()
    // Plotly generates the file client-side, and headless Chromium does not emit a
    // reliable Playwright download event for this path in CI.
    await downloadButton.click({ force: true })

    await page.getByTestId('copy-visualization-state').click()
    await expect(
      page.getByRole('button', { name: 'Copy State as URL' })
    ).toBeVisible()
    expect(pageErrors).toHaveLength(0)
  })

  test('visualization metadata modal supports plotting and downloads', async ({
    page,
  }) => {
    await page.setViewportSize({ width: 500, height: 900 })
    await authenticateSession(page, users.owner.email, users.owner.password)
    await page.goto(`/visualize-data?sites=${fixtures.things.public.id}`)

    await expect(
      page.getByTestId(`datavis-metadata-${fixtures.datastreams.public.id}`)
    ).toBeVisible()
    await page
      .getByTestId(`datavis-metadata-${fixtures.datastreams.public.id}`)
      .click()

    await expect(page.getByText('Datastream information')).toBeVisible()
    await expect(page.getByText('General', { exact: true })).toBeVisible()

    const csvDownload = page.waitForEvent('download')
    await page.getByTestId('download-datastream-csv').click()
    const csvArtifact = await csvDownload
    expect(csvArtifact.suggestedFilename()).toBe(
      `datastream_${fixtures.datastreams.public.id}.csv`
    )

    await page.getByTestId('add-datastream-to-plot').click()
    await page.getByTestId('toggle-selected-datastreams').click()

    await expect(
      page.getByTestId(`plot-datastream-${fixtures.datastreams.public.id}`)
    ).toBeVisible()
    await expect(
      page.getByTestId(
        `plot-datastream-${fixtures.datastreams.publicSystemMetadata.id}`
      )
    ).toHaveCount(0)

    const zipDownload = page.waitForEvent('download')
    await page.getByTestId('download-selected-datastreams').click()
    const zipArtifact = await zipDownload
    expect(zipArtifact.suggestedFilename()).toBe('datastreams.zip')
  })
})
