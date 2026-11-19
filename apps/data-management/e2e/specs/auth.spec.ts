import { expect, test } from '../support/test'

import { login } from '../support/auth'
import { users } from '../support/fixtures'

test.describe('authentication', () => {
  test.use({ storageState: { cookies: [], origins: [] } })

  test('protected pages redirect anonymous users to login', async ({
    page,
  }) => {
    await page.goto('/orchestration')

    await expect(page).toHaveURL(/\/accounts\/login\/(?:\?.*)?$/)
    await expect(page.getByRole('button', { name: 'Sign In' })).toBeVisible()
    await expect(
      page.getByRole('button', { name: 'Quality control' })
    ).toHaveCount(0)
  })

  test('login with seeded owner user reaches Browse monitoring sites', async ({
    page,
  }) => {
    await page.setViewportSize({ width: 1100, height: 720 })
    await login(page, users.owner.email, users.owner.password)

    await expect(page).toHaveURL(/\/browse$/)
    await expect(
      page.getByRole('heading', { name: 'Monitoring sites', level: 1 })
    ).toBeVisible()
    await expect(page.getByTestId('register-site-button')).toBeEnabled()
    await expect(
      page.getByRole('button', { name: 'Quality control' })
    ).toBeVisible()
    const aboutLink = page.locator('header').getByRole('link', {
      name: 'About',
      exact: true,
    })
    await expect(aboutLink).toBeVisible()

    await page.setViewportSize({ width: 960, height: 720 })
    await expect(aboutLink).toBeHidden()
    await page.getByTestId('account-menu-button').click()
    await expect(page.getByTestId('about-menu-item')).toBeVisible()
    await page.keyboard.press('Escape')

    await page.setViewportSize({ width: 900, height: 720 })
    await expect(
      page.getByRole('button', { name: 'Quality control' })
    ).toHaveCount(0)
    await expect(page.getByTestId('mobile-nav-button')).toBeVisible()
    await page.getByTestId('mobile-nav-button').click()
    await expect(page.getByTestId('about-drawer-item')).toBeVisible()

    await page.setViewportSize({ width: 1100, height: 720 })
    await expect(aboutLink).toBeVisible()
  })

  test('authenticated users can log out from the account menu', async ({
    page,
  }) => {
    await login(page, users.owner.email, users.owner.password)
    await expect(page).toHaveURL(/\/browse$/)

    await page.getByTestId('account-menu-button').click()
    await expect(page.getByTestId('logout-menu-item')).toBeVisible()
    await Promise.all([
      page.waitForURL(/\/browse$/),
      page.getByTestId('logout-menu-item').click(),
    ])

    await expect(page).toHaveURL(/\/browse$/)
    await expect(page.getByRole('button', { name: 'Log in' })).toBeVisible()
  })
})
