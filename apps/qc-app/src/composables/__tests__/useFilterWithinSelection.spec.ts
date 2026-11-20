import { describe, it, expect, beforeEach } from 'vitest'
import { createPinia, setActivePinia, storeToRefs } from 'pinia'
import { effectScope } from 'vue'
import { useFilterWithinSelection } from '@/composables/useFilterWithinSelection'
import { useDataVisStore } from '@/store/dataVisualization'
import { useUIStore } from '@/store/userInterface'

describe('useFilterWithinSelection', () => {
  let scope: ReturnType<typeof effectScope>
  let api: ReturnType<typeof useFilterWithinSelection>
  let ui: ReturnType<typeof useUIStore>
  let selectedData: ReturnType<typeof storeToRefs<ReturnType<typeof useDataVisStore>>>['selectedData']

  beforeEach(() => {
    setActivePinia(createPinia())
    ui = useUIStore()
    selectedData = storeToRefs(useDataVisStore()).selectedData
    selectedData.value = [3, 4, 5]
    scope = effectScope()
    api = scope.run(() => useFilterWithinSelection())!
  })

  it('keeps the selection as the base when turned on', () => {
    api.within.value = true
    expect(ui.filterWithinSelection).toBe(true)
    expect(ui.filterWithinBase).toEqual([3, 4, 5])
    expect(api.baseCount.value).toBe(3)
  })

  it('stays off with nothing selected', () => {
    selectedData.value = []
    api.within.value = true
    expect(api.within.value).toBe(false)
    expect(ui.filterWithinBase).toBeNull()
  })

  it('takes a selection picked by hand as the new base', () => {
    api.within.value = true
    selectedData.value = [8, 9]
    expect(ui.filterWithinBase).toEqual([8, 9])
  })

  it("keeps the base when a filter writes its result", () => {
    api.within.value = true
    ui.filterWithinApplying = true
    selectedData.value = [4]
    ui.filterWithinApplying = false
    expect(ui.filterWithinBase).toEqual([3, 4, 5])
  })

  it('turns off when the selection is cleared', () => {
    api.within.value = true
    selectedData.value = []
    expect(api.within.value).toBe(false)
  })

  it('turns off when the operation changes or the panel closes', () => {
    api.within.value = true
    ui.selectedOperation = 'persistence'
    return Promise.resolve().then(() => {
      expect(api.within.value).toBe(false)
      api.within.value = true
      scope.stop()
      expect(ui.filterWithinSelection).toBe(false)
    })
  })
})
