import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useMetadata = defineStore('metadata', () => {
  const tab = ref(0)

  return {
    tab,
  }
})
