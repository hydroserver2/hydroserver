import { Workspace } from '@hydroserver/client'
import type { ThingMarker } from '@/types'

export function filterThingMarkers(
  things: ThingMarker[],
  selectedWorkspaces: Workspace[],
  selectedSiteTypes: string[]
) {
  const selectedWorkspaceIds = new Set(
    selectedWorkspaces.map((workspace) => workspace.id)
  )

  return things.filter((thing) => {
    const inSelectedWorkspace =
      selectedWorkspaceIds.size === 0 ||
      selectedWorkspaceIds.has(thing.workspaceId)
    const inSelectedSiteType =
      selectedSiteTypes.length === 0 ||
      selectedSiteTypes.includes(thing.siteType)

    return inSelectedWorkspace && inSelectedSiteType
  })
}
