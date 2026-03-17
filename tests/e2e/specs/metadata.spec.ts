import { expect, test } from '@playwright/test'

import { authenticateSession } from '../support/auth'
import { fixtures, users } from '../support/fixtures'
import { fillCombobox, selectWorkspace } from '../support/ui'

test.describe('metadata management', () => {
  test('metadata page loads workspace and system tabs', async ({ page }) => {
    await authenticateSession(page, users.owner.email, users.owner.password)
    await page.goto('/metadata')

    await expect(
      page.getByRole('heading', { name: 'Manage metadata' })
    ).toBeVisible()
    await expect(page.getByText('Selected workspace:', { exact: false })).toBeVisible()
    await expect(page.getByRole('tab', { name: 'Sensors' }).first()).toBeVisible()
    await expect(
      page.getByRole('tab', { name: 'Observed properties' }).first()
    ).toBeVisible()
    await expect(
      page.getByRole('tab', { name: 'Processing levels' }).first()
    ).toBeVisible()
    await expect(page.getByRole('tab', { name: 'Units' }).first()).toBeVisible()
    await expect(
      page.getByRole('tab', { name: 'Result qualifiers' }).first()
    ).toBeVisible()
  })

  test('workspace sensor metadata can be created, updated, and deleted', async ({
    page,
  }) => {
    const sensorName = `E2E Sensor ${Date.now()}`
    const renamedSensorName = `${sensorName} Updated`

    await authenticateSession(page, users.owner.email, users.owner.password)
    await page.goto('/metadata')
    await selectWorkspace(page, fixtures.workspaces.private.name)

    const workspaceTable = page.getByTestId('workspace-metadata-table')
    await workspaceTable.getByRole('tab', { name: 'Sensors' }).click()
    await workspaceTable.getByRole('button', { name: /Add new sensor/i }).click()

    await fillCombobox(page, 'Method Type *', 'E2E Method Type')
    await page.getByLabel('Description *').fill(
      'Temporary sensor created by the Playwright metadata CRUD suite.'
    )
    await page.getByLabel('Name *').fill(sensorName)
    await page.getByRole('button', { name: 'Save' }).click()

    const sensorRow = page.locator('tr').filter({ hasText: sensorName }).first()
    await expect(sensorRow).toBeVisible()

    await sensorRow.locator('.v-icon').first().click()
    await page.getByLabel('Name *').fill(renamedSensorName)
    await page.getByRole('button', { name: 'Update' }).click()

    const renamedSensorRow = page
      .locator('tr')
      .filter({ hasText: renamedSensorName })
      .first()
    await expect(renamedSensorRow).toBeVisible()

    await renamedSensorRow.locator('.v-icon').nth(1).click()
    await expect(page.getByText("isn't being used by any datastreams")).toBeVisible()
    await page.getByRole('button', { name: 'Delete' }).click()

    await expect(
      page.locator('tr').filter({ hasText: renamedSensorName })
    ).toHaveCount(0)
  })
})
