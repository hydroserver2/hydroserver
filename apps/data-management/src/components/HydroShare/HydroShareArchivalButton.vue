<template>
  <v-btn
    color="deep-orange-lighten-1"
    @click="isHydroShareModalOpen = true"
    :loading="loading"
    :disabled="loading"
  >
    <template #loader>
      <v-progress-circular indeterminate size="16" width="2" class="mr-2" />
      ... archiving
    </template>
    {{ archivalBtnName }}
  </v-btn>
  <v-dialog v-model="isHydroShareModalOpen" width="60rem">
    <HydroShareFormCard @close="isHydroShareModalOpen = false" />
  </v-dialog>
</template>

<script setup lang="ts">
import { useHydroShareStore } from '@/store/hydroShare'
import { storeToRefs } from 'pinia'
import { computed, ref } from 'vue'
import HydroShareFormCard from './HydroShareFormCard.vue'

const { hydroShareArchive, loading } = storeToRefs(useHydroShareStore())

const isHydroShareModalOpen = ref(false)

const archivalBtnName = computed(() => {
  const BASE_NAME = 'HydroShare archival'
  if (hydroShareArchive.value) {
    if (hydroShareArchive.value.frequency)
      return `${BASE_NAME} (${hydroShareArchive.value.frequency})`
    else return `${BASE_NAME} (manual)`
  } else return `Configure ${BASE_NAME}`
})
</script>
