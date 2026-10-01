/**
 * Persisted QC preferences: the last-used processing level for the create
 * form (null on first use), and the time zone dates are shown in.
 */

import { defineStore } from 'pinia'
import { ref } from 'vue'
import { displayZone } from '@/utils/timeZone'

export const useQcPreferencesStore = defineStore(
  'qcPreferences',
  () => {
    const processingLevelId = ref<string | null>(null)
    // The module-level ref, so plain utilities read the same zone.
    return { processingLevelId, displayZone }
  },
  {
    persist: {
      key: 'qc:preferences:v1',
      pick: ['processingLevelId', 'displayZone'],
    },
  }
)
