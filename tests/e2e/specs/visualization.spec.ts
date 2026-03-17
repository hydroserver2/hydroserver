import { expect, test } from '@playwright/test'

import { authenticateSession } from '../support/auth'
import { fixtures, users } from '../support/fixtures'

test.describe('visualization', () => {
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

    await page
      .getByTestId(`plot-datastream-${fixtures.datastreams.public.id}`)
      .click()
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

    expect(copiedUrl).toContain(`/visualize-data/?sites=${fixtures.things.public.id}`)
    expect(copiedUrl).toContain(`datastreams=${fixtures.datastreams.public.id}`)

    const copiedContext = await browser.newContext()
    const copiedPage = await copiedContext.newPage()
    await copiedPage.goto(copiedUrl)

    await expect(
      copiedPage.getByTestId(`plot-datastream-${fixtures.datastreams.public.id}`)
    ).toBeVisible()
    await copiedContext.close()
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
