import { afterEach, describe, expect, it, vi } from 'vitest'
import { HydroServer } from '../HydroServer'
import { MonitoringSite, Datastream, ObservedProperty, ProcessingLevel } from '../../types'

const jsonResponse = (data: unknown, status = 200) =>
  new Response(JSON.stringify(data), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })

describe('MonitoringSiteService', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  const client = new HydroServer({ host: 'https://hydro.example.com' })

  describe('listMarkers', () => {
    it('fetches monitoringSite markers and returns them in data', async () => {
      const payload = [
        {
          id: 'monitoringSite-1',
          workspaceId: 'workspace-1',
          name: 'Site 1',
          type: 'Stream',
          isPrivate: false,
          latitude: 41.7,
          longitude: -111.8,
        },
      ]

      vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(payload)))

      const res = await client.monitoringSites.listMarkers()

      expect(res.ok).toBe(true)
      expect(res.data).toEqual(payload)
      const [url] = (fetch as any).mock.calls[0]
      expect(url).toMatch(/\/api\/data\/monitoring-sites\/markers$/)
    })

    it('returns ok:false on a failed request', async () => {
      vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse({ detail: 'error' }, 503)))

      const res = await client.monitoringSites.listMarkers()

      expect(res.ok).toBe(false)
      expect(res.status).toBe(503)
    })
  })

  describe('createItem / updateItem / tags / privacy', () => {
    it('createItem returns the fully re-fetched site, not just the {id} the POST returned', async () => {
      const fetchMock = vi.fn().mockImplementation(async (input: string | URL, init?: RequestInit) => {
        if (init?.method === 'POST') return jsonResponse({ id: 'monitoringSite-1' }, 201)
        return jsonResponse({
          data: { id: 'monitoringSite-1', workspaceId: 'ws-1', name: 'New Site', code: 'SF-1' },
          included: {},
        })
      })
      vi.stubGlobal('fetch', fetchMock)

      const site = new MonitoringSite()
      site.name = 'New Site'
      const result = await client.monitoringSites.createItem(site)

      expect(fetchMock).toHaveBeenCalledTimes(2)
      expect(result?.name).toBe('New Site')
      expect(result?.id).toBe('monitoringSite-1')
    })

    it('updateItem returns the fully re-fetched site, not null, after the 204 PATCH response', async () => {
      const fetchMock = vi.fn().mockImplementation(async (input: string | URL, init?: RequestInit) => {
        if (init?.method === 'PATCH') {
          return new Response(null, { status: 204, headers: { 'Content-Length': '0' } })
        }
        return jsonResponse({
          data: { id: 'monitoringSite-1', workspaceId: 'ws-1', name: 'Updated Site', code: 'SF-1' },
          included: {},
        })
      })
      vi.stubGlobal('fetch', fetchMock)

      const result = await client.monitoringSites.updateItem({
        id: 'monitoringSite-1',
        name: 'Updated Site',
      } as any)

      expect(fetchMock).toHaveBeenCalledTimes(2)
      expect(result).not.toBeNull()
      expect(result?.name).toBe('Updated Site')
    })

    it('updatePrivacy patches, then re-fetches the site for its current state', async () => {
      const fetchMock = vi.fn().mockImplementation(async (input: string | URL, init?: RequestInit) => {
        if (init?.method === 'PATCH') {
          return new Response(null, { status: 204, headers: { 'Content-Length': '0' } })
        }
        return jsonResponse({
          data: { id: 'monitoringSite-1', workspaceId: 'ws-1', name: 'Site 1', code: 'SF-1', isPrivate: true },
          included: {},
        })
      })
      vi.stubGlobal('fetch', fetchMock)

      const res = await client.monitoringSites.updatePrivacy('monitoringSite-1', true)

      expect(fetchMock).toHaveBeenCalledTimes(2)
      expect(res.ok).toBe(true)
      if (!res.ok) return
      expect(res.data.isPrivate).toBe(true)
    })

    it('setTag patches, then re-fetches the site for its current tags', async () => {
      const fetchMock = vi.fn().mockImplementation(async (input: string | URL, init?: RequestInit) => {
        if (init?.method === 'PATCH') {
          return new Response(null, { status: 204, headers: { 'Content-Length': '0' } })
        }
        return jsonResponse({
          data: {
            id: 'monitoringSite-1',
            workspaceId: 'ws-1',
            name: 'Site 1',
            code: 'SF-1',
            tags: { region: 'north' },
          },
          included: {},
        })
      })
      vi.stubGlobal('fetch', fetchMock)

      const res = await client.monitoringSites.setTag('monitoringSite-1', 'region', 'north')

      expect(fetchMock).toHaveBeenCalledTimes(2)
      expect(res.ok).toBe(true)
      if (!res.ok) return
      expect(res.data.tags).toEqual({ region: 'north' })
    })
  })

  describe('linked resources', () => {
    it('createLinkedResource posts, then re-fetches the list to find the new entry by id', async () => {
      const fetchMock = vi.fn().mockImplementation(async (input: string | URL, init?: RequestInit) => {
        if (init?.method === 'POST') {
          return jsonResponse({ id: 'linked-1' })
        }
        return jsonResponse([
          { id: 'linked-1', name: 'Site Report', type: 'Report', link: 'https://example.com/report.pdf' },
        ])
      })
      vi.stubGlobal('fetch', fetchMock)

      const res = await client.monitoringSites.createLinkedResource(
        'monitoringSite-1',
        new FormData()
      )

      expect(fetchMock).toHaveBeenCalledTimes(2)
      expect(res.ok).toBe(true)
      if (!res.ok) return
      expect(res.data).toMatchObject({ id: 'linked-1', name: 'Site Report' })
    })

    it('updateLinkedResource patches, then re-fetches the list to find the updated entry by id', async () => {
      const fetchMock = vi.fn().mockImplementation(async (input: string | URL, init?: RequestInit) => {
        if (init?.method === 'PATCH') {
          return new Response(null, { status: 204, headers: { 'Content-Length': '0' } })
        }
        return jsonResponse([
          { id: 'linked-1', name: 'Updated Report', type: 'Report', link: 'https://example.com/report.pdf' },
        ])
      })
      vi.stubGlobal('fetch', fetchMock)

      const res = await client.monitoringSites.updateLinkedResource(
        'monitoringSite-1',
        'linked-1',
        new FormData()
      )

      expect(fetchMock).toHaveBeenCalledTimes(2)
      expect(res.ok).toBe(true)
      if (!res.ok) return
      expect(res.data).toMatchObject({ id: 'linked-1', name: 'Updated Report' })
    })

    it('createLinkedResource returns ok:false when the new entry is missing from the refetched list', async () => {
      const fetchMock = vi.fn().mockImplementation(async (input: string | URL, init?: RequestInit) => {
        if (init?.method === 'POST') return jsonResponse({ id: 'linked-1' })
        return jsonResponse([])
      })
      vi.stubGlobal('fetch', fetchMock)

      const res = await client.monitoringSites.createLinkedResource(
        'monitoringSite-1',
        new FormData()
      )

      expect(res.ok).toBe(false)
    })
  })

  describe('listSiteSummaries', () => {
    it('fetches visible site summaries without requiring a workspace filter', async () => {
      vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse([])))

      const res = await client.monitoringSites.listSiteSummaries()

      expect(res.ok).toBe(true)
      const [url] = (fetch as any).mock.calls[0]
      expect(url).toMatch(/\/api\/data\/monitoring-sites\/site-summaries$/)
    })

    it('passes workspace_id as a query param and returns summaries', async () => {
      const payload = [
        {
          id: 'monitoringSite-1',
          workspaceId: 'workspace-1',
          name: 'Site 1',
          type: 'Stream',
          isPrivate: false,
          latitude: 41.7,
          longitude: -111.8,
          code: 'SF-1',
          tags: { network: 'main' },
        },
      ]

      vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(payload)))

      const res = await client.monitoringSites.listSiteSummaries('workspace id')

      expect(res.ok).toBe(true)
      expect(res.data).toEqual(payload)

      const [url] = (fetch as any).mock.calls[0]
      const parsed = new URL(url)
      expect(parsed.pathname).toBe('/api/data/monitoring-sites/site-summaries')
      expect(parsed.searchParams.get('workspace_id')).toBe('workspace id')
    })

    it('returns ok:false on a failed request', async () => {
      vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse({ detail: 'forbidden' }, 403)))

      const res = await client.monitoringSites.listSiteSummaries('ws-1')

      expect(res.ok).toBe(false)
      expect(res.status).toBe(403)
    })
  })
})

