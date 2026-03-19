import { expect, test } from '@playwright/test'

import { login } from '../support/auth'
import { users } from '../support/fixtures'

test.describe('authentication', () => {
  test.use({ storageState: { cookies: [], origins: [] } })

  test('protected pages redirect anonymous users to login', async ({ page }) => {
    await page.goto('/sites')

    await expect(page).toHaveURL(/\/login(?:\?.*)?$/)
    await expect(
      page.locator('main').getByRole('button', { name: 'Log in' })
    ).toBeVisible()
  })

  test('login with seeded owner user reaches the sites page', async ({ page }) => {
    await login(page, users.owner.email, users.owner.password)

    await expect(page).toHaveURL(/\/sites$/)
    await expect(page.getByText('Your registered sites')).toBeVisible()
    await expect(
      page.getByText('Selected workspace:', { exact: false })
    ).toBeVisible()
  })

  test('authenticated users can log out from the account menu', async ({ page }) => {
    await login(page, users.owner.email, users.owner.password)
    await expect(page).toHaveURL(/\/sites$/)

    await page.getByTestId('account-menu-button').click()
    await expect(page.getByTestId('logout-menu-item')).toBeVisible()
    await Promise.all([
      page.waitForURL(/\/login(?:\?.*)?$/),
      page.getByTestId('logout-menu-item').click(),
    ])

    await expect(page).toHaveURL(/\/login(?:\?.*)?$/)
    await expect(
      page.locator('main').getByRole('button', { name: 'Log in' })
    ).toBeVisible()
  })
})
