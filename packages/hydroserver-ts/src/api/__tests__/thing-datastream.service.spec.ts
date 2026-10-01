import { afterEach, describe, expect, it, vi } from 'vitest'
import { HydroServer } from '../HydroServer'
import { Thing, Datastream, ObservedProperty, ProcessingLevel } from '../../types'

const jsonResponse = (data: unknown, status = 200) =>
  new Response(JSON.stringify(data), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })

describe('ThingService', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  const client = new HydroServer({ host: 'https://hydro.example.com' })

  describe('listMarkers', () => {
    it('fetches thing markers and returns them in data', async () => {
      const payload = [
        {
          id: 'thing-1',
          workspaceId: 'workspace-1',
          name: 'Site 1',
          siteType: 'Stream',
          isPrivate: false,
          latitude: 41.7,
          longitude: -111.8,
        },
      ]

      vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(payload)))

      const res = await client.things.listMarkers()

      expect(res.ok).toBe(true)
      expect(res.data).toEqual(payload)
      const [url] = (fetch as any).mock.calls[0]
      expect(url).toMatch(/\/api\/data\/things\/markers$/)
    })

    it('returns ok:false on a failed request', async () => {
      vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse({ detail: 'error' }, 503)))

      const res = await client.things.listMarkers()

      expect(res.ok).toBe(false)
      expect(res.status).toBe(503)
    })
  })

  describe('listSiteSummaries', () => {
    it('passes workspace_id as a query param and returns summaries', async () => {
      const payload = [
        {
          id: 'thing-1',
          workspaceId: 'workspace-1',
          name: 'Site 1',
          siteType: 'Stream',
          isPrivate: false,
          latitude: 41.7,
          longitude: -111.8,
          samplingFeatureCode: 'SF-1',
          tags: [{ key: 'network', value: 'main' }],
        },
      ]

      vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(payload)))

      const res = await client.things.listSiteSummaries('workspace id')

      expect(res.ok).toBe(true)
      expect(res.data).toEqual(payload)

      const [url] = (fetch as any).mock.calls[0]
      const parsed = new URL(url)
      expect(parsed.pathname).toBe('/api/data/things/site-summaries')
      expect(parsed.searchParams.get('workspace_id')).toBe('workspace id')
    })

    it('returns ok:false on a failed request', async () => {
      vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse({ detail: 'forbidden' }, 403)))

      const res = await client.things.listSiteSummaries('ws-1')

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

  describe('create', () => {
    it('forwards expand_related so the 201 body carries nested relations', async () => {
      vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse({ id: 'ds-1' }, 201)))

      await client.datastreams.create({ name: 'DS 1' } as any, {
        expand_related: true,
      })

      const [url] = (fetch as any).mock.calls[0]
      const parsed = new URL(url)
      expect(parsed.pathname).toBe('/api/data/datastreams')
      expect(parsed.searchParams.get('expand_related')).toBe('true')
    })

    it('omits the query string when no params are given', async () => {
      vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse({ id: 'ds-1' }, 201)))

      await client.datastreams.create({ name: 'DS 1' } as any)

      const [url] = (fetch as any).mock.calls[0]
      expect(url).toMatch(/\/api\/data\/datastreams$/)
    })
  })

  describe('createObservations', () => {
    it('sends the replace range as query params', async () => {
      vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(null, 201)))

      await client.datastreams.createObservations(
        'ds-1',
        { fields: ['phenomenonTime', 'result'], data: [] },
        {
          mode: 'replace',
          phenomenon_time_start: '2025-01-01T00:00:00Z',
          phenomenon_time_end: '2025-02-01T00:00:00Z',
        }
      )

      const [url] = (fetch as any).mock.calls[0]
      const parsed = new URL(url)
      expect(parsed.pathname).toMatch(/\/datastreams\/ds-1\/observations\/bulk-create$/)
      expect(parsed.searchParams.get('mode')).toBe('replace')
      expect(parsed.searchParams.get('phenomenon_time_start')).toBe('2025-01-01T00:00:00Z')
      expect(parsed.searchParams.get('phenomenon_time_end')).toBe('2025-02-01T00:00:00Z')
    })
  })

  describe('getObservationsChecksum', () => {
    const start = new Date('2025-01-01T00:00:00Z')
    const end = new Date('2025-02-01T00:00:00Z')

    it('reads the X-Checksum header for the window', async () => {
      vi.stubGlobal(
        'fetch',
        vi.fn().mockResolvedValue(
          new Response(JSON.stringify({ phenomenonTime: [], result: [] }), {
            status: 200,
            headers: { 'Content-Type': 'application/json', 'X-Checksum': 'abc123' },
          })
        )
      )

      const res = await client.datastreams.getObservationsChecksum('ds-1', start, end)

      expect(res).toMatchObject({ ok: true, data: 'abc123' })
      const [url] = (fetch as any).mock.calls[0]
      const parsed = new URL(url)
      expect(parsed.pathname).toMatch(/\/datastreams\/ds-1\/observations$/)
      expect(parsed.searchParams.get('phenomenon_time_min')).toBe(start.toISOString())
      expect(parsed.searchParams.get('phenomenon_time_max')).toBe(end.toISOString())
      expect(parsed.searchParams.get('page_size')).toBe('1')
    })

    it('fails when the response has no checksum', async () => {
      vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse({}, 200)))

      const res = await client.datastreams.getObservationsChecksum('ds-1', start, end)

      expect(res.ok).toBe(false)
    })

    it('returns ok:false on a failed request', async () => {
      vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse({ detail: 'nope' }, 404)))

      const res = await client.datastreams.getObservationsChecksum('ds-1', start, end)

      expect(res.ok).toBe(false)
    })
  })

  describe('getVisualizationBootstrap', () => {
    it('maps bootstrap payloads into model instances and resolves workspaceId', async () => {
      vi.stubGlobal(
        'fetch',
        vi.fn().mockResolvedValue(
          jsonResponse({
            things: [{ id: 'thing-1', workspaceId: 'ws-1', name: 'Site 1', samplingFeatureCode: 'SF-1' }],
            datastreams: [
              { id: 'ds-1', name: 'DS 1', thingId: 'thing-1', observedPropertyId: 'op-1', processingLevelId: 'pl-1', unitId: 'u-1', noDataValue: -9999 },
              { id: 'ds-2', name: 'DS 2', thingId: 'missing-thing', observedPropertyId: 'op-1', processingLevelId: 'pl-1', unitId: 'u-1', noDataValue: -9999 },
            ],
            observedProperties: [{ id: 'op-1', name: 'Temperature', code: 'temp' }],
            processingLevels: [{ id: 'pl-1', definition: 'Raw data' }],
          })
        )
      )

      const res = await client.datastreams.getVisualizationBootstrap()

      expect(res.ok).toBe(true)

      const [url] = (fetch as any).mock.calls[0]
      expect(url).toMatch(/\/api\/data\/datastreams\/visualization-bootstrap$/)

      expect(res.data.things[0]).toBeInstanceOf(Thing)
      expect(res.data.datastreams[0]).toBeInstanceOf(Datastream)
      expect(res.data.observedProperties[0]).toBeInstanceOf(ObservedProperty)
      expect(res.data.processingLevels[0]).toBeInstanceOf(ProcessingLevel)

      expect(res.data.datastreams[0].workspaceId).toBe('ws-1')
      expect(res.data.datastreams[1].workspaceId).toBe('')
    })

    it('returns ok:false on a failed request', async () => {
      vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse({ detail: 'error' }, 500)))

      const res = await client.datastreams.getVisualizationBootstrap()

      expect(res.ok).toBe(false)
      expect(res.status).toBe(500)
    })
  })
})
