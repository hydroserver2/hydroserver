import { expect, test } from '@playwright/test'

import { authenticateSession } from '../support/auth'
import { fixtures, users } from '../support/fixtures'
import { chooseOverlayOption } from '../support/ui'

test.describe('orchestration', () => {
  test('orchestration page loads seeded workspace orchestration data', async ({
    page,
  }) => {
    await authenticateSession(page, users.owner.email, users.owner.password)

    await page.goto(`/orchestration?workspaceId=${fixtures.workspaces.private.id}`)

    await expect(page.getByText('Job orchestration', { exact: true })).toBeVisible()
    await expect(page.getByText(fixtures.orchestration.systemName)).toBeVisible()
    await page
      .getByRole('button', { name: new RegExp(fixtures.orchestration.systemName) })
      .click()
    await expect(
      page.getByText(fixtures.orchestration.taskName)
    ).toBeVisible()
  })

  test('orchestration status filters narrow the task list', async ({
    page,
  }) => {
    await authenticateSession(page, users.owner.email, users.owner.password)

    await page.goto(`/orchestration?workspaceId=${fixtures.workspaces.private.id}`)

    await expect(page.getByText('Job orchestration', { exact: true })).toBeVisible()

    const statusFilter = page.getByRole('combobox', { name: 'Status filters' }).first()
    await expect(statusFilter).toBeVisible()

    await statusFilter.click()
    await chooseOverlayOption(page, 'OK')
    await expect(
      page.getByRole('heading', { name: 'No tasks match your search/filter.' })
    ).toBeVisible()

    await page.getByRole('button', { name: 'Clear Status filters' }).click()
    await page
      .getByRole('button', {
        name: new RegExp(fixtures.orchestration.systemName),
      })
      .click()
    await expect(page.getByText(fixtures.orchestration.taskName)).toBeVisible()

    await statusFilter.click()
    await chooseOverlayOption(page, 'Loading paused')
    await expect(page.getByText(fixtures.orchestration.taskName)).toBeVisible()
  })
})
