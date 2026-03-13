import { Thing } from '@hydroserver/client'
import { MapThing, ThingMarker } from '@/types'
import { mapMarkerColors } from '@/utils/materialColors'

export const addColorToMarkers = (things: Thing[], key: string) => {
  let colorIndex = 0
  const colorMap = new Map()

  return things.map((thing) => {
    const tagValue = thing.tags.find((tag) => tag.key === key)?.value
    if (tagValue === undefined) return thing

    if (!colorMap.has(tagValue)) {
      colorMap.set(
        tagValue,
        mapMarkerColors[colorIndex % mapMarkerColors.length]
      )
      colorIndex++
    }
    return { ...thing, color: colorMap.get(tagValue), tagValue: tagValue }
  })
}

export function isThingMarker(markerData: MapThing): markerData is ThingMarker {
  return !('location' in markerData)
}

export function generateMarkerContent(markerData: MapThing): string {
  const isMarker = isThingMarker(markerData)
  const subtitle = isMarker
    ? markerData.siteType || ''
    : [
        markerData.location.adminArea2 || '',
        markerData.location.adminArea2 && markerData.location.adminArea1
          ? ','
          : '',
        markerData.location.adminArea1 || '',
      ]
        .join(' ')
        .trim()
  const description = isMarker ? '' : markerData.description ?? ''

  return `
      <div class="m-0 max-w-prose">
        <h6 class="text-lg font-semibold text-slate-900">${markerData.name}</h6>
        ${subtitle ? `<p class="mb-2 text-sm text-slate-500">${subtitle}</p>` : ''}
        ${description ? `<p class="mb-3 text-sm text-slate-700">${description}</p>` : ''}
        <p class="mt-6">
          <a
            class="font-medium text-[rgb(var(--v-theme-primary))] underline decoration-current underline-offset-2 hover:decoration-2 focus:outline-none focus-visible:rounded-sm focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[rgb(var(--v-theme-primary))]"
            href="/sites/${markerData.id}"
          >
            View data for this site
          </a>
        </p>
      </div>`
}
