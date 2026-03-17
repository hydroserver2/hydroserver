import { expect, test } from '@playwright/test'

import { login, requestBrowserSession } from '../support/auth'
import { users } from '../support/fixtures'

test.describe('account management', () => {
  test.use({ storageState: { cookies: [], origins: [] } })

  test('user with no workspaces lands on your sites and sees onboarding guidance', async ({
    page,
  }) => {
    await login(page, users.deleteMe.email, users.deleteMe.password)

    await expect(page).toHaveURL(/\/sites$/)
    await expect(page.getByText('No workspaces found')).toBeVisible()
    await expect(
      page.getByText('Click the "Add workspace" button to create one.')
    ).toBeVisible()
  })

  test('profile editing can remove organization details', async ({ page }) => {
    await login(page, users.profile.email, users.profile.password)
    await expect(page).toHaveURL(/\/sites$/)

    await page.goto('/profile')
    await expect(
      page.getByRole('heading', { name: 'User information' })
    ).toBeVisible()
    await expect(
      page.getByRole('heading', { name: 'Organization information' })
    ).toBeVisible()

    await page.getByRole('button', { name: 'Edit account' }).click()
    await page.getByLabel('First Name *').fill('Profile Updated')
    await page.getByLabel('Affiliated with an Organization').click()

    await expect(
      page.getByText('Warning: Disabling organization affiliation')
    ).toBeVisible()

    await page.getByRole('button', { name: 'Save' }).click()

    await expect(page.getByText('Profile Updated Example')).toBeVisible()
    await expect(
      page.getByRole('heading', { name: 'Organization information' })
    ).toHaveCount(0)
  })

  test('account deletion removes the user session and invalidates login', async ({
    page,
  }) => {
    await login(page, users.deleteMe.email, users.deleteMe.password)
    await expect(page).toHaveURL(/\/sites$/)

    await page.goto('/profile')
    await page.getByRole('button', { name: 'Delete Account' }).click()
    await page.getByRole('textbox').fill('delete my account and data')
    await page.getByRole('button', { name: 'Delete', exact: true }).click()

    await expect(page).toHaveURL(/\/login$/)

    const response = await requestBrowserSession(
      page,
      users.deleteMe.email,
      users.deleteMe.password
    )
    expect(response.ok()).toBeFalsy()
  })
})
