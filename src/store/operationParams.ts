import { defineStore } from 'pinia'
import { ref } from 'vue'

/**
 * Per-datastream persistence for operation parameters (Find Gaps,
 * Fill Gaps). Parameters are keyed by datastream id so switching back
 * to a series restores the user's last-used threshold / cadence /
 * NoData value — otherwise every open resets to the datastream's
 * intended cadence and the user has to re-tune from scratch.
 *
 * Persistence piggybacks on pinia-plugin-persistedstate (see
 * `store/index.ts`); the store only exposes read/write helpers keyed
 * by datastream id so callers don't need to care about the storage
 * layer. Not load-bearing — the userInterface store still seeds
 * defaults from the datastream when no persisted value exists.
 */
export interface PersistedOpParams {
  gapAmount?: number
  gapUnit?: string
  fillAmount?: number
  fillUnit?: string
  noDataValue?: number
}

type AllPersisted = Record<string, PersistedOpParams>

export const useOperationParamsStore = defineStore(
  'operationParams',
  () => {
    const byDatastream = ref<AllPersisted>({})

    function load(datastreamId: string | null | undefined): PersistedOpParams | null {
      if (!datastreamId) return null
      return byDatastream.value[datastreamId] ?? null
    }

    function save(
      datastreamId: string | null | undefined,
      patch: PersistedOpParams
    ) {
      if (!datastreamId) return
      byDatastream.value = {
        ...byDatastream.value,
        [datastreamId]: { ...byDatastream.value[datastreamId], ...patch },
      }
    }

    return { byDatastream, load, save }
  },
  {
    persist: {
      key: 'qc:opParams:v1',
      pick: ['byDatastream'],
    },
  }
)
