import { expect, test } from '../support/test'

import { login } from '../support/auth'
import { users } from '../support/fixtures'

test.describe('account management', () => {
  test.use({ storageState: { cookies: [], origins: [] } })

  test('user with no workspaces lands on Browse with site registration disabled', async ({
    page,
  }) => {
    await login(page, users.deleteMe.email, users.deleteMe.password)

    await expect(page).toHaveURL(/\/browse$/)
    await expect(
      page.getByRole('heading', { name: 'Monitoring sites', level: 1 })
    ).toBeVisible()
    await expect(page.getByTestId('register-site-button')).toBeDisabled()
  })

  test('account menu opens the profile page and profile editing can remove organization details', async ({
    page,
  }) => {
    await login(page, users.profile.email, users.profile.password)
    await expect(page).toHaveURL(/\/browse$/)

    await page.getByTestId('account-menu-button').click()
    await page.getByTestId('account-menu-item').click()
    await expect(page).toHaveURL(/\/accounts\/profile\/$/)
    await expect(page.getByRole('heading', { name: 'Profile' })).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Organization' })).toBeVisible()

    await page.getByRole('link', { name: 'Edit' }).click()
    await page.getByLabel('First name').fill('Profile Updated')
    await page.getByRole('checkbox', { name: 'Organization Affiliation' }).uncheck()
    await page.getByRole('button', { name: 'Save Changes' }).click()

    await expect(page.getByText('Profile Updated Example')).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Organization' })).toHaveCount(0)
  })

  test('account deletion removes the user session and invalidates login', async ({
    page,
  }) => {
    await login(page, users.deleteMe.email, users.deleteMe.password)
    await expect(page).toHaveURL(/\/browse$/)

    await page.goto('/profile')
    await page.getByRole('link', { name: 'Delete Account' }).click()
    await page.getByLabel('Type "delete my account and data" to confirm').fill(
      'delete my account and data'
    )
    await page.getByRole('button', { name: 'Delete My Account' }).click()

    await expect(page).toHaveURL(/\/accounts\/login\/$/)

    await page.getByLabel('Email').fill(users.deleteMe.email)
    await page.getByLabel('Password').fill(users.deleteMe.password)
    await page.getByRole('button', { name: 'Sign In' }).click()
    await expect(page).toHaveURL(/\/accounts\/login\/$/)
    await expect(page.getByRole('button', { name: 'Sign In' })).toBeVisible()
  })
})
