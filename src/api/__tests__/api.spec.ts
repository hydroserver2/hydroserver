import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const { fetchMock } = vi.hoisted(() => ({
  fetchMock: vi.fn(),
}))

vi.mock('@hydroserver/client', () => {
  class Thing {
    id = ''
    workspaceId = ''
    name = ''
    samplingFeatureCode = ''
  }

  class Datastream {
    id = ''
    name = ''
    thingId = ''
    observedPropertyId = ''
    processingLevelId = ''
    unitId = ''
    noDataValue = NaN
    workspaceId = ''
  }

  class ObservedProperty {
    id = ''
    name = ''
    code = ''
  }

  class ProcessingLevel {
    id = ''
    definition?: string | null
  }

  return {
    Thing,
    Datastream,
    ObservedProperty,
    ProcessingLevel,
  }
})

import { listThingMarkers } from '@/api/thingMarkers'
import { listThingSiteSummaries } from '@/api/thingSiteSummaries'
import { getVisualizationBootstrap } from '@/api/visualizationBootstrap'
import {
  Datastream,
  ObservedProperty,
  ProcessingLevel,
  Thing,
} from '@hydroserver/client'

describe('api modules', () => {
  beforeEach(() => {
    fetchMock.mockReset()
    vi.stubGlobal('fetch', fetchMock)
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  describe('listThingMarkers', () => {
    it('requests thing markers and returns the parsed payload', async () => {
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

      fetchMock.mockResolvedValue({
        ok: true,
        json: vi.fn().mockResolvedValue(payload),
      })

      await expect(listThingMarkers()).resolves.toEqual(payload)

      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringMatching(/\/api\/data\/things\/markers$/),
        {
          credentials: 'include',
          headers: {
            Accept: 'application/json',
          },
        }
      )
    })

    it('throws when the markers request fails', async () => {
      fetchMock.mockResolvedValue({
        ok: false,
        status: 503,
      })

      await expect(listThingMarkers()).rejects.toThrow(
        'Failed to load thing markers: 503'
      )
    })
  })

  describe('listThingSiteSummaries', () => {
    it('requests site summaries for the provided workspace id', async () => {
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

      fetchMock.mockResolvedValue({
        ok: true,
        json: vi.fn().mockResolvedValue(payload),
      })

      await expect(listThingSiteSummaries('workspace id')).resolves.toEqual(
        payload
      )

      expect(fetchMock).toHaveBeenCalledTimes(1)
      const [requestUrl, requestOptions] = fetchMock.mock.calls[0]
      const url = new URL(String(requestUrl), 'http://localhost')

      expect(url.pathname).toBe('/api/data/things/site-summaries')
      expect(url.searchParams.get('workspace_id')).toBe('workspace id')
      expect(requestOptions).toEqual({
        credentials: 'include',
        headers: {
          Accept: 'application/json',
        },
      })
    })

    it('throws when the site summaries request fails', async () => {
      fetchMock.mockResolvedValue({
        ok: false,
        status: 401,
      })

      await expect(listThingSiteSummaries('workspace-1')).rejects.toThrow(
        'Failed to load thing site summaries: 401'
      )
    })
  })

  describe('getVisualizationBootstrap', () => {
    it('maps bootstrap payloads into client model instances', async () => {
      fetchMock.mockResolvedValue({
        ok: true,
        json: vi.fn().mockResolvedValue({
          things: [
            {
              id: 'thing-1',
              workspaceId: 'workspace-1',
              name: 'Site 1',
              samplingFeatureCode: 'SF-1',
            },
          ],
          datastreams: [
            {
              id: 'ds-1',
              name: 'Datastream 1',
              thingId: 'thing-1',
              observedPropertyId: 'op-1',
              processingLevelId: 'pl-1',
              unitId: 'unit-1',
              noDataValue: -9999,
              valueCount: 10,
            },
            {
              id: 'ds-2',
              name: 'Datastream 2',
              thingId: 'missing-thing',
              observedPropertyId: 'op-1',
              processingLevelId: 'pl-1',
              unitId: 'unit-1',
              noDataValue: -9999,
            },
          ],
          observedProperties: [
            {
              id: 'op-1',
              name: 'Temperature',
              code: 'temp',
            },
          ],
          processingLevels: [
            {
              id: 'pl-1',
              definition: 'Raw data',
            },
          ],
        }),
      })

      const result = await getVisualizationBootstrap()

      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringMatching(
          /\/api\/data\/datastreams\/visualization-bootstrap$/
        ),
        {
          credentials: 'include',
          headers: {
            Accept: 'application/json',
          },
        }
      )

      expect(result.things[0]).toBeInstanceOf(Thing)
      expect(result.datastreams[0]).toBeInstanceOf(Datastream)
      expect(result.observedProperties[0]).toBeInstanceOf(ObservedProperty)
      expect(result.processingLevels[0]).toBeInstanceOf(ProcessingLevel)
      expect(result.datastreams[0].workspaceId).toBe('workspace-1')
      expect(result.datastreams[1].workspaceId).toBe('')
    })

    it('throws when the bootstrap request fails', async () => {
      fetchMock.mockResolvedValue({
        ok: false,
        status: 500,
      })

      await expect(getVisualizationBootstrap()).rejects.toThrow(
        'Failed to load visualization bootstrap: 500'
      )
    })
  })
})
