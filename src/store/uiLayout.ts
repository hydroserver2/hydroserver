import { defineStore } from 'pinia'
import { ref } from 'vue'

/**
 * Persisted UI-layout state — sidebar widths, split percentages, and
 * collapse flags. Backed by pinia-plugin-persistedstate (see
 * `store/index.ts`) so reloads restore the user's last arrangement.
 *
 * Keyed by the same string identifiers the `useResizable` /
 * `usePersistedFlag` composables accept, so existing call sites
 * don't need to change their identifiers.
 */
export const useUiLayoutStore = defineStore(
  'uiLayout',
  () => {
    const sizes = ref<Record<string, number>>({})
    const flags = ref<Record<string, boolean>>({})

    function getSize(key: string): number | null {
      const v = sizes.value[key]
      return typeof v === 'number' && Number.isFinite(v) ? v : null
    }

    function setSize(key: string, value: number) {
      sizes.value = { ...sizes.value, [key]: value }
    }

    function getFlag(key: string): boolean | null {
      const v = flags.value[key]
      return typeof v === 'boolean' ? v : null
    }

    function setFlag(key: string, value: boolean) {
      flags.value = { ...flags.value, [key]: value }
    }

    return { sizes, flags, getSize, setSize, getFlag, setFlag }
  },
  {
    persist: {
      key: 'qc:uiLayout',
      pick: ['sizes', 'flags'],
    },
  }
)
