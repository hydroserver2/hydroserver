import { defineStore } from 'pinia'
import { ref } from 'vue'

/**
 * Persisted UI-layout state: drawer / split widths and collapse flags
 * the user drags or toggles. Backed by pinia-plugin-persistedstate (see
 * `store/index.ts`); the persisted slice survives reload so users keep
 * the arrangement they last left.
 *
 * Two flat maps keyed by string identifiers:
 *   - `sizes`: numeric values written by `useResizable` (pixel widths,
 *     percentages). Read back via `getSize(key)`, written via `setSize`.
 *   - `flags`: boolean toggles written by `usePersistedFlag` (drawer
 *     open / collapsed, panel expanded). Read via `getFlag`, written
 *     via `setFlag`.
 *
 * Identifier strings come from the calling composable and aren't
 * enumerated here. That keeps the contract one-sided so a new
 * resizable component can be added without touching this store.
 */
export const useUiLayoutStore = defineStore(
  'uiLayout',
  () => {
    /** Numeric layout values keyed by composable-supplied id. */
    const sizes = ref<Record<string, number>>({})
    /** Boolean toggle values keyed by composable-supplied id. */
    const flags = ref<Record<string, boolean>>({})

    /**
     * Read a stored size. Returns `null` when nothing was stored or the
     * stored value is non-finite (`NaN`, `Infinity`). Callers fall
     * back to a component default in that case.
     */
    function getSize(key: string): number | null {
      const v = sizes.value[key]
      return typeof v === 'number' && Number.isFinite(v) ? v : null
    }

    /**
     * Persist a size. Allocates a new object so pinia-plugin-persistedstate
     * sees a reactive write and reactive consumers refresh; mutating
     * the existing record in place skips both.
     */
    function setSize(key: string, value: number) {
      sizes.value = { ...sizes.value, [key]: value }
    }

    /**
     * Read a stored boolean flag. Returns `null` when nothing was
     * stored so the caller can distinguish "user hasn't toggled this
     * yet" from "user explicitly set false".
     */
    function getFlag(key: string): boolean | null {
      const v = flags.value[key]
      return typeof v === 'boolean' ? v : null
    }

    /**
     * Persist a flag. Same fresh-object pattern as `setSize` so the
     * persistence plugin and reactive watchers both fire.
     */
    function setFlag(key: string, value: boolean) {
      flags.value = { ...flags.value, [key]: value }
    }

    return { sizes, flags, getSize, setSize, getFlag, setFlag }
  },
  {
    // `:v1` suffix matches the `qc-utils:calibration:v1` template so
    // a future shape change can be invalidated by bumping the version.
    persist: {
      key: 'qc:uiLayout:v1',
      pick: ['sizes', 'flags'],
    },
  }
)
