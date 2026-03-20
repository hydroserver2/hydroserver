<template>
  <div class="d-flex fill-height">
    <BrowseFilterTool :things="things" @filter="updateFilteredThings" />
    <OpenLayersMap v-if="loaded" :things="filteredThings" />
    <FullScreenLoader v-else loading-text="Loading map..." />
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import OpenLayersMap from '@/components/Maps/OpenLayersMap.vue'
import BrowseFilterTool from '@/components/Browse/BrowseFilterTool.vue'
import FullScreenLoader from '@/components/base/FullScreenLoader.vue'
import { listThingMarkers } from '@/api/thingMarkers'
import type { ThingMarker } from '@/types'

const things = ref<ThingMarker[]>([])
const filteredThings = ref<ThingMarker[]>([])
const loaded = ref(false)

const updateFilteredThings = (updatedThings: ThingMarker[]) => {
  filteredThings.value = updatedThings
}

onMounted(async () => {
  filteredThings.value = things.value = await listThingMarkers()

  // The BroseFilterTool changes the Canvas size of the Map, making it zoom too close.
  // Wait until we're sure the drawer has opened, then render map
  await new Promise((r) => setTimeout(r, 100))
  loaded.value = true
})
</script>
