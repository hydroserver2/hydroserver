import { afterEach, describe, expect, it, vi } from 'vitest'
import { getCSRFToken, registerCSRFCookieName } from '../getCSRFToken'

afterEach(() => {
  registerCSRFCookieName('csrftoken')
  vi.unstubAllGlobals()
})

describe('getCSRFToken', () => {
  it('reads the csrftoken cookie by default', () => {
    vi.stubGlobal('document', { cookie: 'other=1; csrftoken=csrf-123' })

    expect(getCSRFToken()).toBe('csrf-123')
  })

  it('reads the configured cookie name', () => {
    vi.stubGlobal('document', {
      cookie: 'csrftoken=other-app; hs_csrftoken=csrf-123',
    })
    registerCSRFCookieName('hs_csrftoken')

    expect(getCSRFToken()).toBe('csrf-123')
  })

  it('ignores a csrftoken cookie when another name is configured', () => {
    vi.stubGlobal('document', { cookie: 'csrftoken=other-app' })
    registerCSRFCookieName('hs_csrftoken')

    expect(getCSRFToken()).toBeNull()
  })
})
