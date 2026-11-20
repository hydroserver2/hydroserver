import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import TileLayer from 'ol/layer/Tile'
import LayerGroup from 'ol/layer/Group'
import VectorTileLayer from 'ol/layer/VectorTile'
import type VectorTileSource from 'ol/source/VectorTile'
import { applyStyle } from 'ol-mapbox-style'
import { createOverlayLayers } from '@/utils/maps/overlays'
import type { MapLayer } from '@/models/settings'

vi.mock('ol-mapbox-style', () => ({
  applyStyle: vi.fn().mockResolvedValue(undefined),
}))

const service =
  'https://tiles.arcgis.com/tiles/ZzrwjTRez6FJiOq4/arcgis/rest/services/NetFlowlinesVTPK/VectorTileServer'
const config: MapLayer = {
  name: 'Flowlines',
  source: `${service}?f=json`,
  attribution: 'Flowline provider',
}
const metadata = {
  tiles: ['tile/{z}/{y}/{x}.pbf'],
  defaultStyles: 'resources/styles',
  tileInfo: {
    rows: 512,
    cols: 512,
    origin: { x: -20037508.342787, y: 20037508.342787 },
    spatialReference: { wkid: 102100, latestWkid: 3857 },
    lods: [
      { level: 0, resolution: 78271.516964 },
      { level: 1, resolution: 39135.758482 },
    ],
  },
}

describe('map overlays', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ ok: true, json: async () => metadata })
    )
  })
  afterEach(() => vi.unstubAllGlobals())

  it('sorts by priority with deterministic ties and preserves default visibility', () => {
    const overlays = createOverlayLayers([
      { ...config, name: 'High', priority: 100000, visibleByDefault: true },
      { ...config, name: 'B', priority: -10 },
      { ...config, name: 'A', priority: -10 },
    ])
    expect(overlays.map(({ configuration }) => configuration.name)).toEqual([
      'A',
      'B',
      'High',
    ])
    const group = new LayerGroup({
      layers: overlays.map(({ layer }) => layer),
      zIndex: 1,
    })
    const mapLayers = new LayerGroup({
      layers: [
        new TileLayer({ zIndex: 0 }),
        group,
        new TileLayer({ zIndex: 2 }),
      ],
    })
    expect(mapLayers.getLayerStatesArray().map(({ zIndex }) => zIndex)).toEqual(
      [0, 1, 1, 1, 2]
    )
    expect(overlays.map(({ layer }) => layer.getVisible())).toEqual([
      false,
      false,
      true,
    ])
    expect(overlays.every(({ layer }) => !layer.getSource())).toBe(true)
    expect(fetch).not.toHaveBeenCalled()
    expect(applyStyle).not.toHaveBeenCalled()
  })

  it('loads XYZ tiles and attribution only when enabled', async () => {
    const overlay = createOverlayLayers([
      { ...config, source: 'https://example.com/{z}/{x}/{y}.png' },
    ])[0]
    expect(overlay.layer).toBeInstanceOf(TileLayer)
    expect(overlay.layer.getSource()).toBeNull()
    overlay.layer.setVisible(true)
    await overlay.load()
    const source = overlay.layer.getSource()!
    expect(source.getAttributions()?.({} as never)).toEqual([
      'Flowline provider',
    ])
    await overlay.load()
    expect(overlay.layer.getSource()).toBe(source)
    expect(fetch).not.toHaveBeenCalled()
  })

  it.each(['', '/', '?f=json', '/?f=json', '/resources/styles/root.json'])(
    'loads ArcGIS URL form %s with its native tile grid and published style',
    async (suffix) => {
      const overlay = createOverlayLayers([
        { ...config, source: `${service}${suffix}` },
      ])[0]
      expect(overlay.layer).toBeInstanceOf(VectorTileLayer)
      await Promise.all([overlay.load(), overlay.load()])
      expect(fetch).toHaveBeenCalledTimes(1)
      expect(String(vi.mocked(fetch).mock.calls[0][0])).toBe(
        `${service}/?f=json`
      )
      const source = overlay.layer.getSource() as VectorTileSource
      expect(source.getTileGrid()!.getTileSize(0)).toEqual([512, 512])
      expect(source.getTileGrid()!.getResolutions()).toEqual([
        78271.516964, 39135.758482,
      ])
      expect(source.getTileGrid()!.getOrigin(0)).toEqual([
        -20037508.342787, 20037508.342787,
      ])
      expect(
        source.getTileUrlFunction()([1, 2, 3], 1, source.getProjection()!)
      ).toBe(`${service}/tile/1/3/2.pbf`)
      expect(source.getAttributions()?.({} as never)).toEqual([
        'Flowline provider',
      ])
      expect(applyStyle).toHaveBeenCalledWith(
        overlay.layer,
        `${service}/resources/styles/root.json`,
        { updateSource: false }
      )
    }
  )

  it('preserves service query parameters on metadata, style, and tile URLs', async () => {
    const overlay = createOverlayLayers([
      { ...config, source: `${service}?f=json&token=test-token` },
    ])[0]
    await overlay.load()
    expect(String(vi.mocked(fetch).mock.calls[0][0])).toContain(
      'token=test-token'
    )
    expect(vi.mocked(applyStyle).mock.calls[0][1]).toBe(
      `${service}/resources/styles/root.json?token=test-token`
    )
    const source = overlay.layer.getSource() as VectorTileSource
    expect(source.getUrls()).toEqual([
      `${service}/tile/{z}/{y}/{x}.pbf?token=test-token`,
    ])
  })

  it('allows a failed layer to be retried without affecting other overlays', async () => {
    vi.mocked(fetch).mockResolvedValueOnce({ ok: false } as Response)
    const [overlay, other] = createOverlayLayers([
      config,
      { ...config, name: 'Other' },
    ])
    await expect(overlay.load()).rejects.toThrow('metadata')
    expect(other.layer.getSource()).toBeNull()
    await overlay.load()
    expect(overlay.layer.getSource()).toBeTruthy()
    expect(fetch).toHaveBeenCalledTimes(2)
  })
})
