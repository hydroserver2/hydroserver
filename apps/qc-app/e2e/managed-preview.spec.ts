/**
 * A managed datastream with nothing committed and a session in progress plots
 * the session's working copy, the same data the editor opens.
 */

import { expect, test } from '@playwright/test'
import { installMocks, type MockQcSession } from './support/mocks'
import { gotoHome } from './support/app'
import {
  DATASTREAM_ID,
  FIXTURE_OBS_COUNT,
  FIXTURE_OBS_END_ISO,
  FIXTURE_OBS_START_ISO,
  MANAGED_DATASTREAM_ID,
  QC_HISTORY_ID,
} from './support/fixtures'

/** A fresh in-progress session over the fixture window, no saved operations. */
function inProgressSession(): MockQcSession {
  return {
    id: 'qcs-e2e-draft',
    historyId: QC_HISTORY_ID,
    status: 'in_progress',
    description: 'Draft',
    phenomenonTimeStart: FIXTURE_OBS_START_ISO,
    phenomenonTimeEnd: FIXTURE_OBS_END_ISO,
    sourceChecksum: 'e2e-draft-checksum',
    createdAt: FIXTURE_OBS_START_ISO,
    committedAt: null,
    createdBy: { name: 'Test User', email: 'test@example.com' },
    dependencyIds: [],
    operations: [],
  }
}

test.describe('managed datastream preview', () => {
  test.beforeEach(async ({ page }) => {
    await installMocks(page, {
      qcHistories: true,
      qcSessionState: [inProgressSession()],
      observationsById: {
        [MANAGED_DATASTREAM_ID]: { phenomenonTime: [], result: [] },
      },
      catalogOverrides: {
        [MANAGED_DATASTREAM_ID]: {
          valueCount: 0,
          phenomenonBeginTime: null,
          phenomenonEndTime: null,
        },
      },
    })
    await gotoHome(page)
  })

  const plotOptions = async (page: any, ids: string[]) => {
    await page.getByTestId(`plot-checkbox-${DATASTREAM_ID}`).click()
    await expect(page.getByTestId('plot-source-dialog')).toBeVisible()
    for (const id of ids) {
      await page.getByTestId(`plot-option-${id}`).locator('input').check()
    }
    await page.getByTestId('plot-source-apply').click()
    await expect(page.getByTestId('plot-source-dialog')).toBeHidden()
  }

  test('plots the session working copy instead of an empty line', async ({ page }) => {
    await plotOptions(page, [MANAGED_DATASTREAM_ID])
    await expect(page.locator('.plotted-item__subtitle').first()).toHaveText(
      `${FIXTURE_OBS_COUNT} pts loaded`
    )
  })

  test('plots raw and working copy side by side', async ({ page }) => {
    await plotOptions(page, [DATASTREAM_ID, MANAGED_DATASTREAM_ID])
    const subtitles = page.locator('.plotted-item__subtitle')
    await expect(subtitles).toHaveCount(2)
    await expect(subtitles.nth(0)).toHaveText(`${FIXTURE_OBS_COUNT} pts loaded`)
    await expect(subtitles.nth(1)).toHaveText(`${FIXTURE_OBS_COUNT} pts loaded`)
  })
})
