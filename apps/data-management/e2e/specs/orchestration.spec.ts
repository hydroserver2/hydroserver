import { expect, test } from '../support/test'

import { authenticateSession } from '../support/auth'
import { fixtures, users } from '../support/fixtures'
import { chooseOverlayOption, selectWorkspace } from '../support/ui'

test.describe('orchestration', () => {
  test('orchestration page loads seeded workspace orchestration data', async ({
    page,
  }) => {
    await authenticateSession(page, users.owner.email, users.owner.password)

    await page.goto('/orchestration')
    await selectWorkspace(page, fixtures.workspaces.private.name)

    await expect(
      page.getByRole('navigation', { name: 'Job orchestration sections' })
    ).toBeVisible()
    await expect(
      page.getByRole('heading', {
        name: fixtures.orchestration.dataConnectionName,
      })
    ).toBeVisible()
    await expect(page.getByText(fixtures.orchestration.taskName)).toBeVisible()
  })

  test('orchestration status filters narrow the task list', async ({
    page,
  }) => {
    await authenticateSession(page, users.owner.email, users.owner.password)

    await page.goto('/orchestration')
    await selectWorkspace(page, fixtures.workspaces.private.name)

    const statusFilter = page.getByRole('button', {
      name: 'Filter by status',
    })
    await expect(statusFilter).toBeVisible()

    await statusFilter.click()
    await chooseOverlayOption(page, 'OK')
    await expect(
      page.getByRole('heading', { name: 'No tasks match your filter' })
    ).toBeVisible()

    await page.getByRole('button', { name: 'Clear search and filters' }).click()
    await expect(page.getByText(fixtures.orchestration.taskName)).toBeVisible()

    await page.getByRole('button', { name: /Filter by status/ }).click()
    await chooseOverlayOption(page, 'Loading paused')
    await expect(page.getByText(fixtures.orchestration.taskName)).toBeVisible()
  })

  test('orchestration workspace selection updates the visible systems and tasks', async ({
    page,
  }) => {
    await authenticateSession(page, users.owner.email, users.owner.password)
    await page.goto('/orchestration')
    await selectWorkspace(page, fixtures.workspaces.private.name)

    await expect(
      page.getByRole('heading', {
        name: fixtures.orchestration.dataConnectionName,
      })
    ).toBeVisible()
    await selectWorkspace(page, fixtures.workspaces.public.name)

    await expect(
      page.getByText(fixtures.orchestration.dataConnectionName)
    ).toHaveCount(0)

    await selectWorkspace(page, fixtures.workspaces.private.name)
    await expect(
      page.getByRole('heading', {
        name: fixtures.orchestration.dataConnectionName,
      })
    ).toBeVisible()
  })

  test('opening Edit on an existing ingestion task pre-populates its mappings', async ({
    page,
  }) => {
    await authenticateSession(page, users.owner.email, users.owner.password)

    await page.goto('/orchestration')
    await selectWorkspace(page, fixtures.workspaces.private.name)

    await expect(
      page.getByRole('heading', {
        name: fixtures.orchestration.dataConnectionName,
      })
    ).toBeVisible()
    await page.getByText(fixtures.orchestration.taskName).click()

    await expect(
      page.getByRole('heading', { name: fixtures.orchestration.taskName })
    ).toBeVisible()

    await page.getByRole('button', { name: 'Edit', exact: true }).click()

    const dialog = page.getByRole('dialog').filter({ hasText: 'Edit task' })
    await expect(dialog.getByText('Edit task')).toBeVisible()
    await expect(dialog.locator('input[value="test_value"]')).toBeVisible()
    await expect(
      dialog.getByText(fixtures.datastreams.privateWorkspacePublic.name)
    ).toBeVisible()
  })

  test('opening Edit on an existing aggregation task pre-populates its transformation', async ({
    page,
  }) => {
    await authenticateSession(page, users.owner.email, users.owner.password)

    await page.goto('/orchestration')
    await selectWorkspace(page, fixtures.workspaces.private.name)

    await page
      .getByTestId('nav-rail')
      .getByRole('button', { name: 'Aggregations & products' })
      .click()
    await page
      .getByRole('button', {
        name: `Select ${fixtures.monitoringSites.private.name}`,
      })
      .click()
    await page.getByText(fixtures.orchestration.aggregationTaskName).click()

    await expect(
      page.getByRole('heading', {
        name: fixtures.orchestration.aggregationTaskName,
      })
    ).toBeVisible()

    await page.getByRole('button', { name: 'Edit', exact: true }).click()

    const dialog = page
      .getByRole('dialog')
      .filter({ hasText: 'Edit aggregation task' })
    await expect(dialog.getByText('Edit aggregation task')).toBeVisible()
    await expect(dialog.getByText('Mean')).toBeVisible()
  })

  test('opening Edit on an existing quality task pre-populates its rules', async ({
    page,
  }) => {
    await authenticateSession(page, users.owner.email, users.owner.password)

    await page.goto('/orchestration')
    await selectWorkspace(page, fixtures.workspaces.private.name)

    await page
      .getByTestId('nav-rail')
      .getByRole('button', { name: 'Quality' })
      .click()
    await page
      .getByRole('button', {
        name: `Select ${fixtures.monitoringSites.private.name}`,
      })
      .click()
    await page.getByText(fixtures.orchestration.monitoringTaskName).click()

    await expect(
      page.getByRole('heading', {
        name: fixtures.orchestration.monitoringTaskName,
      })
    ).toBeVisible()

    await page.getByRole('button', { name: 'Edit', exact: true }).click()

    const dialog = page.getByRole('dialog')
    await expect(dialog.getByText('Edit')).toBeVisible()
  })
})
