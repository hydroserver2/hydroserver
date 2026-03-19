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

  test('browse page site type filter filters the site list and can be cleared', async ({
    page,
  }) => {
    await page.goto('/browse')
    await expect(page.getByText('Browse data collection sites')).toBeVisible()

    const siteTypeFilter = page
      .getByRole('combobox', { name: /site type/i })
      .first()
    await expect(siteTypeFilter).toBeVisible()

    await siteTypeFilter.click()
    await siteTypeFilter.fill('Lake')
    await siteTypeFilter.press('Enter')

    await page.getByRole('button', { name: /clear/i }).first().click()
    await expect(siteTypeFilter).toBeEmpty()
  })
})
