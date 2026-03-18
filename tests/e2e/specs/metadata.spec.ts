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

  test('workspace observed property metadata can be created, updated, and deleted', async ({
    page,
  }) => {
    const propName = `E2E Observed Property ${Date.now()}`
    const renamedPropName = `${propName} Updated`

    await authenticateSession(page, users.owner.email, users.owner.password)
    await page.goto('/metadata')
    await selectWorkspace(page, fixtures.workspaces.private.name)

    const workspaceTable = page.getByTestId('workspace-metadata-table')
    await workspaceTable.getByRole('tab', { name: 'Observed properties' }).click()
    await workspaceTable
      .getByRole('button', { name: /Add new observed property/i })
      .click()

    await fillCombobox(page, 'Variable Type *', 'E2E Variable Type')
    await page.getByLabel('Definition *').fill('https://www.example.com/e2e-observed-property')
    await page.getByLabel('Name *').fill(propName)
    await page.getByRole('button', { name: 'Save' }).click()

    const propRow = page.locator('tr').filter({ hasText: propName }).first()
    await expect(propRow).toBeVisible()

    await propRow.locator('.v-icon').first().click()
    await page.getByLabel('Name *').fill(renamedPropName)
    await page.getByRole('button', { name: 'Update' }).click()

    const renamedPropRow = page
      .locator('tr')
      .filter({ hasText: renamedPropName })
      .first()
    await expect(renamedPropRow).toBeVisible()

    await renamedPropRow.locator('.v-icon').nth(1).click()
    await expect(page.getByText(/isn't being used|not.*used/i)).toBeVisible()
    await page.getByRole('button', { name: 'Delete' }).click()

    await expect(
      page.locator('tr').filter({ hasText: renamedPropName })
    ).toHaveCount(0)
  })

  test('workspace processing level metadata can be created, updated, and deleted', async ({
    page,
  }) => {
    const stamp = Date.now()
    const levelCode = `E2E-PL-${stamp}`
    const renamedCode = `${levelCode}-UPD`

    await authenticateSession(page, users.owner.email, users.owner.password)
    await page.goto('/metadata')
    await selectWorkspace(page, fixtures.workspaces.private.name)

    const workspaceTable = page.getByTestId('workspace-metadata-table')
    await workspaceTable.getByRole('tab', { name: 'Processing levels' }).click()
    await workspaceTable
      .getByRole('button', { name: /Add new processing level/i })
      .click()

    await page.getByLabel('Code *').fill(levelCode)
    await page.getByLabel('Definition *').fill('E2E processing level definition')
    await page.getByRole('button', { name: 'Save' }).click()

    const levelRow = page.locator('tr').filter({ hasText: levelCode }).first()
    await expect(levelRow).toBeVisible()

    await levelRow.locator('.v-icon').first().click()
    await page.getByLabel('Code *').fill(renamedCode)
    await page.getByRole('button', { name: 'Update' }).click()

    const renamedRow = page.locator('tr').filter({ hasText: renamedCode }).first()
    await expect(renamedRow).toBeVisible()

    await renamedRow.locator('.v-icon').nth(1).click()
    await expect(page.getByText(/isn't being used|not.*used/i)).toBeVisible()
    await page.getByRole('button', { name: 'Delete' }).click()

    await expect(
      page.locator('tr').filter({ hasText: renamedCode })
    ).toHaveCount(0)
  })

  test('workspace unit metadata can be created, updated, and deleted', async ({
    page,
  }) => {
    const stamp = Date.now()
    const unitName = `E2E Unit ${stamp}`
    const renamedUnitName = `${unitName} Updated`

    await authenticateSession(page, users.owner.email, users.owner.password)
    await page.goto('/metadata')
    await selectWorkspace(page, fixtures.workspaces.private.name)

    const workspaceTable = page.getByTestId('workspace-metadata-table')
    await workspaceTable.getByRole('tab', { name: 'Units' }).click()
    await workspaceTable.getByRole('button', { name: /Add new unit/i }).click()

    await fillCombobox(page, 'Unit Type *', 'E2E Unit Type')
    await page.getByLabel('Symbol *').fill(`e2e${stamp}`)
    await page.getByLabel('Name *').fill(unitName)
    await page.getByRole('button', { name: 'Save' }).click()

    const unitRow = page.locator('tr').filter({ hasText: unitName }).first()
    await expect(unitRow).toBeVisible()

    await unitRow.locator('.v-icon').first().click()
    await page.getByLabel('Name *').fill(renamedUnitName)
    await page.getByRole('button', { name: 'Update' }).click()

    const renamedUnitRow = page
      .locator('tr')
      .filter({ hasText: renamedUnitName })
      .first()
    await expect(renamedUnitRow).toBeVisible()

    await renamedUnitRow.locator('.v-icon').nth(1).click()
    await expect(page.getByText(/isn't being used|not.*used/i)).toBeVisible()
    await page.getByRole('button', { name: 'Delete' }).click()

    await expect(
      page.locator('tr').filter({ hasText: renamedUnitName })
    ).toHaveCount(0)
  })

  test('workspace result qualifier metadata can be created, updated, and deleted', async ({
    page,
  }) => {
    const stamp = Date.now()
    const qualifierCode = `E2E-RQ-${stamp}`
    const renamedCode = `${qualifierCode}-UPD`

    await authenticateSession(page, users.owner.email, users.owner.password)
    await page.goto('/metadata')
    await selectWorkspace(page, fixtures.workspaces.private.name)

    const workspaceTable = page.getByTestId('workspace-metadata-table')
    await workspaceTable
      .getByRole('tab', { name: 'Result qualifiers' })
      .click()
    await workspaceTable
      .getByRole('button', { name: /Add new result qualifier/i })
      .click()

    await page.getByLabel('Code *').fill(qualifierCode)
    await page.getByLabel('Description *').fill(
      'Temporary result qualifier created by the Playwright metadata CRUD suite.'
    )
    await page.getByRole('button', { name: 'Save' }).click()

    const qualifierRow = page
      .locator('tr')
      .filter({ hasText: qualifierCode })
      .first()
    await expect(qualifierRow).toBeVisible()

    await qualifierRow.locator('.v-icon').first().click()
    await page.getByLabel('Code *').fill(renamedCode)
    await page.getByRole('button', { name: 'Update' }).click()

    const renamedRow = page
      .locator('tr')
      .filter({ hasText: renamedCode })
      .first()
    await expect(renamedRow).toBeVisible()

    await renamedRow.locator('.v-icon').nth(1).click()
    await expect(page.getByText(/isn't being used|not.*used/i)).toBeVisible()
    await page.getByRole('button', { name: 'Delete' }).click()

    await expect(
      page.locator('tr').filter({ hasText: renamedCode })
    ).toHaveCount(0)
  })

  test('metadata search box filters visible rows', async ({ page }) => {
    await authenticateSession(page, users.owner.email, users.owner.password)
    await page.goto('/metadata')

    const searchBox = page.getByRole('textbox', { name: /search/i }).first()
    await expect(searchBox).toBeVisible()

    await searchBox.fill('Public Assigned Sensor')
    await expect(
      page.locator('tr').filter({ hasText: 'Public Assigned Sensor' }).first()
    ).toBeVisible()

    await searchBox.fill('zzz-no-match-e2e')
    await expect(
      page.locator('tr').filter({ hasText: 'Public Assigned Sensor' })
    ).toHaveCount(0)

    await searchBox.clear()
  })
})
