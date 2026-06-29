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
      selectable
      :things="filteredThings"
      :fit-padding="mapFitPadding"
      :selected-thing-id="selectedThingId"
      @select="selectedThingId = $event"
    />
    <FullScreenLoader v-else loading-text="Loading map..." />
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import OpenLayersMap from '@/components/Maps/OpenLayersMap.vue'
import BrowseFilterTool from '@/components/Browse/BrowseFilterTool.vue'
import FullScreenLoader from '@/components/base/FullScreenLoader.vue'
import hs from '@hydroserver/client'
import type { ThingMarker } from '@hydroserver/client'

const desktopMapFitPadding: [number, number, number, number] = [
  44, 88, 96, 400,
]
const compactMapFitPadding: [number, number, number, number] = [
  72, 48, 72, 48,
]

const things = ref<ThingMarker[]>([])
const filteredThings = ref<ThingMarker[]>([])
const selectedThingId = ref<string>()
const loaded = ref(false)
const isCompactMapViewport = ref(false)
const mapFitPadding = computed<[number, number, number, number]>(() =>
  isCompactMapViewport.value ? compactMapFitPadding : desktopMapFitPadding
)

let compactMapQuery: MediaQueryList | undefined

const updateCompactMapViewport = (event?: MediaQueryListEvent) => {
  isCompactMapViewport.value =
    event?.matches ?? compactMapQuery?.matches ?? false
}

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
  compactMapQuery = window.matchMedia('(max-width: 700px)')
  updateCompactMapViewport()
  compactMapQuery.addEventListener('change', updateCompactMapViewport)

  const res = await hs.things.listMarkers()
  filteredThings.value = things.value = res.ok ? res.data : []

  await new Promise((r) => setTimeout(r, 100))
  loaded.value = true
})

onBeforeUnmount(() => {
  compactMapQuery?.removeEventListener('change', updateCompactMapViewport)
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
    inset: 0;
  }

  .browse-filter-overlay:not(.browse-filter-tool--expanded) {
    inset: 12px auto auto 12px;
  }
}
</style>
