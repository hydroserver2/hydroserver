import { Thing } from '@hydroserver/client'
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

export function generateMarkerContent(markerData: Thing): string {
  return `
      <div class="m-0 max-w-prose">
        <h6 class="text-lg font-semibold text-slate-900">${markerData.name}</h6>
        <p class="mb-2 text-sm text-slate-500">
        ${markerData.location.adminArea2 ? markerData.location.adminArea2 : ''}
        ${markerData.location.adminArea2 && markerData.location.adminArea1 ? ',' : ''}
        ${markerData.location.adminArea1 ? markerData.location.adminArea1 : ''}
        </p>
        <p class="mb-3 text-sm text-slate-700">${markerData.description ?? ''}</p>
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
