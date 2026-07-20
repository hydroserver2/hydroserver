import { defineStore } from 'pinia'
import { ref } from 'vue'
import { DataConnection } from '@hydroserver/client'

export const useDataConnectionStore = defineStore('dataConnection', () => {
  const dataConnection = ref(new DataConnection())

  return {
    dataConnection,
  }
})
