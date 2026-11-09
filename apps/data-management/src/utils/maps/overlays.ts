import TileLayer from 'ol/layer/Tile'
import VectorTileLayer from 'ol/layer/VectorTile'
import VectorTileSource from 'ol/source/VectorTile'
import XYZ from 'ol/source/XYZ'
import MVT from 'ol/format/MVT'
import TileGrid from 'ol/tilegrid/TileGrid'
import type { MapLayer } from '@/models/settings'

interface ArcGISMetadata {
  tiles: string[]
  defaultStyles?: string
  tileInfo: {
    rows: number
    cols: number
    origin: { x: number; y: number }
    spatialReference: { wkid: number; latestWkid?: number }
    lods: { level: number; resolution: number }[]
  }
}

// Match service roots and the published style, including ?f=json service links.
function getArcGISServiceUrl(source: string): URL | undefined {
  const url = new URL(source, window.location.href)
  const match = url.pathname.match(
    /^(.*\/VectorTileServer)(?:\/resources\/styles\/root\.json)?\/?$/i
  )
  if (!match) return
  url.pathname = `${match[1]}/`
  url.searchParams.delete('f')
  url.hash = ''
  return url
}

function serviceResource(serviceUrl: URL, path: string): string {
  const url = new URL(path, serviceUrl)
  // Preserve service query parameters such as an access token.
  serviceUrl.searchParams.forEach((value, key) =>
    url.searchParams.set(key, value)
  )
  // URL encodes template braces, which OpenLayers needs in their original form.
  return url.href.replaceAll('%7B', '{').replaceAll('%7D', '}')
}

export function createOverlayLayers(configurations: MapLayer[]) {
  // Inherit the overlay group's z-index; sorted collection order breaks ties.
  // Names break priority ties consistently across database query orders.
  return [...configurations]
    .sort(
      (a, b) =>
        (a.priority ?? 0) - (b.priority ?? 0) || a.name.localeCompare(b.name)
    )
    .map((configuration) => {
      const serviceUrl = getArcGISServiceUrl(configuration.source)
      const options = {
        visible: configuration.visibleByDefault ?? false,
      }
      const layer = serviceUrl
        ? new VectorTileLayer({ ...options, declutter: true, style: null })
        : new TileLayer(options)
      let loaded: Promise<void> | undefined

      const load = (): Promise<void> => {
        if (loaded) return loaded
        loaded = (async () => {
          if (layer instanceof TileLayer) {
            layer.setSource(
              new XYZ({
                url: configuration.source,
                attributions: configuration.attribution,
              })
            )
            return
          }

          const metadataUrl = new URL(serviceUrl!)
          metadataUrl.searchParams.set('f', 'json')
          const response = await fetch(metadataUrl)
          if (!response.ok)
            throw new Error('Could not load ArcGIS tile metadata')
          const metadata: ArcGISMetadata = await response.json()
          const tileInfo = metadata.tileInfo
          const wkid =
            tileInfo?.spatialReference.latestWkid ??
            tileInfo?.spatialReference.wkid
          if (
            ![3857, 102100, 102113].includes(wkid!) ||
            !metadata.tiles?.length
          ) {
            throw new Error(
              'ArcGIS overlays must provide Web Mercator vector tiles'
            )
          }
          const source = new VectorTileSource({
            format: new MVT(),
            urls: metadata.tiles.map((path) =>
              serviceResource(serviceUrl!, path)
            ),
            attributions: configuration.attribution,
            tileGrid: new TileGrid({
              origin: [tileInfo.origin.x, tileInfo.origin.y],
              resolutions: Array.from(
                { length: tileInfo.lods.at(-1)!.level + 1 },
                (_, zoom) =>
                  tileInfo.lods.find((lod) => lod.level === zoom)?.resolution ??
                  tileInfo.lods[0].resolution *
                    2 ** (tileInfo.lods[0].level - zoom)
              ),
              tileSize: [tileInfo.cols, tileInfo.rows],
              minZoom: tileInfo.lods[0].level,
            }),
          })
          layer.setSource(source)
          const { applyStyle } = await import('ol-mapbox-style')
          await applyStyle(
            layer,
            serviceResource(
              serviceUrl!,
              `${metadata.defaultStyles || 'resources/styles'}/root.json`
            ),
            { updateSource: false }
          )
        })().catch((error) => {
          loaded = undefined // A failed service may be retried by toggling it on again.
          throw error
        })
        return loaded
      }

      return { configuration, layer, load }
    })
}
