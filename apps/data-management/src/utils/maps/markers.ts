import { MonitoringSite } from '@hydroserver/client'
import { MapMonitoringSite, MonitoringSiteMarker, MonitoringSiteMapSummary } from '@/types'
import { mapMarkerColors } from '@/utils/materialColors'

type ColorableMonitoringSite = MonitoringSite | MonitoringSiteMapSummary

type ColorizedMonitoringSite<T extends MapMonitoringSite> = T & {
  color?: {
    borderColor: string
    background: string
    glyphColor: string
  }
  tagValue?: string
}

export function hasMonitoringSiteTags(
  monitoringSite: MapMonitoringSite
): monitoringSite is ColorableMonitoringSite {
  return 'tags' in monitoringSite && Array.isArray(monitoringSite.tags)
}

const addColorToMarkersByValue = <T extends MapMonitoringSite>(
  monitoringSites: T[],
  getValue: (monitoringSite: T) => string | undefined
): Array<ColorizedMonitoringSite<T>> => {
  let colorIndex = 0
  const colorMap = new Map<string, (typeof mapMarkerColors)[number]>()

  return monitoringSites.map((monitoringSite) => {
    const value = getValue(monitoringSite)
    if (!value) return monitoringSite

    if (!colorMap.has(value)) {
      colorMap.set(value, mapMarkerColors[colorIndex % mapMarkerColors.length])
      colorIndex++
    }
    return { ...monitoringSite, color: colorMap.get(value), tagValue: value }
  })
}

export const addColorToMarkers = <T extends ColorableMonitoringSite>(
  monitoringSites: T[],
  key: string
): Array<ColorizedMonitoringSite<T>> =>
  addColorToMarkersByValue(
    monitoringSites,
    (monitoringSite) => monitoringSite.tags.find((tag) => tag.key === key)?.value
  )

export const addWorkspaceColorToMarkers = <T extends MapMonitoringSite>(
  monitoringSites: T[]
): Array<ColorizedMonitoringSite<T>> =>
  addColorToMarkersByValue(monitoringSites, (monitoringSite) => monitoringSite.workspaceId)

export const addSiteTypeColorToMarkers = <T extends MapMonitoringSite>(
  monitoringSites: T[]
): Array<ColorizedMonitoringSite<T>> =>
  addColorToMarkersByValue(monitoringSites, (monitoringSite) => monitoringSite.type)

export function isMonitoringSiteMarker(
  markerData: MapMonitoringSite
): markerData is MonitoringSiteMarker {
  return !('description' in markerData)
}

export function generateMarkerContent(markerData: MapMonitoringSite): string {
  const isMarker = isMonitoringSiteMarker(markerData)
  const subtitle = isMarker
    ? markerData.type || ''
    : [
        markerData.adminArea2 || '',
        markerData.adminArea2 && markerData.adminArea1
          ? ','
          : '',
        markerData.adminArea1 || '',
      ]
        .join(' ')
        .trim()
  const description = isMarker ? '' : markerData.description ?? ''

  return `
      <div class="m-0 max-w-prose">
        <h6 class="hs-text-md font-weight-semibold text-slate-900">${markerData.name}</h6>
        ${subtitle ? `<p class="mb-2 hs-text-sm text-slate-500">${subtitle}</p>` : ''}
        ${description ? `<p class="mb-3 hs-text-sm text-slate-700">${description}</p>` : ''}
        <p class="mt-6">
          <a
            class="font-weight-medium text-[rgb(var(--v-theme-primary))] underline decoration-current underline-offset-2 hover:decoration-2 focus:outline-none focus-visible:rounded-sm focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[rgb(var(--v-theme-primary))]"
            href="/sites/${markerData.id}"
          >
            View data for this site
          </a>
        </p>
      </div>`
}
