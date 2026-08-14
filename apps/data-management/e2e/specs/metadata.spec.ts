import { expect, test } from '../support/test'

import { authenticateSession } from '../support/auth'
import { fixtures, users } from '../support/fixtures'
import { fillCombobox, workspaceListItem } from '../support/ui'

test.describe('metadata management', () => {
  test('the metadata route redirects to the workspaces page metadata tab', async ({
    page,
  }) => {
    await authenticateSession(page, users.owner.email, users.owner.password)
    await page.goto('/metadata')

    await expect(page).toHaveURL(/\/workspaces\?section=metadata/)
    await expect(
      page.getByRole('heading', { name: 'Manage workspaces' })
    ).toBeVisible()

    // Workspace metadata is shown by default, with its own type tabs.
    await expect(page.getByTestId('workspace-metadata-table')).toBeVisible()
    await expect(page.getByRole('tab', { name: 'Methods' })).toBeVisible()
    await expect(
      page.getByRole('tab', { name: 'Observed properties' })
    ).toBeVisible()
    await expect(
      page.getByRole('tab', { name: 'Processing levels' })
    ).toBeVisible()
    await expect(page.getByRole('tab', { name: 'Units' })).toBeVisible()
    await expect(
      page.getByRole('tab', { name: 'Result qualifiers' })
    ).toBeVisible()
    await expect(page.getByTestId('system-metadata-table')).toHaveCount(0)

    // Switching scope swaps to the system-scoped table.
    await page
      .getByRole('button', { name: 'System metadata', exact: true })
      .click()
    await expect(page.getByTestId('system-metadata-table')).toBeVisible()
    await expect(page.getByTestId('workspace-metadata-table')).toHaveCount(0)
  })

  test('switching metadata scope shows workspace or system entries, not both at once', async ({
    page,
  }) => {
    await authenticateSession(page, users.owner.email, users.owner.password)
    await page.goto('/metadata')
    await workspaceListItem(page, fixtures.workspaces.private.name).click()

    await page.getByRole('tab', { name: 'Methods' }).click()

    const workspaceTable = page.getByTestId('workspace-metadata-table')
    await expect(
      workspaceTable
        .locator('tr')
        .filter({ hasText: fixtures.metadata.privateAssignedMethod.name })
        .first()
    ).toBeVisible()
    await expect(page.getByTestId('system-metadata-table')).toHaveCount(0)

    await page
      .getByRole('button', { name: 'System metadata', exact: true })
      .click()

    const systemTable = page.getByTestId('system-metadata-table')
    await expect(
      systemTable
        .locator('tr')
        .filter({ hasText: fixtures.metadata.systemMethod.name })
        .first()
    ).toBeVisible()
    await expect(page.getByTestId('workspace-metadata-table')).toHaveCount(0)
  })

  test('admins can update and delete system metadata from the all metadata table', async ({
    page,
  }) => {
    const qualifier = fixtures.metadata.editableSystemResultQualifier
    const renamedCode = `${qualifier.name}-UPDATED`

    await authenticateSession(page, users.admin.email, users.admin.password)
    await page.goto(
      `/workspaces?workspace=${fixtures.workspaces.admin.id}&section=metadata`
    )

    await page.getByRole('button', { name: 'All', exact: true }).click()
    await page.getByRole('tab', { name: 'Result qualifiers' }).click()

    const allTable = page.getByTestId('all-metadata-table')
    await allTable
      .getByRole('textbox', { name: 'Search metadata' })
      .fill(qualifier.name)
    const editButton = allTable.getByTestId(`edit-metadata-${qualifier.id}`)
    const deleteButton = allTable.getByTestId(`delete-metadata-${qualifier.id}`)
    await expect(editButton).toBeVisible()
    await expect(deleteButton).toBeVisible()

    await editButton.click()
    await page.getByLabel('Code *').fill(renamedCode)
    await page.getByRole('button', { name: 'Update', exact: true }).click()

    const renamedRow = allTable.locator('tr').filter({ hasText: renamedCode })
    await expect(renamedRow).toBeVisible()

    await renamedRow.getByLabel('Delete metadata item').click()
    await expect(page.getByText(/isn't being used|not.*used/i)).toBeVisible()
    await page.getByRole('button', { name: 'Delete', exact: true }).click()
    await expect(renamedRow).toHaveCount(0)
  })

  test('workspace method metadata can be created, updated, and deleted', async ({
    page,
  }) => {
    const methodName = `E2E Method ${Date.now()}`
    const renamedMethodName = `${methodName} Updated`

    await authenticateSession(page, users.owner.email, users.owner.password)
    await page.goto('/metadata')
    await workspaceListItem(page, fixtures.workspaces.private.name).click()

    const workspaceTable = page.getByTestId('workspace-metadata-table')
    await page.getByRole('tab', { name: 'Methods' }).click()
    await workspaceTable
      .getByRole('button', { name: /Add new method/i })
      .click()

    await fillCombobox(page, 'Type *', 'E2E Method Type')
    await page
      .getByLabel('Description *')
      .fill('Temporary method created by the Playwright metadata CRUD suite.')
    await page.getByLabel('Name *').fill(methodName)
    await page.getByRole('button', { name: 'Save' }).click()

    const methodRow = page.locator('tr').filter({ hasText: methodName }).first()
    await expect(methodRow).toBeVisible()

    await methodRow.locator('.v-icon').first().click()
    await page.getByLabel('Name *').fill(renamedMethodName)
    await page.getByRole('button', { name: 'Update' }).click()

    const renamedMethodRow = page
      .locator('tr')
      .filter({ hasText: renamedMethodName })
      .first()
    await expect(renamedMethodRow).toBeVisible()

    await renamedMethodRow.locator('.v-icon').nth(1).click()
    await expect(
      page.getByText("isn't being used by any datastreams")
    ).toBeVisible()
    await page.getByRole('button', { name: 'Delete', exact: true }).click()

    await expect(
      page.locator('tr').filter({ hasText: renamedMethodName })
    ).toHaveCount(0)
  })

  test('instrument methods require sensor details and derive their name', async ({
    page,
  }) => {
    const manufacturer = `E2E Manufacturer ${Date.now()}`
    const model = 'E2E Model'
    const derivedName = `${manufacturer}: ${model}`

    await authenticateSession(page, users.owner.email, users.owner.password)
    await page.goto('/metadata')
    await workspaceListItem(page, fixtures.workspaces.private.name).click()

    const workspaceTable = page.getByTestId('workspace-metadata-table')
    await page.getByRole('tab', { name: 'Methods' }).click()
    await workspaceTable
      .getByRole('button', { name: /Add new method/i })
      .click()

    await fillCombobox(page, 'Type *', 'Instrument Deployment')
    await page
      .getByLabel('Description *')
      .fill('Instrument method created by the Playwright regression suite.')

    await expect(page.getByLabel('Name *', { exact: true })).toHaveCount(0)

    const manufacturerField = page.getByLabel('Sensor Model Manufacturer *')
    const modelField = page.getByLabel('Sensor Model *', { exact: true })
    await page.getByRole('button', { name: 'Save' }).click()
    await expect(page.getByText('This field is required.')).toHaveCount(2)

    await manufacturerField.fill(manufacturer)
    await modelField.fill(model)
    await page.getByRole('button', { name: 'Save' }).click()

    const methodRow = page
      .locator('tr')
      .filter({ hasText: derivedName })
      .first()
    await expect(methodRow).toBeVisible()

    await methodRow.locator('.v-icon').nth(1).click()
    await page.getByRole('button', { name: 'Delete', exact: true }).click()
    await expect(
      page.locator('tr').filter({ hasText: derivedName })
    ).toHaveCount(0)
  })

  test('workspace observed property metadata can be created, updated, and deleted', async ({
    page,
  }) => {
    const propName = `E2E Observed Property ${Date.now()}`
    const renamedPropName = `${propName} Updated`

    await authenticateSession(page, users.owner.email, users.owner.password)
    await page.goto('/metadata')
    await workspaceListItem(page, fixtures.workspaces.private.name).click()

    const workspaceTable = page.getByTestId('workspace-metadata-table')
    await page.getByRole('tab', { name: 'Observed properties' }).click()
    await workspaceTable
      .getByRole('button', { name: /Add new observed property/i })
      .click()

    await fillCombobox(page, 'Variable Type *', 'E2E Variable Type')
    await page
      .getByLabel('Definition *')
      .fill('https://www.example.com/e2e-observed-property')
    await page
      .getByLabel('Description *')
      .fill(
        'Temporary observed property created by the Playwright metadata CRUD suite.'
      )
    await page.getByLabel('Variable Code *').fill(`E2E-OP-${Date.now()}`)
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
    await page.getByRole('button', { name: 'Delete', exact: true }).click()

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
    await workspaceListItem(page, fixtures.workspaces.private.name).click()

    const workspaceTable = page.getByTestId('workspace-metadata-table')
    await page.getByRole('tab', { name: 'Processing levels' }).click()
    await workspaceTable
      .getByRole('button', { name: /Add new processing level/i })
      .click()

    await page.getByLabel('Code *').fill(levelCode)
    await page.getByLabel('Definition').fill('E2E processing level definition')
    await page.getByRole('button', { name: 'Save' }).click()

    const levelRow = page.locator('tr').filter({ hasText: levelCode }).first()
    await expect(levelRow).toBeVisible()

    await levelRow.locator('.v-icon').first().click()
    await page.getByLabel('Code *').fill(renamedCode)
    await page.getByRole('button', { name: 'Update' }).click()

    const renamedRow = page
      .locator('tr')
      .filter({ hasText: renamedCode })
      .first()
    await expect(renamedRow).toBeVisible()

    await renamedRow.locator('.v-icon').nth(1).click()
    await expect(page.getByText(/isn't being used|not.*used/i)).toBeVisible()
    await page.getByRole('button', { name: 'Delete', exact: true }).click()

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
    await workspaceListItem(page, fixtures.workspaces.private.name).click()

    const workspaceTable = page.getByTestId('workspace-metadata-table')
    await page.getByRole('tab', { name: 'Units' }).click()
    await workspaceTable.getByRole('button', { name: /Add new unit/i }).click()

    await fillCombobox(page, 'Unit Type *', 'E2E Unit Type')
    await page.getByLabel('Symbol *').fill(`e2e${stamp}`)
    await page.getByLabel('Definition *').fill('E2E unit definition')
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
    await page.getByRole('button', { name: 'Delete', exact: true }).click()

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
    await workspaceListItem(page, fixtures.workspaces.private.name).click()

    const workspaceTable = page.getByTestId('workspace-metadata-table')
    await page.getByRole('tab', { name: 'Result qualifiers' }).click()
    await workspaceTable
      .getByRole('button', { name: /Add new result qualifier/i })
      .click()

    await page.getByLabel('Code *').fill(qualifierCode)
    await page
      .getByLabel('Description')
      .fill(
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
    await page.getByRole('button', { name: 'Delete', exact: true }).click()

    await expect(
      page.locator('tr').filter({ hasText: renamedCode })
    ).toHaveCount(0)
  })

  test('metadata search box filters visible rows', async ({ page }) => {
    await authenticateSession(page, users.owner.email, users.owner.password)
    await page.goto('/metadata')
    await workspaceListItem(page, fixtures.workspaces.public.name).click()

    const workspaceTable = page.getByTestId('workspace-metadata-table')

    const searchBox = page
      .getByRole('textbox', { name: 'Search metadata', exact: true })
      .first()
    await expect(searchBox).toBeVisible()

    await searchBox.fill(fixtures.metadata.publicAssignedMethod.name)
    await expect(
      workspaceTable
        .locator('tr')
        .filter({ hasText: fixtures.metadata.publicAssignedMethod.name })
        .first()
    ).toBeVisible()

    await searchBox.fill('zzz-no-match-e2e')
    await expect(
      workspaceTable
        .locator('tr')
        .filter({ hasText: fixtures.metadata.publicAssignedMethod.name })
    ).toHaveCount(0)

    await searchBox.clear()
  })

  test('metadata in-use items cannot be deleted from the workspace table', async ({
    page,
  }) => {
    await authenticateSession(page, users.owner.email, users.owner.password)
    await page.goto('/metadata')
    await workspaceListItem(page, fixtures.workspaces.private.name).click()

    const workspaceTable = page.getByTestId('workspace-metadata-table')
    await page.getByRole('tab', { name: 'Methods' }).click()

    const assignedMethodRow = workspaceTable
      .locator('tr')
      .filter({ hasText: fixtures.metadata.privateAssignedMethod.name })
      .first()
    await expect(assignedMethodRow).toBeVisible()

    await assignedMethodRow.locator('.v-icon').nth(1).click()
    await expect(
      page.getByText("cannot be deleted because it's being referenced")
    ).toBeVisible()
    await expect(
      page.getByRole('button', { name: 'Delete', exact: true })
    ).toHaveCount(0)
    await page.getByRole('button', { name: 'Cancel' }).click()
  })
})
