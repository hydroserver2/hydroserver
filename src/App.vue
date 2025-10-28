<template>
  <v-app>
    <v-main>
      <FullScreenLoader v-if="isLoading" />
      <router-view v-else />
    </v-main>

    <Notifications />
  </v-app>
</template>

<script setup lang="ts">
import Notifications from '@/components/base/Notifications.vue'
import FullScreenLoader from '@/components/base/FullScreenLoader.vue'

import { setupRouteGuards } from '@/router/router'
// import { api } from '@uwrl/qc-utils'
import { ref } from 'vue'
import { useDataVisStore } from '@/store/dataVisualization'
import { storeToRefs } from 'pinia'
import { HydroServer } from '@hydroserver/client'

const hs = await HydroServer.initialize({
  host: import.meta.env.VITE_APP_API_URL,
})

// Use stores
const isLoading = ref(true)

const { things, processingLevels, observedProperties, datastreams } =
  storeToRefs(useDataVisStore())

const initializeHydroServer = async () => {
  const [
    thingsResponse,
    datastreamsResponse,
    processingLevelsResponse,
    observedPropertiesResponse,
  ] = await Promise.all([
    hs.things.list(),
    hs.datastreams.list(),
    hs.processingLevels.list(),
    hs.observedProperties.list(),
  ])

  things.value = thingsResponse.data
  datastreams.value = datastreamsResponse.data
  processingLevels.value = processingLevelsResponse.data
  observedProperties.value = observedPropertiesResponse.data

  isLoading.value = false
}

initializeHydroServer()
// TODO: use route guard setup in Router v3
setupRouteGuards()
</script>
