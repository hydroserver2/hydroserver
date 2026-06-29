<template>
  <div class="browse-page">
    <BrowseFilterTool
      class="browse-filter-overlay"
      :things="things"
      :things-loaded="loaded"
      :selected-site-id="selectedThingId"
      @filter="updateFilteredThings"
      @select-site="selectedThingId = $event"
    />
    <OpenLayersMap
      v-if="loaded"
      class="browse-map"
      :things="filteredThings"
      :fit-padding="mapFitPadding"
      :selected-thing-id="selectedThingId"
    />
    <FullScreenLoader v-else loading-text="Loading map..." />
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import OpenLayersMap from '@/components/Maps/OpenLayersMap.vue'
import BrowseFilterTool from '@/components/Browse/BrowseFilterTool.vue'
import FullScreenLoader from '@/components/base/FullScreenLoader.vue'
import hs from '@hydroserver/client'
import type { ThingMarker } from '@hydroserver/client'

const things = ref<ThingMarker[]>([])
const filteredThings = ref<ThingMarker[]>([])
const selectedThingId = ref<string>()
const loaded = ref(false)
const mapFitPadding: [number, number, number, number] = [44, 88, 96, 400]

const updateFilteredThings = (updatedThings: ThingMarker[]) => {
  filteredThings.value = updatedThings
  if (
    selectedThingId.value &&
    !updatedThings.some((thing) => thing.id === selectedThingId.value)
  ) {
    selectedThingId.value = undefined
  }
}

onMounted(async () => {
  const res = await hs.things.listMarkers()
  filteredThings.value = things.value = res.ok ? res.data : []

  await new Promise((r) => setTimeout(r, 100))
  loaded.value = true
})
</script>

<style scoped>
.browse-page {
  position: relative;
  height: calc(100dvh - var(--v-layout-top, 0px));
  min-height: 520px;
  overflow: hidden;
}

.browse-map {
  width: 100%;
  height: 100%;
}

.browse-filter-overlay {
  position: absolute;
  top: 16px;
  left: 16px;
  z-index: 1000;
}

@media (max-width: 700px) {
  .browse-filter-overlay {
    top: 12px;
    left: 12px;
    right: 12px;
  }
}
</style>
