<template>
  <v-card>
    <v-card-title class="text-body-1">Find persistent values</v-card-title>

    <v-card-text>
      <div class="text-caption text-medium-emphasis mb-2">
        Flag runs of identical values that repeat at least
      </div>
      <v-text-field
        v-model.number="times"
        type="number"
        suffix="times in a row"
        min="2"
        density="comfortable"
        variant="outlined"
        hide-details
        @keyup.enter="!isUpdating && onPersistence()"
      />
    </v-card-text>

    <v-card-actions>
      <v-spacer />
      <v-btn
        color="primary"
        variant="flat"
        :disabled="isUpdating"
        @click="onPersistence"
      >
        Apply filter
      </v-btn>
    </v-card-actions>
  </v-card>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { storeToRefs } from 'pinia'
import { EnumFilterOperations } from '@uwrl/qc-utils'
import { useFilterDispatch } from '@/composables/useFilterDispatch'
import { usePlotlyStore } from '@/store/plotly'

const { isUpdating } = storeToRefs(usePlotlyStore())
const { dispatchFilter, getActiveFilterRange } = useFilterDispatch()

defineEmits(['close'])
const times = ref(2)

const onPersistence = async () => {
  await dispatchFilter(
    EnumFilterOperations.PERSISTENCE,
    times.value,
    getActiveFilterRange()
  )
}
</script>
