import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import {
  ExtractorConfig,
  TransformerConfig,
  LoaderConfig,
  DataConnection,
} from '@hydroserver/client'

export const useDataConnectionStore = defineStore('dataConnection', () => {
  const dataConnection = ref(new DataConnection())
  const openDataConnectionTableDialog = ref(false)

  const extractor = computed<ExtractorConfig>({
    get() {
      return dataConnection.value.extractor
    },
    set(newVal) {
      dataConnection.value.extractor = newVal
    },
  })

  const transformer = computed<TransformerConfig>({
    get() {
      return dataConnection.value.transformer
    },
    set(newVal) {
      dataConnection.value.transformer = newVal
    },
  })

  const loader = computed<LoaderConfig>({
    get() {
      return dataConnection.value.loader
    },
    set(newVal) {
      dataConnection.value.loader = newVal
    },
  })

  const isExtractorValid = ref(true)
  const isTransformerValid = ref(true)
  const isLoaderValid = ref(true)

  return {
    dataConnection,
    openDataConnectionTableDialog,
    extractor,
    transformer,
    loader,
    isExtractorValid,
    isTransformerValid,
    isLoaderValid,
  }
})
