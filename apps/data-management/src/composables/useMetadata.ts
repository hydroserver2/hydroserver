import { computed, Ref, ref, watch } from 'vue'
import hs, {
  ProcessingLevel,
  Unit,
  ObservedProperty,
  Sensor,
  ResultQualifier,
  Workspace,
} from '@hydroserver/client'

import { storeToRefs } from 'pinia'
import { useWorkspaceStore } from '@/store/workspaces'

export function useMetadata(localWorkspace?: Ref<Workspace | undefined>) {
  const { selectedWorkspace } = storeToRefs(useWorkspaceStore())

  const effectiveWorkspace = computed(
    () => localWorkspace?.value ?? selectedWorkspace.value
  )

  const workspaceId = computed(() => effectiveWorkspace.value?.id ?? null)

  const sensors = ref<Sensor[]>([])
  const units = ref<Unit[]>([])
  const resultQualifiers = ref<ResultQualifier[]>([])
  const processingLevels = ref<ProcessingLevel[]>([])
  const observedProperties = ref<ObservedProperty[]>([])

  const formattedObservedProperties = computed(() =>
    observedProperties.value
      .map((op) => ({
        ...op,
        title: `${op.code}: ${op.name}, ${op.type}`,
      }))
      .sort((a, b) => a.title.localeCompare(b.title))
  )

  const formattedProcessingLevels = computed(() =>
    processingLevels.value.map((pl) => ({
      ...pl,
      title: `${pl.code}: ${pl.definition}`,
    }))
  )

  const fetchMetadata = async (id: string | null) => {
    try {
      const [
        unitsResponse,
        observedPropertiesResponse,
        processingLevelsResponse,
        sensorsResponse,
        resultQualifiersResponse,
      ] = await Promise.all([
        hs.units.listAllItems({ order_by: ['name'] }),
        hs.observedProperties.listAllItems({ order_by: ['name'] }),
        hs.processingLevels.listAllItems({ order_by: ['code'] }),
        hs.sensors.listAllItems({ order_by: ['name'] }),
        hs.resultQualifiers.listAllItems({ order_by: ['code'] }),
      ])

      units.value = unitsResponse.filter(
        (u) => (u.type !== 'Time' && !u.workspaceId) || u.workspaceId === id
      )

      sensors.value = sensorsResponse.filter(
        (s) => s.workspaceId === null || s.workspaceId === id
      )

      observedProperties.value = observedPropertiesResponse.filter(
        (op) => op.workspaceId === null || op.workspaceId === id
      )

      processingLevels.value = processingLevelsResponse.filter(
        (p) => p.workspaceId === null || p.workspaceId === id
      )

      resultQualifiers.value = resultQualifiersResponse.filter(
        (r) => r.workspaceId === null || r.workspaceId === id
      )
    } catch (error) {
      console.error('Error fetching metadata', error)
    }
  }

  /**
   * Watch the effective workspace ID. When it changes (including on first mount),
   *    immediately fetch metadata if a valid workspace ID is available.
   */
  watch(
    workspaceId,
    async (id) => {
      if (id !== null) await fetchMetadata(id)
    },
    { immediate: true }
  )

  return {
    sensors,
    units,
    observedProperties,
    formattedObservedProperties,
    processingLevels,
    formattedProcessingLevels,
    resultQualifiers,
    fetchMetadata,
  }
}
