<template>
  <div class="d-flex flex-column">
    <div class="d-flex px-4 justify-space-between align-center">
      <div class="d-flex align-center gap-2">
        <v-switch
          v-model="areTooltipsEnabled"
          @update:model-value="handleRelayout"
          color="primary"
          label="Tooltips"
          :disabled="visiblePoints > tooltipsMaxDataPoints"
          hide-details
        />

        <v-progress-circular v-if="isUpdating" color="primary" indeterminate />

        <!-- <v-text-field
          type="number"
          label="Disable tooltips after"
          v-model="tooltipsMaxDataPoints"
          density="compact"
          hide-details
          suffix="data points"
          min="0"
          width="240"
          :loading="isUpdating"
        ></v-text-field> -->

        <!-- <label v-if="visiblePoints"
          >Showing <span class="text-red">{{ visiblePoints }}</span> data
          points</label
        > -->
      </div>

      <div v-if="showCoordinates" class="text-medium-emphasis text-body-2">
        <div>{{ hover.y }}</div>
        <div>{{ formatDate(new Date(hover.x)) }}</div>
      </div>

      <div class="d-flex align-center gap-1">
        <v-chip
          v-if="selectedData?.length"
          :model-value="true"
          class="ma-2"
          close-icon="mdi-close"
          @click:close="clearSelected"
          color="red"
          prepend-icon="mdi-checkbox-marked-circle"
          closable
        >
          Selected: <b class="ml-1 mr-2">{{ selectedData?.length }}</b>
        </v-chip>
      </div>
    </div>
    <v-divider></v-divider>

    <div class="d-flex flex-row flex-grow-1">
      <v-tabs
        v-model="tab"
        @update:model-value="onTabChange"
        direction="vertical"
        style="width: 50px; border-right: 1px solid #ddd"
        class="bg-grey-lighten-4"
      >
        <v-tab value="plot"><v-icon icon="mdi-chart-line"></v-icon></v-tab>
        <v-tab value="table"><v-icon icon="mdi-table"></v-icon></v-tab>
      </v-tabs>

      <v-tabs-window v-model="tab" class="flex-grow-1">
        <v-tabs-window-item value="plot" class="fill-height">
          <div ref="plot" class="fill-height"></div>
        </v-tabs-window-item>

        <v-tabs-window-item value="table" class="fill-height">
          <!-- Important to NOT keep the DataTable component in memory if the tab is not shown -->
          <DataTable v-if="tab === 'table'" class="fill-height"
        /></v-tabs-window-item>
      </v-tabs-window>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'

import { usePlotlyStore } from '@/store/plotly'
import { storeToRefs } from 'pinia'
import { useDataVisStore } from '@/store/dataVisualization'
import { handleNewPlot, handleRelayout } from '@/utils/plotting/plotly'
import DataTable from '@/components/VisualizeData/DataTable.vue'
import { useDataSelection } from '@/composables/useDataSelection'
import { formatDate } from '@uwrl/qc-utils'

const { dispatchSelection } = useDataSelection()
const { clearSelected } = useDataSelection()
const plot = ref<HTMLDivElement>()
const { isUpdating, areTooltipsEnabled, visiblePoints, tooltipsMaxDataPoints, hover, showCoordinates } =
  storeToRefs(usePlotlyStore())
const { selectedData } = storeToRefs(useDataVisStore())
const tab = ref('plot')

onMounted(async () => {
  // This timeout halts the execution of handleNewPlot until the view switching animation is complete, and the container has expanded.
  setTimeout(() => {
    handleNewPlot(plot.value)
  }, 200)
})

const onTabChange = () => {
  if (tab.value === 'plot') {
    setTimeout(() => {
      dispatchSelection(selectedData.value || [])
    })
  }
}
</script>

<style scoped>
:deep(.js-plotly-plot .plotly) {
  .drag.cursor-ns-resize,
  .drag.cursor-n-resize,
  .drag.cursor-s-resize,
  .drag.cursor-w-resize,
  .drag.cursor-ew-resize,
  .drag.cursor-e-resize {
    fill: #f8f8f8 !important;
    stroke: #f8f8f8 !important;
    stroke-width: 1px !important;
  }

  .drag.cursor-sw-resize,
  .drag.cursor-nw-resize,
  .drag.cursor-ne-resize,
  .drag.cursor-se-resize {
    fill: #f2f2f2 !important;
    stroke: #f2f2f2 !important;
    stroke-width: 1px !important;
  }
}

:deep(.v-window__container) {
  height: 100%;
}
</style>
