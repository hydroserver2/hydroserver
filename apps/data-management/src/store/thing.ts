import { defineStore } from 'pinia'
import { ref } from 'vue'
import { Thing } from '@hydroserver/client'

export const useThingStore = defineStore('thing', () => {
  const thing = ref<Thing | undefined>()

  return {
    thing,
  }
})
