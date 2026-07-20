import { defineStore } from 'pinia'
import { ref } from 'vue'

/**
 * Per-datastream persistence for operation parameters (Find Gaps,
 * Fill Gaps). Parameters are keyed by datastream id so switching back
 * to a series restores the user's last-used threshold / cadence /
 * NoData value; otherwise every open resets to the datastream's
 * intended cadence and the user has to re-tune from scratch.
 *
 * Persistence piggybacks on pinia-plugin-persistedstate (see
 * `store/index.ts`); the store only exposes read/write helpers keyed
 * by datastream id so callers don't need to care about the storage
 * layer. Not load-bearing: the userInterface store still seeds
 * defaults from the datastream when no persisted value exists.
 *
 * Slot a datastream remembers between sessions. Every field is
 * optional so partial writes (e.g. the user only changed the gap
 * threshold) don't clobber unrelated fields.
 *
 *   - `gapAmount` / `gapUnit`: Find Gaps threshold.
 *   - `fillAmount` / `fillUnit`: Fill Gaps cadence.
 *   - `noDataValue`: sentinel value the user types when declaring a
 *     fill is "missing" rather than zero.
 *
 * The userInterface store reads these via `load()` and falls back to
 * datastream-derived defaults when a field is absent.
 */
export interface PersistedOpParams {
  gapAmount?: number
  gapUnit?: string
  fillAmount?: number
  fillUnit?: string
  noDataValue?: number
}

/** Persisted-state shape: datastream id -> its remembered slot. */
type AllPersisted = Record<string, PersistedOpParams>

export const useOperationParamsStore = defineStore(
  'operationParams',
  () => {
    /** All per-datastream slots; keyed by datastream id. Persisted. */
    const byDatastream = ref<AllPersisted>({})

    /**
     * Read the slot for `datastreamId`. Returns `null` when nothing
     * has been stored yet or the id is missing. Callers seed from
     * the datastream's intrinsic cadence in that case.
     */
    function load(datastreamId: string | null | undefined): PersistedOpParams | null {
      if (!datastreamId) return null
      return byDatastream.value[datastreamId] ?? null
    }

    /**
     * Merge `patch` into the slot for `datastreamId`. A partial patch
     * (only the field the user just touched) leaves the rest of the
     * slot intact. Allocates a new outer + inner record so the
     * persistence plugin and reactive watchers both fire.
     */
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
