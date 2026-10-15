import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { createApp, nextTick } from 'vue'
import { createPinia, setActivePinia } from 'pinia'
import piniaPluginPersistedstate from 'pinia-plugin-persistedstate'
import { useDataVisStore } from '@/store/dataVisualization'
import { usePlotlyStore } from '@/store/plotly'
import { useQcSessionStore } from '@/store/qcSession'
import { useObservationStore } from '@/store/observations'
import { useQcPreferencesStore } from '@/store/qcPreferences'
import { useEditResumeStore } from '@/store/editResume'

// Persisting a store deep-watches all of its state, so a store holding
// series or selections would walk the whole dataset on every change.
describe('store persistence', () => {
  beforeEach(() => {
    localStorage.clear()
    const pinia = createPinia()
    pinia.use(piniaPluginPersistedstate)
    createApp({ render: () => null }).use(pinia)
    setActivePinia(pinia)
  })
  afterEach(() => localStorage.clear())

  it('never persists the stores that hold data', () => {
    for (const store of [
      useDataVisStore(),
      usePlotlyStore(),
      useQcSessionStore(),
      useObservationStore(),
    ]) {
      expect(store, store.$id).not.toHaveProperty('$persist')
    }
  })

  it('shares the persisted preferences with the data stores', () => {
    const prefs = useQcPreferencesStore()
    usePlotlyStore().tooltipsMode = 'manual'
    useDataVisStore().contextPresetId = 3
    expect(prefs.tooltipsMode).toBe('manual')
    expect(prefs.contextPresetId).toBe(3)
  })

  it('persists the resume pointer through its own store', async () => {
    useQcSessionStore().resumeDatastreamId = 'mgd'
    await nextTick()
    expect(useEditResumeStore().resumeDatastreamId).toBe('mgd')
    expect(
      JSON.parse(localStorage.getItem('qc:editResume:v1') ?? '{}')
    ).toEqual({ resumeDatastreamId: 'mgd' })
  })
})
