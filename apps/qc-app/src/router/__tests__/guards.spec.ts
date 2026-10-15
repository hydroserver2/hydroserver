import { describe, it, expect, beforeAll, beforeEach, vi } from 'vitest'
import { createTestPinia } from '@/utils/test/pinia'
import type { RouteLocationNormalized } from 'vue-router'

const { requestLeave, forgetSession } = vi.hoisted(() => ({
  requestLeave: vi.fn(),
  forgetSession: vi.fn(),
}))

vi.mock('@/composables/useLeaveSession', () => ({
  useLeaveSession: () => ({ requestLeave, forgetSession }),
}))

vi.mock('@hydroserver/client', () => ({ default: { session: {} } }))

vi.mock('@/store/workspaces', () => ({
  useWorkspaceStore: () => ({
    selectedWorkspaceId: 'ws-1',
    hasSelection: true,
    applyWorkspaceById: vi.fn(),
  }),
}))

vi.mock('@/router/routes', () => ({
  routes: [
    { path: '/', name: 'Home', component: {}, meta: { title: 'Home' } },
    {
      path: '/workspaces',
      name: 'Workspaces',
      component: {},
      meta: { title: 'Workspaces' },
    },
  ],
}))

import { leaveSessionGuard } from '@/router/guards'
import { isLeavingPage } from '@/router/navigationState'
import router, { setupRouteGuards } from '@/router/router'

const route = (name: string | undefined, query: Record<string, string> = {}) =>
  ({ name, query, meta: {}, fullPath: '/' }) as unknown as RouteLocationNormalized

beforeEach(() => {
  createTestPinia()
  vi.clearAllMocks()
  requestLeave.mockResolvedValue(true)
})

describe('leaveSessionGuard', () => {
  it('asks before navigating away from the editor', async () => {
    expect(await leaveSessionGuard(route('Workspaces'), route('Home'))).toBe(
      null
    )
    expect(requestLeave).toHaveBeenCalled()
    expect(forgetSession).toHaveBeenCalled()
  })

  it('cancels the navigation when the user stays', async () => {
    requestLeave.mockResolvedValueOnce(false)
    expect(await leaveSessionGuard(route('Workspaces'), route('Home'))).toBe(
      false
    )
    expect(forgetSession).not.toHaveBeenCalled()
  })

  // A route replace before this navigation lands would cancel it.
  it('holds the URL writer from asking on, when the user leaves', async () => {
    let reply!: (v: boolean) => void
    requestLeave.mockReturnValueOnce(new Promise((r) => (reply = r)))
    const guarded = leaveSessionGuard(route('Workspaces'), route('Home'))
    expect(isLeavingPage.value).toBe(true)
    reply(true)
    await guarded
    // Released by the router once the navigation lands.
    expect(isLeavingPage.value).toBe(true)
    isLeavingPage.value = false
  })

  it('releases the URL writer when the user stays', async () => {
    requestLeave.mockResolvedValueOnce(false)
    await leaveSessionGuard(route('Workspaces'), route('Home'))
    expect(isLeavingPage.value).toBe(false)
  })

  it('releases the URL writer when asking fails', async () => {
    requestLeave.mockRejectedValueOnce(new Error('boom'))
    await expect(
      leaveSessionGuard(route('Workspaces'), route('Home'))
    ).rejects.toThrow('boom')
    expect(isLeavingPage.value).toBe(false)
  })

  // The editor rewrites its own URL constantly; that is not an exit.
  it('ignores a new URL for the page it is already on', async () => {
    expect(
      await leaveSessionGuard(route('Home', { ds: 'a' }), route('Home'))
    ).toBe(null)
    expect(requestLeave).not.toHaveBeenCalled()
  })

  // The flow answers "nothing to decide" itself, so the guard needs no
  // knowledge of which page holds the editor.
  it('consults the flow on any change of page', async () => {
    expect(await leaveSessionGuard(route('Home'), route('Workspaces'))).toBe(
      null
    )
    expect(requestLeave).toHaveBeenCalled()
  })

  it('ignores the first navigation of the session', async () => {
    expect(await leaveSessionGuard(route('Home'), route(undefined))).toBe(null)
    expect(requestLeave).not.toHaveBeenCalled()
  })
})

describe('route guard order', () => {
  beforeAll(() => setupRouteGuards())

  beforeEach(async () => {
    requestLeave.mockResolvedValue(true)
    await router.push('/')
    vi.clearAllMocks()
  })

  // The picker sends a user with a workspace straight back, so this
  // navigation never leaves the editor and must not end the session.
  it('does not ask about a navigation another guard redirects back', async () => {
    await router.push('/workspaces')

    expect(router.currentRoute.value.name).toBe('Home')
    expect(requestLeave).not.toHaveBeenCalled()
  })

  it('asks about a navigation that leaves the page', async () => {
    await router.push('/workspaces?switch=1')

    expect(requestLeave).toHaveBeenCalledOnce()
    expect(router.currentRoute.value.name).toBe('Workspaces')
    expect(isLeavingPage.value).toBe(false)
  })

  it('keeps the page title when the user stays', async () => {
    requestLeave.mockResolvedValueOnce(false)
    await router.push('/workspaces?switch=1')

    expect(router.currentRoute.value.name).toBe('Home')
    expect(document.title).toBe('HydroServer | Home')
  })
})
