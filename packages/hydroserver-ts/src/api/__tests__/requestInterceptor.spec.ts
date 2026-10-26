import {
  registerAccessTokenProvider,
  requestInterceptor,
} from '../requestInterceptor'
import { afterEach, describe, expect, it, vi } from 'vitest'

afterEach(() => {
  registerAccessTokenProvider(null)
  vi.unstubAllGlobals()
})

describe('requestInterceptor', () => {
  it('keeps string body as is', async () => {
    const options = { body: 'test_string' }
    const result = await requestInterceptor(options)
    expect(result.body).toBe('test_string')
  })

  it('stringifies object body', async () => {
    const options = { body: { test: 'value' } }
    const result = await requestInterceptor(options)
    expect(result.body).toBe('{"test":"value"}')
  })

  it('adds an authorization header when a token is available', async () => {
    registerAccessTokenProvider(async () => 'token-123')

    const result = await requestInterceptor({})

    expect(new Headers(result.headers).get('Authorization')).toBe(
      'Bearer token-123'
    )
  })

  it('adds a CSRF header from the cookie when no token provider is registered', async () => {
    vi.stubGlobal('document', { cookie: 'csrftoken=csrf-123' })

    const result = await requestInterceptor({})

    expect(new Headers(result.headers).get('X-CSRFToken')).toBe('csrf-123')
    expect(result.credentials).toBe('include')
  })

  it('omits the CSRF header and cookies when sending a token', async () => {
    vi.stubGlobal('document', { cookie: 'csrftoken=csrf-123' })
    registerAccessTokenProvider(async () => 'token-123')

    const result = await requestInterceptor({})

    expect(new Headers(result.headers).get('X-CSRFToken')).toBeNull()
    expect(result.credentials).toBe('omit')
  })

  it.each([
    ['returns no token', async () => null],
    [
      'fails',
      async () => {
        throw new Error('token endpoint unavailable')
      },
    ],
  ])('does not fall back to cookies when the provider %s', async (_, provider) => {
    vi.stubGlobal('document', { cookie: 'csrftoken=csrf-123' })
    registerAccessTokenProvider(provider)

    const result = await requestInterceptor({})

    const headers = new Headers(result.headers)
    expect(headers.get('Authorization')).toBeNull()
    expect(headers.get('X-CSRFToken')).toBeNull()
    expect(result.credentials).toBe('omit')
  })

  it('Preserves unmodified options while updating header and body', async () => {
    const options = {
      headers: {
        'Existing-Header': 'Existing-Value',
      },
      body: { key: 'value' },
      method: 'GET',
      credentials: 'include',
    }

    const result = await requestInterceptor(options)

    // Checking modified properties
    expect(result.body).toBe(JSON.stringify(options.body))

    // Checking properties that shouldn't be changed
    expect(new Headers(result.headers).get('Existing-Header')).toBe(
      'Existing-Value'
    )
    expect(result.method).toBe('GET')
    expect(result.credentials).toBe('include')
  })

  it('accepts standard HeadersInit values', async () => {
    const result = await requestInterceptor({
      headers: new Headers([['Existing-Header', 'Existing-Value']]),
    })

    expect(new Headers(result.headers).get('Existing-Header')).toBe(
      'Existing-Value'
    )
  })

  it('keeps native BodyInit values as is', async () => {
    const body = new URLSearchParams({ test: 'value' })
    const result = await requestInterceptor({ body })

    expect(result.body).toBe(body)
  })
})
