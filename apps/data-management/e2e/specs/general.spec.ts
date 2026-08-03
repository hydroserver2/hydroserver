import { expect, test } from '@playwright/test'

import { authenticateSession } from '../support/auth'
import { fixtures, users } from '../support/fixtures'

test.describe('general navigation', () => {
  test('root redirects to browse and the logo returns to browse from about', async ({
    page,
  }) => {
    await page.goto('/')
    await expect(page).toHaveURL(/\/browse$/)
    await expect(
      page.getByRole('heading', { name: 'Monitoring sites', level: 1 })
    ).toBeVisible()

    await page.goto('/about')
    await expect(page.getByText(/About (HydroServer|us)/).first()).toBeVisible()

    await page.getByRole('link', { name: 'Logo', exact: true }).first().click()
    await expect(page).toHaveURL(/\/browse$/)
  })

  test('browse page site type filter filters the site list and can be cleared', async ({
    page,
  }) => {
    await authenticateSession(page, users.owner.email, users.owner.password)
    await page.goto('/browse?siteTypes=Private')
    await expect(
      page.getByRole('heading', { name: 'Monitoring sites', level: 1 })
    ).toBeVisible()

    await expect(
      page.getByText(fixtures.things.private.name, { exact: true })
    ).toBeVisible()
    await expect(
      page.getByText(fixtures.things.public.name, { exact: true })
    ).toHaveCount(0)

    await page.getByRole('button', { name: 'Reset', exact: true }).click()
    await expect(
      page.getByText(fixtures.things.public.name, { exact: true })
    ).toBeVisible()
  })
})
