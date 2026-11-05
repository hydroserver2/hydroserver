import { describe, expect, it, vi } from 'vitest'
import { installProfileFixtureTransport } from '../profileFixtureTransport'
import { profileFixtureResponse } from '../../../dev/profileFixtures'

const bootstrap = '/api/ogc/collections/datastreams/visualization-bootstrap'
const fixturePrefix = '/__fixtures/profiles'
function transport(body: unknown = {}) {
  const originalFetch = vi.fn(
    async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = new URL(String(input), 'http://localhost:1203')
      if (url.pathname.startsWith(fixturePrefix)) {
        if (init?.method && init.method !== 'GET')
          return Response.json(
            { message: 'Read-only fixtures' },
            { status: 405 }
          )
        url.pathname = url.pathname.slice(fixturePrefix.length)
        const fixture = profileFixtureResponse(url)
        return Response.json(fixture.body, { status: fixture.status })
      }
      return Response.json(body)
    }
  )
  const target = {
    fetch: originalFetch,
    location: { origin: 'http://localhost:1203' },
  } as unknown as Pick<Window, 'fetch' | 'location'>
  installProfileFixtureTransport(target)
  return { fetch: target.fetch, originalFetch }
}

describe('development profile fixture transport', () => {
  it('adds four profile datastreams alongside real data, with metadata and no duplicates', async () => {
    const real = { id: 'real-stream', type: 'timeSeriesCoverage' }
    const body = {
      data: {
        datastreams: [real, { id: 'profile-oxygen', type: 'profileCoverage' }],
        monitoringSites: [{ id: 'real-site' }],
        observedProperties: [],
        processingLevels: [],
      },
      meta: { retained: true },
    }
    const client = transport(body)
    const response = await client.fetch(`http://localhost:8000${bootstrap}`)
    const result = await response.json()
    expect(result.data.datastreams).toContainEqual(real)
    expect(
      result.data.datastreams.filter(
        (row: { id: string }) => row.id === 'profile-oxygen'
      )
    ).toHaveLength(1)
    expect(
      result.data.datastreams.filter(
        (row: { type: string }) => row.type === 'profileCoverage'
      )
    ).toHaveLength(4)
    expect(result.data.datastreams).toHaveLength(6)
    expect(
      result.data.monitoringSites.map((site: { id: string }) => site.id)
    ).toEqual(['real-site', 'profile-demo'])
    expect(result.meta).toEqual({ retained: true })
  })

  it('routes synthetic site, datastream, and metadata requests to local fixtures', async () => {
    const client = transport()
    const response = await client.fetch(
      'http://localhost:8000/api/ogc/collections/datastreams/items/profile-oxygen?include=workspace'
    )
    const body = await response.json()
    expect(body.data.type).toBe('profileCoverage')
    expect(body.included.workspaces[0].id).toBe('profile-demo')
    expect(client.originalFetch).toHaveBeenCalledWith(
      expect.stringContaining(fixturePrefix),
      expect.anything()
    )
    const metadata = await client.fetch(
      '/api/ogc/collections/units/items?workspaceId=profile-demo,null'
    )
    expect((await metadata.json()).data.length).toBeGreaterThan(0)
  })

  it('leaves real reads and writes alone while rejecting writes to fixture IDs', async () => {
    const client = transport({ real: true })
    const input =
      'http://localhost:8000/api/ogc/collections/datastreams/items/real-stream'
    const options = {
      method: 'PATCH',
      body: JSON.stringify({ name: 'Real stream' }),
      credentials: 'include' as const,
    }
    await client.fetch(input, options)
    expect(client.originalFetch).toHaveBeenCalledWith(input, options)
    const response = await client.fetch(
      '/api/ogc/collections/datastreams/items/profile-oxygen',
      options
    )
    expect(response.status).toBe(405)
    expect(client.originalFetch).not.toHaveBeenCalledWith(
      expect.stringContaining(
        '/api/ogc/collections/datastreams/items/profile-oxygen'
      ),
      options
    )
  })

  it('preserves live data when the fixture endpoint is unavailable', async () => {
    const body = {
      datastreams: [{ id: 'real' }],
      monitoringSites: [],
      observedProperties: [],
      processingLevels: [],
    }
    const client = transport(body)
    client.originalFetch.mockImplementation(async (input) => {
      if (String(input).startsWith(fixturePrefix))
        throw new Error('Fixture server unavailable')
      return Response.json(body)
    })
    expect(await (await client.fetch(bootstrap)).json()).toEqual(body)
  })
})
