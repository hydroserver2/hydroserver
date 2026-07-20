import { defineStore } from 'pinia'
import { Ref, ref } from 'vue'
import { HydroServer } from '@hydroserver/client'

export const useHydroServer = defineStore(
  'hydroserver',
  () => {
    const hs: Ref<null | HydroServer> = ref(null)

    return {
      hs: hs as Ref<HydroServer>
    }
  },
  { persist: false }
)
