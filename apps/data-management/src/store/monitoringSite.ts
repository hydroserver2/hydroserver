import { defineStore } from 'pinia'
import { ref } from 'vue'
import { MonitoringSite } from '@hydroserver/client'

export const useMonitoringSiteStore = defineStore('monitoringSite', () => {
  const monitoringSite = ref<MonitoringSite | undefined>()

  return {
    monitoringSite,
  }
})
