/**
 * Time range presets anchor to the plotted data, so a datastream whose
 * observations are years old plots without widening the range first.
 */

import { expect, test } from '@playwright/test'
import { installMocks } from './support/mocks'
import { gotoHome, plotFirstDatastream } from './support/app'
import {
  DATASTREAM_ID,
  FIXTURE_OBS_COUNT,
  FIXTURE_OBS_SPACING_MS,
  buildObservations,
} from './support/fixtures'

const OLD_START_MS = Date.UTC(2021, 5, 1)
const OLD_END_MS = OLD_START_MS + (FIXTURE_OBS_COUNT - 1) * FIXTURE_OBS_SPACING_MS
// Off a whole-minute boundary: DatePickerField has no seconds field for
// this control, so a blur reconstructs the date at minute resolution. On
// a whole-minute end time that reconstruction already matches the raw
// model value, so the untouched-field test below would pass even without
// the field's own unchanged-value guard.
const OLD_END_ISO = new Date(OLD_END_MS + 37_500).toISOString()

test.describe('time range presets', () => {
  test.beforeEach(async ({ page }) => {
    await installMocks(page, {
      observations: buildObservations(FIXTURE_OBS_COUNT, OLD_START_MS),
      catalogOverrides: {
        [DATASTREAM_ID]: {
          phenomenonBeginTime: new Date(OLD_START_MS).toISOString(),
          phenomenonEndTime: OLD_END_ISO,
        },
      },
    })
    await gotoHome(page)
  })

  test('plots years-old data with the default preset', async ({ page }) => {
    await plotFirstDatastream(page)
    await expect(page.locator('.plotted-item__subtitle').first()).toHaveText(
      `${FIXTURE_OBS_COUNT} pts loaded`
    )
    await expect(page.getByTestId('date-preset-1m')).toHaveClass(
      /v-chip--variant-tonal/
    )
    await expect(page.getByTestId('date-preset-custom')).toHaveCount(0)
  })

  test('leaving a date field untouched keeps the preset', async ({ page }) => {
    await plotFirstDatastream(page)
    await page.getByTestId('date-range-from').locator('input').first().click()
    await page.keyboard.press('Tab')
    await expect(page.getByTestId('date-preset-custom')).toHaveCount(0)
    await expect(page.getByTestId('date-preset-1m')).toHaveClass(
      /v-chip--variant-tonal/
    )
  })
})
