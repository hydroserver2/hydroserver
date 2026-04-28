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
