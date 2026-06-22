import { expect, type Cookie, type Page } from '@playwright/test'

const APP_BASE_URL = process.env.E2E_APP_BASE_URL || 'http://127.0.0.1:14173'
const API_BASE_URL = process.env.E2E_API_BASE_URL || 'http://127.0.0.1:18000'

function parseSetCookie(header: string): Cookie {
  const [nameValue, ...attributes] = header.split(';').map((part) => part.trim())
  const [name, ...valueParts] = nameValue.split('=')
  const cookie: Cookie = {
    name,
    value: valueParts.join('='),
    domain: '127.0.0.1',
    path: '/',
    httpOnly: false,
    secure: false,
    sameSite: 'Lax',
  }

  for (const attribute of attributes) {
    const [rawKey, ...rawValueParts] = attribute.split('=')
    const key = rawKey.toLowerCase()
    const value = rawValueParts.join('=')

    if (key === 'path' && value) cookie.path = value
    if (key === 'domain' && value) cookie.domain = value
    if (key === 'httponly') cookie.httpOnly = true
    if (key === 'secure') cookie.secure = true
    if (key === 'samesite' && value) {
      const normalized =
        value.toLowerCase() === 'strict'
          ? 'Strict'
          : value.toLowerCase() === 'none'
          ? 'None'
          : 'Lax'
      cookie.sameSite = normalized
    }
    if (key === 'expires' && value) {
      const expiresAt = Date.parse(value)
      if (Number.isFinite(expiresAt)) cookie.expires = expiresAt / 1000
    }
  }

  return cookie
}

export async function login(page: Page, email: string, password: string) {
  await page.goto('/login')
  await page.getByLabel('Email *').fill(email)
  await page.getByLabel('Password *').fill(password)
  await page.getByRole('button', { name: 'Log in' }).click()
}

export async function authenticateSession(
  page: Page,
  email: string,
  password: string
) {
  let response = await requestBrowserSession(page, email, password)

  for (let attempt = 0; response.status() === 429 && attempt < 5; attempt += 1) {
    await page.waitForTimeout(250 * (attempt + 1))
    response = await requestBrowserSession(page, email, password)
  }

  expect(response.ok()).toBeTruthy()

  const cookies = response
    .headersArray()
    .filter((header) => header.name.toLowerCase() === 'set-cookie')
    .map((header) => parseSetCookie(header.value))

  await page.context().addCookies(
    cookies.map((cookie) => ({
      name: cookie.name,
      value: cookie.value,
      url: APP_BASE_URL,
      httpOnly: cookie.httpOnly,
      secure: cookie.secure,
      sameSite: cookie.sameSite,
      expires: cookie.expires,
    }))
  )
}

export async function requestBrowserSession(
  page: Page,
  email: string,
  password: string
) {
  return page.request.post(
    `${API_BASE_URL}/api/auth/browser/session`,
    {
      data: { email, password },
      failOnStatusCode: false,
    }
  )
}
