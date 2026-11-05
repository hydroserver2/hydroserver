<template>
  <v-card v-if="isProfileDatastream(datastream)" class="profile-popup">
    <ProfileViewer :datastream="datastream" />
    <v-card-actions
      ><v-spacer /><v-btn-cancel @click="$emit('close')"
        >Close</v-btn-cancel
      ></v-card-actions
    >
  </v-card>
  <TimeSeriesPopupPlot
    v-else
    :datastream="datastream"
    @close="$emit('close')"
  />
</template>
<script setup lang="ts">
import type { Datastream } from '@hydroserver/client'
import { isProfileDatastream } from '@/models/profile'
import ProfileViewer from '@/components/Profile/ProfileViewer.vue'
import TimeSeriesPopupPlot from './TimeSeriesPopupPlot.vue'
defineProps<{ datastream: Datastream }>()
defineEmits<{ close: [] }>()
</script>
<style scoped>
.profile-popup {
  display: flex;
  flex-direction: column;
  height: min(80dvh, 48rem);
  overflow: auto;
}
.profile-popup > :first-child {
  flex: 1;
  min-height: 0;
}
</style>