describe('DatastreamService', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  const client = new HydroServer({ host: 'https://hydro.example.com' })

  describe('linked resources', () => {
    it('createLinkedResource posts, then re-fetches the list to find the new entry by id', async () => {
      const fetchMock = vi.fn().mockImplementation(async (input: string | URL, init?: RequestInit) => {
        if (init?.method === 'POST') {
          return jsonResponse({ id: 'linked-1' })
        }
        return jsonResponse([
          { id: 'linked-1', name: 'Datastream Report', type: 'Report', link: 'https://example.com/report.pdf' },
        ])
      })
      vi.stubGlobal('fetch', fetchMock)

      const res = await client.datastreams.createLinkedResource('ds-1', new FormData())

      expect(fetchMock).toHaveBeenCalledTimes(2)
      expect(res.ok).toBe(true)
      if (!res.ok) return
      expect(res.data).toMatchObject({ id: 'linked-1', name: 'Datastream Report' })
    })

    it('updateLinkedResource patches, then re-fetches the list to find the updated entry by id', async () => {
      const fetchMock = vi.fn().mockImplementation(async (input: string | URL, init?: RequestInit) => {
        if (init?.method === 'PATCH') {
          return new Response(null, { status: 204, headers: { 'Content-Length': '0' } })
        }
        return jsonResponse([
          { id: 'linked-1', name: 'Updated Report', type: 'Report', link: 'https://example.com/report.pdf' },
        ])
      })
      vi.stubGlobal('fetch', fetchMock)

      const res = await client.datastreams.updateLinkedResource(
        'ds-1',
        'linked-1',
        new FormData()
      )

      expect(fetchMock).toHaveBeenCalledTimes(2)
      expect(res.ok).toBe(true)
      if (!res.ok) return
      expect(res.data).toMatchObject({ id: 'linked-1', name: 'Updated Report' })
    })
  })

  describe('getVisualizationBootstrap', () => {
    it('maps bootstrap payloads into model instances and resolves workspaceId', async () => {
      vi.stubGlobal(
        'fetch',
        vi.fn().mockResolvedValue(
          jsonResponse({
            monitoringSites: [{ id: 'monitoringSite-1', workspaceId: 'ws-1', name: 'Site 1', code: 'SF-1' }],
            datastreams: [
              { id: 'ds-1', name: 'DS 1', monitoringSiteId: 'monitoringSite-1', methodId: 'method-1', methodName: 'Shielded sensor', observedPropertyId: 'op-1', processingLevelId: 'pl-1', unitId: 'u-1', unitName: 'Degrees Celsius', unitSymbol: 'degC', noDataValue: -9999 },
              { id: 'ds-2', name: 'DS 2', monitoringSiteId: 'missing-monitoringSite', methodId: 'method-1', methodName: 'Shielded sensor', observedPropertyId: 'op-1', processingLevelId: 'pl-1', unitId: 'u-1', unitName: 'Degrees Celsius', unitSymbol: 'degC', noDataValue: -9999 },
            ],
            observedProperties: [{ id: 'op-1', name: 'Temperature', code: 'temp' }],
            processingLevels: [{ id: 'pl-1', name: 'Raw data' }],
          })
        )
      )

      const res = await client.datastreams.getVisualizationBootstrap()

      expect(res.ok).toBe(true)

      const [url] = (fetch as any).mock.calls[0]
      expect(url).toMatch(/\/api\/data\/datastreams\/visualization-bootstrap$/)

      expect(res.data.monitoringSites[0]).toBeInstanceOf(MonitoringSite)
      expect(res.data.datastreams[0]).toBeInstanceOf(Datastream)
      expect(res.data.observedProperties[0]).toBeInstanceOf(ObservedProperty)
      expect(res.data.processingLevels[0]).toBeInstanceOf(ProcessingLevel)

      expect(res.data.datastreams[0].workspaceId).toBe('ws-1')
      expect(res.data.datastreams[0].methodName).toBe('Shielded sensor')
      expect(res.data.datastreams[0].unitName).toBe('Degrees Celsius')
      expect(res.data.datastreams[1].workspaceId).toBe('')
    })

    it('returns ok:false on a failed request', async () => {
      vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse({ detail: 'error' }, 500)))

      const res = await client.datastreams.getVisualizationBootstrap()

      expect(res.ok).toBe(false)
      expect(res.status).toBe(500)
    })
  })

  describe('get/list with expand_related', () => {
    const rawDatastream = {
      id: 'ds-1',
      workspaceId: 'ws-1',
      monitoringSiteId: 'monitoringSite-1',
      methodId: 'method-1',
      observedPropertyId: 'op-1',
      processingLevelId: 'pl-1',
      unitId: 'unit-1',
      name: 'DS 1',
    }
    const included = {
      workspaces: [{ id: 'ws-1', name: 'Acme' }],
      monitoringSites: [{ id: 'monitoringSite-1', name: 'Site 1' }],
      methods: [{ id: 'method-1', name: 'Method 1' }],
      observedProperties: [{ id: 'op-1', name: 'Temperature' }],
      processingLevels: [{ id: 'pl-1', name: 'Raw data' }],
      units: [{ id: 'unit-1', name: 'Celsius' }],
    }

    it('get() with expand_related translates to include= and merges the sideloaded relations', async () => {
      const fetchMock = vi
        .fn()
        .mockResolvedValue(jsonResponse({ data: rawDatastream, included }))
      vi.stubGlobal('fetch', fetchMock)

      const res = await client.datastreams.get('ds-1', { expand_related: true })

      expect(String(fetchMock.mock.calls[0][0])).toContain(
        'include=workspace%2CmonitoringSite%2Cmethod%2CobservedProperty%2CprocessingLevel%2Cunit'
      )
      expect(res.ok).toBe(true)
      if (!res.ok) return
      expect((res.data as any).workspace).toMatchObject({ id: 'ws-1', name: 'Acme' })
      expect((res.data as any).monitoringSite).toMatchObject({
        id: 'monitoringSite-1',
        name: 'Site 1',
      })
      expect((res.data as any).method).toMatchObject({ id: 'method-1', name: 'Method 1' })
      expect((res.data as any).unit).toMatchObject({ id: 'unit-1', name: 'Celsius' })
    })

    it('get() without expand_related does not request include= or merge anything', async () => {
      const fetchMock = vi
        .fn()
        .mockResolvedValue(jsonResponse({ data: rawDatastream }))
      vi.stubGlobal('fetch', fetchMock)

      const res = await client.datastreams.get('ds-1')

      expect(String(fetchMock.mock.calls[0][0])).not.toContain('include=')
      expect(res.ok).toBe(true)
      if (!res.ok) return
      expect((res.data as any).workspace).toBeUndefined()
    })

    it('list() with expand_related merges included relations onto every row', async () => {
      const fetchMock = vi.fn().mockResolvedValue(
        jsonResponse({
          data: [rawDatastream],
          meta: { offset: 0, limit: 100, totalCount: 1 },
          included,
        })
      )
      vi.stubGlobal('fetch', fetchMock)

      const res = await client.datastreams.list({ expand_related: true } as any)

      expect(String(fetchMock.mock.calls[0][0])).toContain(
        'include=workspace%2CmonitoringSite%2Cmethod%2CobservedProperty%2CprocessingLevel%2Cunit'
      )
      expect(res.ok).toBe(true)
      if (!res.ok) return
      expect((res.data[0] as any).processingLevel).toMatchObject({
        id: 'pl-1',
        name: 'Raw data',
      })
      expect((res.data[0] as any).observedProperty).toMatchObject({
        id: 'op-1',
        name: 'Temperature',
      })
    })
  })
})
