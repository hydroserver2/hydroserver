import { describe, it, expect, beforeEach, vi } from 'vitest'
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

import { leaveSessionGuard } from '@/router/guards'

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
