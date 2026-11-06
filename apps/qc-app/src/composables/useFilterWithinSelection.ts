import { computed, onScopeDispose, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { useDataVisStore } from '@/store/dataVisualization'
import { useUIStore } from '@/store/userInterface'

/**
 * The filter panels' "Search only the selected points" switch. A selection
 * picked by hand becomes the base filters search; a filter's own result
 * doesn't, so it can be re-run over the same points.
 */
export function useFilterWithinSelection() {
  const {
    filterWithinSelection,
    filterWithinBase,
    filterWithinApplying,
    selectedOperation,
  } = storeToRefs(useUIStore())
  const { selectedData } = storeToRefs(useDataVisStore())

  const setWithin = (on: boolean) => {
    const selection = selectedData.value ?? []
    filterWithinSelection.value = on && selection.length > 0
    filterWithinBase.value = filterWithinSelection.value ? [...selection] : null
  }

  // Sync, so the dispatch's `filterWithinApplying` is still set when its
  // result lands.
  watch(
    selectedData,
    (selection) => {
      if (!filterWithinSelection.value || filterWithinApplying.value) return
      if (!selection?.length) setWithin(false)
      else filterWithinBase.value = [...selection]
    },
    { flush: 'sync' }
  )
  watch(selectedOperation, () => setWithin(false))
  onScopeDispose(() => setWithin(false))

  return {
    within: computed({
      get: () => filterWithinSelection.value,
      set: setWithin,
    }),
    baseCount: computed(() => filterWithinBase.value?.length ?? 0),
    selectedCount: computed(() => selectedData.value?.length ?? 0),
  }
}
