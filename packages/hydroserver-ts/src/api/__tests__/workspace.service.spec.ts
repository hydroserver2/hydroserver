import { afterEach, describe, expect, it, vi } from 'vitest'
import { HydroServer } from '../HydroServer'

describe('WorkspaceService', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('expands API key roles used by the workspace management table', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify([]), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      })
    )
    vi.stubGlobal('fetch', fetchMock)

    const client = new HydroServer({ host: 'https://hydro.example.com' })
    await client.workspaces.getApiKeys('workspace-1')

    expect(fetchMock.mock.calls[0][0]).toBe(
      'https://hydro.example.com/api/data/workspaces/workspace-1/api-keys?expand_related=true'
    )
  })
})
