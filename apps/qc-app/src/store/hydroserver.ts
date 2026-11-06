import { defineStore } from 'pinia'
import { Ref, ref } from 'vue'
import { HydroServer } from '@hydroserver/client'

export const useHydroServer = defineStore(
  'hydroserver',
  () => {
    const hs: Ref<null | HydroServer> = ref(null)
    // Set when the server rejects a request because the login ended.
    const sessionExpired = ref(false)

    return {
      hs: hs as Ref<HydroServer>,
      sessionExpired,
    }
  },
  { persist: false }
)
