import {
  registerAccessTokenProvider,
  requestInterceptor,
} from '../requestInterceptor'
import { afterEach, describe, expect, it } from 'vitest'

afterEach(() => {
  registerAccessTokenProvider(null)
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

    expect(result.headers.Authorization).toBe('Bearer token-123')
  })

  it('Preserves unmodified options while updating header and body', async () => {
    const options = {
      headers: {
        'Existing-Header': 'Existing-Value',
      },
      body: { key: 'value' },
      method: 'GET',
    }

    const result = await requestInterceptor(options)

    // Checking modified properties
    expect(result.body).toBe(JSON.stringify(options.body))

    // Checking properties that shouldn't be changed
    expect(result.headers['Existing-Header']).toBe('Existing-Value')
    expect(result.method).toBe('GET')
    expect(result.credentials).toBeUndefined()
  })
})
