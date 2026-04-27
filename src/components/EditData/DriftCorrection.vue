<template>
  <v-card>
    <v-card-title>Drift correction</v-card-title>
    <v-card-subtitle v-if="selectedGroups.length">
      <v-icon icon="mdi-chart-sankey" size="14" class="mr-1" />
      {{ selectedGroups.length }} consecutive group{{
        selectedGroups.length === 1 ? '' : 's'
      }}
    </v-card-subtitle>

    <v-card-text>
      <v-alert
        v-if="selectedGroups.length === 0"
        type="warning"
        density="compact"
        variant="tonal"
        class="text-body-2 mb-3"
      >
        Select two or more consecutive points on the plot. Multiple groups are
        allowed — each will be corrected independently.
      </v-alert>
      <v-alert
        v-else-if="selectedGroups.length > 1"
        type="info"
        density="compact"
        variant="tonal"
        class="text-body-2 mb-3"
      >
        Drift correction will be applied to each group individually.
      </v-alert>

      <div v-if="selectedGroups.length" class="mb-3">
        <div class="text-caption text-medium-emphasis mb-1">Groups</div>
        <div class="drift-groups d-flex flex-column">
          <div
            v-for="(group, i) of selectedGroups"
            :key="i"
            class="drift-groups__row d-flex align-center py-1"
          >
            <v-avatar size="20" color="primary" variant="tonal" class="mr-2">
              <span class="text-caption">{{ i + 1 }}</span>
            </v-avatar>
            <div class="d-flex flex-column flex-grow-1" style="min-width: 0">
              <span class="text-body-2 font-weight-medium">
                {{ group.length }} points
              </span>
              <span class="text-caption text-medium-emphasis text-truncate">
                starts {{ getGroupStart(group) }}
              </span>
            </div>
          </div>
        </div>
      </div>

      <div class="text-caption text-medium-emphasis mb-1">Drift amount</div>
      <v-text-field
        v-model="driftGapWidth"
        type="number"
        step="0.1"
        density="comfortable"
        variant="outlined"
        hide-details
        class="mb-3"
        @keyup.enter="
          !isUpdating && selectedGroups.length && onDriftCorrection()
        "
      />

      <div class="text-caption text-medium-emphasis mb-1">Method</div>
      <v-radio-group
        hide-details
        color="primary"
        v-model="selectedDriftCorrectionMethod"
        density="compact"
      >
        <v-radio
          label="Linear drift correction"
          :value="DriftCorrectionMethods.LINEAR"
        />
      </v-radio-group>
    </v-card-text>

    <v-card-actions>
      <v-spacer />
      <v-btn
        color="primary"
        variant="flat"
        :disabled="selectedGroups.length === 0 || isUpdating"
        @click="onDriftCorrection"
      >
        Apply
      </v-btn>
    </v-card-actions>
  </v-card>
</template>

<script setup lang="ts">
import { storeToRefs } from 'pinia'
import { useDataVisStore } from '@/store/dataVisualization'
import { EnumEditOperations } from '@uwrl/qc-utils'
import { computed } from 'vue'
import { formatDate } from '@uwrl/qc-utils'
import { usePlotlyStore } from '@/store/plotly'
import { useFilterDispatch } from '@/composables/useFilterDispatch'
import { useUIStore, DriftCorrectionMethods } from '@/store/userInterface'
const { recordPostActionSelection } = useFilterDispatch()
const { selectedSeries, plotlyRef, isUpdating } = storeToRefs(usePlotlyStore())
const { driftGapWidth, selectedDriftCorrectionMethod } =
  storeToRefs(useUIStore())
const { redraw } = usePlotlyStore()

const { selectedData } = storeToRefs(useDataVisStore())
const emit = defineEmits(['close'])

const selectedGroups = computed((): number[][] => {
  if (!selectedData.value?.length) {
    return []
  }

  let groups: number[][] = [[]]

  selectedData.value.reduce((acc: number[][], curr) => {
    const target: number[] = acc[acc.length - 1] as number[]

    // @ts-ignore
    if (!target.length || curr == target[target.length - 1] + 1) {
      target.push(curr)
    } else {
      acc.push([curr])
    }

    return acc
  }, groups)

  return groups.filter((g) => g.length > 1)
})

const onDriftCorrection = async () => {
  const indices = selectedGroups.value.flat()

  isUpdating.value = true

  setTimeout(async () => {
    // No ranges arg — qc-utils' dispatch reads the target indices
    // off the preceding SELECTION in history, partitions them into
    // consecutive groups, and applies the same `value` drift to
    // each group as one logged operation.
    await selectedSeries.value?.data.dispatch([
      [EnumEditOperations.DRIFT_CORRECTION, +driftGapWidth.value],
    ])
    isUpdating.value = false
    await redraw()
    await recordPostActionSelection(indices)
    emit('close')
  })
}

const getGroupStart = (group: number[]) => {
  const xData = plotlyRef.value?.data[0].x
  if (!xData) return ''
  return formatDate(new Date(xData[group[0] as number]))
}
</script>

<style scoped>
.drift-groups {
  max-height: 10rem;
  overflow-y: auto;
  border: 1px solid rgba(var(--v-theme-on-surface), 0.08);
  border-radius: 4px;
  padding: 4px 8px;
}

.drift-groups__row + .drift-groups__row {
  border-top: 1px dashed rgba(var(--v-theme-on-surface), 0.06);
}
</style>
