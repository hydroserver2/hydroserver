import { expect, test } from '@playwright/test'

test.describe('general navigation', () => {
  test('root redirects to browse and the logo returns to browse from about', async ({
    page,
  }) => {
    await page.goto('/')
    await expect(page).toHaveURL(/\/browse$/)
    await expect(page.getByText('Browse data collection sites')).toBeVisible()

    await page.goto('/about')
    await expect(page.getByText(/About (HydroServer|us)/).first()).toBeVisible()

    await page.getByRole('link', { name: 'Logo', exact: true }).first().click()
    await expect(page).toHaveURL(/\/browse$/)
  })
})
