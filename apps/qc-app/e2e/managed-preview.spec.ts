/**
 * A managed datastream with nothing committed and a session in progress plots
 * the session's working copy (its saved draft replayed), the same data the
 * editor opens, while the raw line keeps every point.
 */

import { expect, test, type Page } from '@playwright/test'
import { installMocks, type MockQcSession } from './support/mocks'
import { gotoHome } from './support/app'
import {
  DATASTREAM_ID,
  FIXTURE_OBS_COUNT,
  FIXTURE_OBS_END_ISO,
  FIXTURE_OBS_START_ISO,
  MANAGED_DATASTREAM_ID,
  QC_HISTORY_ID,
  QC_SOURCE_CHECKSUM,
} from './support/fixtures'

const RAW_NAME = 'Streamflow Datastream'
const MANAGED_NAME = 'Streamflow Datastream (QC)'
const SESSION_ID = 'qcs-e2e-draft'
const DELETED_INDICES = [10, 11, 12]

/** An in-progress session whose saved draft deletes `DELETED_INDICES`. */
function inProgressSession(): MockQcSession {
  // Persisted as the app saves a delete: the SELECTION it consumes, then DELETE_POINTS.
  const draft = [
    { operationType: 'SELECTION', arguments: [DELETED_INDICES] },
    { operationType: 'DELETE_POINTS', arguments: [] },
  ]
  return {
    id: SESSION_ID,
    historyId: QC_HISTORY_ID,
    status: 'in_progress',
    description: 'Draft',
    phenomenonTimeStart: FIXTURE_OBS_START_ISO,
    phenomenonTimeEnd: FIXTURE_OBS_END_ISO,
    sourceChecksum: QC_SOURCE_CHECKSUM,
    createdAt: FIXTURE_OBS_START_ISO,
    committedAt: null,
    createdBy: { name: 'Test User', email: 'test@example.com' },
    dependencyIds: [],
    operations: draft.map((op, order) => ({
      ...op,
      id: `${SESSION_ID}-op-${order}`,
      order,
      comment: null,
      createdAt: FIXTURE_OBS_START_ISO,
    })),
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

  const plotOptions = async (page: Page, ids: string[]) => {
    await page.getByTestId(`plot-checkbox-${DATASTREAM_ID}`).click()
    await expect(page.getByTestId('plot-source-dialog')).toBeVisible()
    for (const id of ids) {
      await page.getByTestId(`plot-option-${id}`).locator('input').check()
    }
    await page.getByTestId('plot-source-apply').click()
    await expect(page.getByTestId('plot-source-dialog')).toBeHidden()
  }

  // The raw name is a substring of the managed name ("Streamflow Datastream"
  // vs "Streamflow Datastream (QC)"), so pin the row by its title text using
  // exact matching rather than a loose text filter.
  const subtitleForRow = (page: Page, name: string) =>
    page
      .locator('.plotted-item')
      .filter({ has: page.getByText(name, { exact: true }) })
      .locator('.plotted-item__subtitle')

  const replayedCount = FIXTURE_OBS_COUNT - DELETED_INDICES.length

  test('plots the session working copy with its saved draft replayed', async ({ page }) => {
    await plotOptions(page, [MANAGED_DATASTREAM_ID])
    await expect(page.locator('.plotted-item__subtitle')).toHaveCount(1)
    await expect(subtitleForRow(page, MANAGED_NAME)).toHaveText(
      `${replayedCount} pts loaded`
    )
  })

  test('plots raw and working copy side by side without editing the raw line', async ({ page }) => {
    await plotOptions(page, [DATASTREAM_ID, MANAGED_DATASTREAM_ID])
    await expect(page.locator('.plotted-item__subtitle')).toHaveCount(2)
    await expect(subtitleForRow(page, MANAGED_NAME)).toHaveText(
      `${replayedCount} pts loaded`
    )
    await expect(subtitleForRow(page, RAW_NAME)).toHaveText(
      `${FIXTURE_OBS_COUNT} pts loaded`
    )
  })
})
