import { expect, test } from '@playwright/test'

import { login, requestBrowserSession } from '../support/auth'
import { users } from '../support/fixtures'

const API_BASE_URL = process.env.E2E_API_BASE_URL || 'http://127.0.0.1:18000'

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

    // Restore profile to original seeded state so retries start from a clean slate.
    await page.request.patch(`${API_BASE_URL}/api/auth/browser/account`, {
      data: {
        first_name: 'Profile',
        last_name: 'Example',
        type: 'Other',
        organization: {
          code: 'E2E',
          name: 'E2E Test Organization',
          description: 'Deterministic organization for browser profile tests.',
          link: 'https://example.com/org/e2e-profile',
          type: 'Other',
        },
      },
    })
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
