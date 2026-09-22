import { afterEach, describe, expect, it, vi } from 'vitest'
import { HydroServer } from '../HydroServer'

const jsonResponse = (data: unknown, headers: Record<string, string> = {}) =>
  new Response(JSON.stringify(data), {
    status: 200,
    headers: { 'Content-Type': 'application/json', ...headers },
  })

describe('QualityControlSessionService query params', () => {
  afterEach(() => vi.restoreAllMocks())

  it('sends expand_related on the sessions list', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse([], { 'X-Total-Pages': '1' })
    )
    vi.stubGlobal('fetch', fetchMock)

    const hs = new HydroServer({ host: 'https://example.org' })
    await hs.qualityControlSessions.listAllItems('h-1', {
      expand_related: true,
    })

    const url = String(fetchMock.mock.calls[0]![0])
    console.log('LIST URL:', url)
    expect(url).toContain('expand_related=true')
  })

  it('sends expand_related on a single session read', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ id: 's-1' }))
    vi.stubGlobal('fetch', fetchMock)

    const hs = new HydroServer({ host: 'https://example.org' })
    await hs.qualityControlSessions.getItem('h-1', 's-1', {
      expand_related: true,
    })

    const url = String(fetchMock.mock.calls[0]![0])
    console.log('GET URL:', url)
    expect(url).toContain('expand_related=true')
  })
})
