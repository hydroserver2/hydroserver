import { flushPromises, shallowMount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const {
  loginMock,
  replaceMock,
  initializeAuthenticatedStateMock,
  sessionState,
} = vi.hoisted(() => ({
  loginMock: vi.fn(),
  replaceMock: vi.fn(),
  initializeAuthenticatedStateMock: vi.fn(),
  sessionState: {
    isAuthenticated: false,
  },
}))

vi.mock('@hydroserver/client', () => ({
  default: {
    session: {
      get isAuthenticated() {
        return sessionState.isAuthenticated
      },
      login: loginMock,
    },
  },
}))

vi.mock('@/router/router', () => ({
  default: {
    replace: replaceMock,
  },
}))

vi.mock('@/bootstrap/appInitialization', () => ({
  initializeAuthenticatedState: initializeAuthenticatedStateMock,
}))

describe('AuthHandoff page', () => {
  beforeEach(() => {
    loginMock.mockReset()
    replaceMock.mockReset()
    initializeAuthenticatedStateMock.mockReset()
    sessionState.isAuthenticated = false
    window.history.replaceState({}, '', '/auth/handoff')
  })

  it('starts the OIDC login flow with the original app route when not authenticated', async () => {
    loginMock.mockResolvedValue(undefined)
    window.history.replaceState(
      {},
      '',
      '/auth/handoff?returnTo=http%3A%2F%2Flocalhost%3A3000%2Forchestration%3FworkspaceId%3Dabc%23runs'
    )

    const component = (await import('../AuthHandoff.vue')).default
    shallowMount(component)
    await flushPromises()

    expect(loginMock).toHaveBeenCalledWith('/orchestration?workspaceId=abc#runs')
    expect(initializeAuthenticatedStateMock).not.toHaveBeenCalled()
    expect(replaceMock).not.toHaveBeenCalled()
  })

  it('rehydrates app state and routes directly when already authenticated', async () => {
    sessionState.isAuthenticated = true
    initializeAuthenticatedStateMock.mockResolvedValue(undefined)
    replaceMock.mockResolvedValue(undefined)
    window.history.replaceState(
      {},
      '',
      '/auth/handoff?returnTo=http%3A%2F%2Flocalhost%3A3000%2Fsites'
    )

    const component = (await import('../AuthHandoff.vue')).default
    shallowMount(component)
    await flushPromises()

    expect(initializeAuthenticatedStateMock).toHaveBeenCalledTimes(1)
    expect(replaceMock).toHaveBeenCalledWith('/sites')
    expect(loginMock).not.toHaveBeenCalled()
  })

  it('falls back to the app root for cross-origin return targets', async () => {
    loginMock.mockResolvedValue(undefined)
    window.history.replaceState(
      {},
      '',
      '/auth/handoff?returnTo=https%3A%2F%2Fmalicious.example.com%2Fsteal'
    )

    const component = (await import('../AuthHandoff.vue')).default
    shallowMount(component)
    await flushPromises()

    expect(loginMock).toHaveBeenCalledWith('/')
  })
})
