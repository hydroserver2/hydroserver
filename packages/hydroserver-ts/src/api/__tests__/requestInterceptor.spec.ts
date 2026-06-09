import { requestInterceptor } from '../requestInterceptor'
import { describe, it, expect } from 'vitest'

describe('requestInterceptor', () => {
  it('keeps string body as is', () => {
    const options = { body: 'test_string' }
    const result = requestInterceptor(options)
    expect(result.body).toBe('test_string')
  })

  it('stringifies object body', () => {
    const options = { body: { test: 'value' } }
    const result = requestInterceptor(options)
    expect(result.body).toBe('{"test":"value"}')
  })

  it('Preserves unmodified options while updating header and body', () => {
    const options = {
      headers: {
        'Existing-Header': 'Existing-Value',
      },
      body: { key: 'value' },
      method: 'GET',
      credentials: 'include',
    }

    const result = requestInterceptor(options)

    // Checking modified properties
    expect(result.body).toBe(JSON.stringify(options.body))

    // Checking properties that shouldn't be changed
    expect(new Headers(result.headers).get('Existing-Header')).toBe(
      'Existing-Value'
    )
    expect(result.method).toBe('GET')
    expect(result.credentials).toBe('include')
  })

  it('accepts standard HeadersInit values', () => {
    const result = requestInterceptor({
      headers: new Headers([['Existing-Header', 'Existing-Value']]),
    })

    expect(new Headers(result.headers).get('Existing-Header')).toBe(
      'Existing-Value'
    )
  })

  it('keeps native BodyInit values as is', () => {
    const body = new URLSearchParams({ test: 'value' })
    const result = requestInterceptor({ body })

    expect(result.body).toBe(body)
  })
})
