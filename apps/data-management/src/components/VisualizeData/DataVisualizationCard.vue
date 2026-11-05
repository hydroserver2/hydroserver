<template>
  <v-card v-if="profile" flat class="hs-table-card profile-visualization"
    ><ProfileViewer :key="profile.id" :datastream="profile" sync-route
  /></v-card>
  <TimeSeriesVisualizationCard
    v-else
    :card-height="cardHeight"
    @minimum-height="$emit('minimumHeight', $event)"
  />
</template>
<script setup lang="ts">
import { computed, watch } from 'vue'
import { useDataVisStore } from '@/store/dataVisualization'
import { isProfileDatastream } from '@/models/profile'
import ProfileViewer from '@/components/Profile/ProfileViewer.vue'
import TimeSeriesVisualizationCard from './TimeSeriesVisualizationCard.vue'
defineProps<{ cardHeight: number }>()
const emit = defineEmits<{ minimumHeight: [height: number] }>()
const store = useDataVisStore()
const profile = computed(() =>
  store.plottedDatastreams.find(isProfileDatastream)
)
watch(
  profile,
  (value) => {
    if (value) emit('minimumHeight', 420)
  },
  { immediate: true }
)
</script>
<style scoped>
.profile-visualization {
  min-height: 0;
  height: 100%;
}
</style>
