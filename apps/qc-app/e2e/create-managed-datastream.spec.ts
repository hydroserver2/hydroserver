/**
 * Creating a managed datastream from a source that has none: the form
 * defaults every field from the source, and what the user edits (name,
 * description, status, method) is what gets posted.
 */

import { expect, test } from '@playwright/test'
import { installMocks } from './support/mocks'
import { gotoHome } from './support/app'
import { DATASTREAM_ID, QC_PROC_LEVEL_ID, SENSOR_ID_B } from './support/fixtures'

/** Open a Vuetify select and pick one of its options. */
async function pick(page: import('@playwright/test').Page, testId: string, option: string) {
  await page.getByTestId(testId).click()
  await page.getByRole('option', { name: option, exact: true }).click()
}

test.describe('create managed datastream', () => {
  test.beforeEach(() => test.slow())

  test('posts the edited fields and moves on to the session window', async ({
    page,
  }) => {
    const datastreamCreates: Array<Record<string, any>> = []
    await installMocks(page, { datastreamCreates })
    await gotoHome(page)

    // No managed datastream yet, so Edit opens the create form directly.
    await page.getByTestId(`edit-datastream-${DATASTREAM_ID}`).click()
    await expect(page.getByTestId('create-confirm')).toBeVisible()

    // Defaults come from the source datastream.
    await expect(page.getByTestId('create-name').locator('input')).toHaveValue(
      'Streamflow Datastream (QC)'
    )
    await expect(
      page.getByTestId('create-description').getByRole('textbox')
    ).toHaveValue('Synthetic sine-wave dataset for QC tests')
    await expect(page.getByTestId('create-status')).toContainText('ongoing')
    await expect(page.getByTestId('create-sensor')).toContainText(
      'ADVelocity Sensor'
    )

    await pick(page, 'create-processing-level', 'Quality controlled')
    await page
      .getByTestId('create-description')
      .getByRole('textbox')
      .fill('Quality-controlled streamflow')
    await pick(page, 'create-status', 'complete')
    await pick(page, 'create-sensor', 'Thermistor Sensor')

    await page.getByTestId('create-confirm').click()

    await expect.poll(() => datastreamCreates.length).toBe(1)
    expect(datastreamCreates[0]).toMatchObject({
      name: 'Streamflow Datastream (QC)',
      description: 'Quality-controlled streamflow',
      status: 'complete',
      sensorId: SENSOR_ID_B,
      processingLevelId: QC_PROC_LEVEL_ID,
      valueCount: 0,
    })

    // The flow continues into the session window for the new datastream.
    await expect(page.getByTestId('session-window-start')).toBeVisible()
  })

  test('blocks create without a description', async ({ page }) => {
    await installMocks(page)
    await gotoHome(page)

    await page.getByTestId(`edit-datastream-${DATASTREAM_ID}`).click()
    await pick(page, 'create-processing-level', 'Quality controlled')
    await expect(page.getByTestId('create-confirm')).toBeEnabled()

    await page.getByTestId('create-description').getByRole('textbox').fill('')
    await expect(page.getByTestId('create-confirm')).toBeDisabled()
    await expect(page.getByTestId('create-description')).toContainText(
      'A description is required'
    )
  })
})
