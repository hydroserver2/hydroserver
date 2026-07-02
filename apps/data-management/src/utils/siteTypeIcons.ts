import type { SiteTypeIcon } from '@hydroserver/client'
import {
  mdiBeach,
  mdiCalculator,
  mdiFountain,
  mdiGate,
  mdiGauge,
  mdiGrass,
  mdiHomeOutline,
  mdiHydroPower,
  mdiImageFilterHdr,
  mdiMapMarker,
  mdiMapMarkerOutline,
  mdiPipeDisconnected,
  mdiRoadVariant,
  mdiSnowflake,
  mdiSprinkler,
  mdiTerrain,
  mdiTestTube,
  mdiVectorPolyline,
  mdiWater,
  mdiWaterCheck,
  mdiWaterPump,
  mdiWaterWell,
  mdiWaves,
  mdiWavesArrowRight,
  mdiWeatherCloudy,
} from '@mdi/js'

const iconPaths: Record<string, string> = {
  beach: mdiBeach,
  calculator: mdiCalculator,
  fountain: mdiFountain,
  gate: mdiGate,
  gauge: mdiGauge,
  grass: mdiGrass,
  'home-outline': mdiHomeOutline,
  'hydro-power': mdiHydroPower,
  'image-filter-hdr': mdiImageFilterHdr,
  'map-marker': mdiMapMarker,
  'pipe-disconnected': mdiPipeDisconnected,
  'road-variant': mdiRoadVariant,
  snowflake: mdiSnowflake,
  sprinkler: mdiSprinkler,
  terrain: mdiTerrain,
  'test-tube': mdiTestTube,
  'vector-polyline': mdiVectorPolyline,
  water: mdiWater,
  'water-check': mdiWaterCheck,
  'water-pump': mdiWaterPump,
  'water-well': mdiWaterWell,
  waves: mdiWaves,
  'waves-arrow-right': mdiWavesArrowRight,
  'weather-cloudy': mdiWeatherCloudy,
}

export interface SiteTypeIconRule {
  keyword: string
  icon: string
}

const normalizeSiteType = (siteType: string) =>
  siteType
    .toLowerCase()
    .replace(/[^\p{L}\p{N}]+/gu, ' ')
    .trim()
    .replace(/\s+/g, ' ')

export const buildSiteTypeIconRules = (
  mappings: SiteTypeIcon[]
): SiteTypeIconRule[] =>
  mappings
    .flatMap(({ icon, siteTypes }) => {
      const iconPath = iconPaths[icon]
      if (!iconPath) return []

      return siteTypes
        .map(normalizeSiteType)
        .filter(Boolean)
        .map((keyword) => ({ keyword, icon: iconPath }))
    })
    .sort((a, b) => b.keyword.length - a.keyword.length)

export const getSiteTypeIcon = (
  siteType: string,
  rules: SiteTypeIconRule[]
): string => {
  const normalized = ` ${normalizeSiteType(siteType)} `
  return (
    rules.find(({ keyword }) => normalized.includes(` ${keyword} `))?.icon ??
    mdiMapMarkerOutline
  )
}
