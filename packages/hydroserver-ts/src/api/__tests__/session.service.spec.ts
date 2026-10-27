import { afterEach, describe, expect, it, vi } from 'vitest'
import { HydroServer } from '../HydroServer'
import { apiMethods } from '../apiMethods'
import { registerCSRFCookieName } from '../getCSRFToken'
import {
  registerAccessTokenProvider,
  registerUnauthorizedHandler,
  requestInterceptor,
} from '../requestInterceptor'

afterEach(() => {
  registerAccessTokenProvider(null)
  registerUnauthorizedHandler(null)
  registerCSRFCookieName('csrftoken')
  vi.unstubAllGlobals()
})

describe('SessionService account URLs', () => {
  it('includes the app developer’s return destination', () => {
    const originalLocation = Object.getOwnPropertyDescriptor(globalThis, 'location')
    Object.defineProperty(globalThis, 'location', {
      configurable: true,
      value: { origin: 'https://app.example.test' },
    })

    const client = new HydroServer({ host: 'https://api.example.test' })

    try {
      expect(client.session.getAccountSignupUrl('/projects')).toBe(
        'https://api.example.test/accounts/signup/?next=https%3A%2F%2Fapp.example.test%2Fprojects'
      )
      expect(client.session.getAccountProfileUrl('/settings')).toBe(
        'https://api.example.test/accounts/profile/?next=https%3A%2F%2Fapp.example.test%2Fsettings'
      )
    } finally {
      if (originalLocation) {
        Object.defineProperty(globalThis, 'location', originalLocation)
      } else {
        Reflect.deleteProperty(globalThis, 'location')
      }
    }
  })

  it('uses the current app URL when a destination is not supplied', () => {
    const originalLocation = Object.getOwnPropertyDescriptor(globalThis, 'location')
    const originalWindow = Object.getOwnPropertyDescriptor(globalThis, 'window')
    const location = {
      origin: 'http://localhost:1203',
      pathname: '/workspaces',
      search: '?tab=metadata',
      hash: '#details',
    }
    Object.defineProperty(globalThis, 'location', {
      configurable: true,
      value: location,
    })
    Object.defineProperty(globalThis, 'window', {
      configurable: true,
      value: { location },
    })

    const client = new HydroServer({ host: 'http://127.0.0.1:8000' })

    try {
      expect(client.session.getAccountProfileUrl()).toBe(
        'http://127.0.0.1:8000/accounts/profile/?next=http%3A%2F%2Flocalhost%3A1203%2Fworkspaces%3Ftab%3Dmetadata%23details'
      )
    } finally {
      if (originalLocation) {
        Object.defineProperty(globalThis, 'location', originalLocation)
      } else {
        Reflect.deleteProperty(globalThis, 'location')
      }
      if (originalWindow) {
        Object.defineProperty(globalThis, 'window', originalWindow)
      } else {
        Reflect.deleteProperty(globalThis, 'window')
      }
    }
  })
})

describe('SessionService with an access token provider', () => {
  it('cannot be combined with OIDC options', () => {
    expect(
      () =>
        new HydroServer({
          host: 'https://api.example.test',
          oidc: { clientId: 'client' },
          accessTokenProvider: async () => 'token-123',
        })
    ).toThrow('cannot be used together')
  })

  it('reports token mode', () => {
    const client = new HydroServer({
      host: 'https://api.example.test',
      accessTokenProvider: async () => 'token-123',
    })

    expect(client.authMode).toBe('token')
  })

  it('authenticates from the token the provider returns', async () => {
    const provider = vi.fn().mockResolvedValue('token-123')
    const client = await HydroServer.initialize({
      host: 'https://api.example.test',
      accessTokenProvider: provider,
    })

    expect(provider).toHaveBeenCalledTimes(1)
    expect(client.session.isAuthenticated).toBe(true)
    expect(client.session.accessToken).toBe('token-123')
    expect(client.user.isAuthenticated).toBe(true)
  })

  it('is signed out when the provider has no token', async () => {
    const client = await HydroServer.initialize({
      host: 'https://api.example.test',
      accessTokenProvider: async () => null,
    })

    expect(client.session.isAuthenticated).toBe(false)
    expect(client.session.accessToken).toBeNull()
  })

  it('is signed out when the provider fails', async () => {
    const client = await HydroServer.initialize({
      host: 'https://api.example.test',
      accessTokenProvider: async () => {
        throw new Error('token endpoint unavailable')
      },
    })

    expect(client.session.isAuthenticated).toBe(false)
  })

  it('tracks the latest token returned by getAccessToken()', async () => {
    const tokens = ['token-1', 'token-2']
    const client = await HydroServer.initialize({
      host: 'https://api.example.test',
      accessTokenProvider: async () => tokens.shift() ?? null,
    })

    expect(await client.session.getAccessToken()).toBe('token-2')
    expect(client.session.accessToken).toBe('token-2')
  })

  it('leaves sign-in and sign-out to the host app', async () => {
    const client = new HydroServer({
      host: 'https://api.example.test',
      accessTokenProvider: async () => 'token-123',
    })

    await expect(client.session.login('/')).rejects.toThrow('managed by the host app')
    await expect(client.session.logout('/')).rejects.toThrow('managed by the host app')
  })
})

describe('HydroServer.initialize() request setup', () => {
  const endpoint = 'https://api.example.test/api/ogc/collections/workspaces/items/1'

  it('sends the bearer token from accessTokenProvider', async () => {
    await HydroServer.initialize({
      host: 'https://api.example.test',
      accessTokenProvider: async () => 'token-123',
    })
    const fetchMock = vi.fn().mockResolvedValue(new Response('{}', { status: 200 }))
    vi.stubGlobal('fetch', fetchMock)

    await apiMethods.fetch(endpoint)

    const [, init] = fetchMock.mock.calls[0]
    expect(new Headers(init.headers).get('Authorization')).toBe('Bearer token-123')
  })

  it('calls onUnauthorized when a token is rejected after a retry', async () => {
    const onUnauthorized = vi.fn()
    await HydroServer.initialize({
      host: 'https://api.example.test',
      accessTokenProvider: async () => 'revoked-token',
      onUnauthorized,
    })
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation(async () => new Response(null, { status: 401 }))
    )

    await apiMethods.fetch(endpoint)

    expect(onUnauthorized).toHaveBeenCalledTimes(1)
  })

  it('reads the configured CSRF cookie name', async () => {
    vi.stubGlobal('document', {
      cookie: 'csrftoken=other-app; hs_csrftoken=csrf-123',
    })
    await HydroServer.initialize({
      host: 'https://api.example.test',
      csrfCookieName: 'hs_csrftoken',
    })

    const result = await requestInterceptor({})

    expect(new Headers(result.headers).get('X-CSRFToken')).toBe('csrf-123')
  })
})
