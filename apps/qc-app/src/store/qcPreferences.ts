/**
 * Persisted QC editing preferences.
 *
 * Currently just the last-used processing level for the "Create Datastream
 * for Editing" form, so the user's choice is remembered across reloads.
 * Defaults to null (no assumed processing level on first use).
 */

import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useQcPreferencesStore = defineStore(
  'qcPreferences',
  () => {
    const processingLevelId = ref<string | null>(null)
    return { processingLevelId }
  },
  {
    persist: {
      key: 'qc:preferences:v1',
      pick: ['processingLevelId'],
    },
  }
)
