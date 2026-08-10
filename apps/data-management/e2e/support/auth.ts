import type { Page } from '@playwright/test'

const APP_BASE_URL = process.env.E2E_APP_BASE_URL || 'http://127.0.0.1:14173'
const API_BASE_URL = process.env.E2E_API_BASE_URL || 'http://127.0.0.1:18000'

export async function login(page: Page, email: string, password: string) {
  const loginUrl = new URL('/accounts/login/', API_BASE_URL)
  loginUrl.searchParams.set('next', `${APP_BASE_URL}/browse`)

  await page.goto(loginUrl.toString())
  await page.getByLabel('Email').fill(email)
  await page.getByLabel('Password').fill(password)
  await page.getByRole('button', { name: 'Sign In' }).click()
}

export async function authenticateSession(
  page: Page,
  email: string,
  password: string
) {
  await login(page, email, password)
}
