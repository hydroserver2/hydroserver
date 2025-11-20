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
import { ref } from 'vue'
import { useDataVisStore } from '@/store/dataVisualization'
import { useHydroServer } from '@/store/hydroserver'
import { storeToRefs } from 'pinia'
import { HydroServer } from '@hydroserver/client'

// Use stores
const isLoading = ref(true)

const { things, processingLevels, observedProperties, datastreams } =
  storeToRefs(useDataVisStore())

const { hs } = storeToRefs(useHydroServer())

const initializeHydroServer = async () => {
  hs.value = await HydroServer.initialize({
    host: import.meta.env.VITE_APP_API_URL,
  })
  await hs.value.session.login(
    import.meta.env.VITE_APP_HS_USER,
    import.meta.env.VITE_APP_HS_PW
  )

  const [
    thingsResponse,
    datastreamsResponse,
    processingLevelsResponse,
    observedPropertiesResponse,
  ] = await Promise.all([
    hs.value.things.list(),
    hs.value.datastreams.list({ expand_related: true }), // TODO: get type definitions when using `expand_related`
    hs.value.processingLevels.list(),
    hs.value.observedProperties.list(),
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
