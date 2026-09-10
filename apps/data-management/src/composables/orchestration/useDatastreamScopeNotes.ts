import { computed, type Ref } from 'vue'
import type { Datastream } from '@hydroserver/client'
import { storeToRefs } from 'pinia'
import { datastreamMonitoringSiteId } from '@/utils/orchestration/datastreams'
import { useOrchestrationStore } from '@/store/orchestration'

/**
 * The datastream card selectors carry no caption — the button already says
 * what it picks — so a short note above them is what explains why the list is
 * scoped the way it is. Every task form draws that note from here so the
 * wording stays identical across forms.
 */
export const INPUT_SCOPE_NOTE =
  'Inputs may come from any monitoring site in this workspace.'

export function useDatastreamScopeNotes(
  datastreams: Ref<Datastream[]>,
  monitoringSiteId: Ref<string | null>
) {
  const { workspaceMonitoringSites } = storeToRefs(useOrchestrationStore())

  const monitoringSiteName = computed(() => {
    const siteId = monitoringSiteId.value
    if (!siteId) return null

    const fromStore = workspaceMonitoringSites.value.find(
      (monitoringSite) => monitoringSite.id === siteId
    )?.name
    if (fromStore) return fromStore

    // A site with no datastreams yet isn't always in the store, so fall back
    // to whatever the loaded datastreams know about it.
    const siteDatastream = datastreams.value.find(
      (datastream) => datastreamMonitoringSiteId(datastream) === siteId
    ) as (Datastream & Record<string, any>) | undefined
    return siteDatastream?.monitoringSite?.name ?? null
  })

  const monitoringSiteLabel = computed(() =>
    monitoringSiteName.value
      ? `the ${monitoringSiteName.value} site`
      : 'the selected site'
  )

  const outputScopeNote = computed(
    () => `Outputs must belong to ${monitoringSiteLabel.value}.`
  )

  const siteScopeNote = computed(
    () => `Only datastreams at ${monitoringSiteLabel.value} can be selected.`
  )

  return {
    monitoringSiteName,
    monitoringSiteLabel,
    inputScopeNote: INPUT_SCOPE_NOTE,
    outputScopeNote,
    siteScopeNote,
  }
}
