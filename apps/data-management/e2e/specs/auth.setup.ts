import { expect, test } from '@playwright/test'

import { login } from '../support/auth'
import { users } from '../support/fixtures'

test('authenticate owner user and persist storage state', async ({ page }) => {
  await login(page, users.owner.email, users.owner.password)

  await expect(page).toHaveURL(/\/browse$/)
  await expect(
    page.getByRole('heading', { name: 'Monitoring sites', level: 1 })
  ).toBeVisible()
  await expect(page.getByTestId('register-site-button')).toBeEnabled()
})
