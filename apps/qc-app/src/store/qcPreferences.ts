/**
 * Persisted QC preferences: the last-used processing level for the create
 * form (null on first use), the time zone dates are shown in, and the plot
 * preferences the data stores expose.
 *
 * Persisted values live in small stores like this one, never in stores that
 * hold series or selections: persisting a store deep-watches all of its
 * state, so every change there would walk the whole dataset.
 */

import { defineStore } from 'pinia'
import { ref } from 'vue'
import { displayZone } from '@/utils/timeZone'
import { DEFAULT_PRESET_ID, findPreset } from '@/utils/timeRangePresets'

export const useQcPreferencesStore = defineStore(
  'qcPreferences',
  () => {
    const processingLevelId = ref<string | null>(null)

    /** Visible-point cutoff for markers and hover in automatic mode. */
    const tooltipsMaxDataPoints = ref<number>(10 * 1000)
    /** 'auto' follows the cutoff; 'manual' follows `tooltipsManualEnabled`. */
    const tooltipsMode = ref<'manual' | 'auto'>('auto')
    const tooltipsManualEnabled = ref(true)

    /** The Select view's Time range preset. */
    const selectedDateBtnId = ref(DEFAULT_PRESET_ID)
    /** The editor's Context range preset, kept apart from the Select view's
     *  so neither moves the other. */
    const contextPresetId = ref(DEFAULT_PRESET_ID)
    /** Whether the edit target's source is drawn around it as context. */
    const showSourceContext = ref(true)

    // The module-level ref, so plain utilities read the same zone.
    return {
      processingLevelId,
      displayZone,
      tooltipsMaxDataPoints,
      tooltipsMode,
      tooltipsManualEnabled,
      selectedDateBtnId,
      contextPresetId,
      showSourceContext,
    }
  },
  {
    persist: {
      key: 'qc:preferences:v1',
      // A Custom id (or a stale one) comes back with no window to resolve
      // against, so only a real preset survives hydration.
      afterHydrate: ({ store }) => {
        if (!findPreset(store.selectedDateBtnId)) {
          store.selectedDateBtnId = DEFAULT_PRESET_ID
        }
        if (!findPreset(store.contextPresetId)) {
          store.contextPresetId = DEFAULT_PRESET_ID
        }
      },
    },
  }
)
