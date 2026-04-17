<template>
  <div class="d-flex flex-column">
    <div class="d-flex px-4 py-1 justify-space-between align-center">
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
      </div>

      <div v-if="showCoordinates" class="text-medium-emphasis text-body-2">
        <div>{{ hover.y }}</div>
        <div>{{ formatDate(new Date(hover.x)) }}</div>
      </div>

      <div class="d-flex align-center gap-1">
        <v-menu
          v-model="showHelp"
          :close-on-content-click="false"
          location="bottom end"
          offset="6"
        >
          <template v-slot:activator="{ props: menuProps }">
            <v-btn
              v-bind="menuProps"
              variant="text"
              size="small"
              prepend-icon="mdi-help-circle-outline"
            >
              Plot controls
            </v-btn>
          </template>

          <v-card max-width="360" class="plot-help">
            <v-card-title class="text-subtitle-1 d-flex align-center gap-2">
              <v-icon icon="mdi-gesture-tap" size="20" />
              Plot controls
            </v-card-title>
            <v-divider />
            <v-list density="compact" class="py-1" lines="two">
              <v-list-subheader class="text-uppercase text-caption font-weight-bold">
                Gestures
              </v-list-subheader>
              <v-list-item
                v-for="(g, i) in gestures"
                :key="`g-${i}`"
                class="px-4"
              >
                <template v-slot:prepend>
                  <v-icon :icon="g.icon" size="18" class="mr-2" />
                </template>
                <v-list-item-title class="text-body-2 font-weight-medium">
                  {{ g.title }}
                </v-list-item-title>
                <v-list-item-subtitle class="text-caption">
                  {{ g.desc }}
                </v-list-item-subtitle>
              </v-list-item>

              <v-divider class="my-1" />

              <v-list-subheader class="text-uppercase text-caption font-weight-bold">
                Toolbar icons
              </v-list-subheader>
              <v-list-item
                v-for="(b, i) in modebarIcons"
                :key="`mb-${i}`"
                class="px-4"
              >
                <template v-slot:prepend>
                  <v-icon :icon="b.icon" size="18" class="mr-2" />
                </template>
                <v-list-item-title class="text-body-2 font-weight-medium">
                  {{ b.title }}
                </v-list-item-title>
                <v-list-item-subtitle class="text-caption">
                  {{ b.desc }}
                </v-list-item-subtitle>
              </v-list-item>
            </v-list>
          </v-card>
        </v-menu>
      </div>
    </div>

    <div
      v-if="showTip && !selectedData?.length"
      class="plot-tip px-4 py-1 d-flex align-center gap-2 text-caption"
    >
      <v-icon icon="mdi-lightbulb-on-outline" size="16" color="primary" />
      <span>
        <b>Tip:</b>
        drag across the plot to select points, drag the edges of the axes to
        rescale, or scroll on the plot to zoom.
      </span>
      <v-spacer />
      <v-btn
        size="x-small"
        variant="text"
        icon="mdi-close"
        @click="showTip = false"
      />
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
        <v-tooltip location="end" text="Plot view">
          <template v-slot:activator="{ props: tooltipProps }">
            <v-tab v-bind="tooltipProps" value="plot">
              <v-icon icon="mdi-chart-line"></v-icon>
            </v-tab>
          </template>
        </v-tooltip>
        <v-tooltip location="end" text="Table view">
          <template v-slot:activator="{ props: tooltipProps }">
            <v-tab v-bind="tooltipProps" value="table">
              <v-icon icon="mdi-table"></v-icon>
            </v-tab>
          </template>
        </v-tooltip>
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
const plot = ref<HTMLDivElement>()
const {
  isUpdating,
  areTooltipsEnabled,
  visiblePoints,
  tooltipsMaxDataPoints,
  hover,
  showCoordinates,
} = storeToRefs(usePlotlyStore())
const { selectedData } = storeToRefs(useDataVisStore())
const tab = ref('plot')

const showHelp = ref(false)
const showTip = ref(true)

const gestures = [
  {
    icon: 'mdi-cursor-default-click-outline',
    title: 'Click a point',
    desc: 'Toggle a single point in the selection',
  },
  {
    icon: 'mdi-selection-drag',
    title: 'Box / lasso select',
    desc: 'Enable Box or Lasso on the toolbar, then drag across the plot',
  },
  {
    icon: 'mdi-pan',
    title: 'Pan',
    desc: 'With Pan active, drag anywhere to move the view',
  },
  {
    icon: 'mdi-mouse',
    title: 'Scroll to zoom',
    desc: 'Scroll over the plot to zoom in or out on time',
  },
  {
    icon: 'mdi-arrow-expand-vertical',
    title: 'Resize an axis',
    desc: 'Drag near the ends of a Y axis to rescale that axis only',
  },
  {
    icon: 'mdi-gesture-double-tap',
    title: 'Double-click axis',
    desc: 'Double-click a Y or X axis to reset its range',
  },
]

const modebarIcons = [
  {
    icon: 'mdi-magnify-plus-outline',
    title: 'Zoom',
    desc: 'Drag a rectangle to zoom the view to that region',
  },
  {
    icon: 'mdi-cursor-move',
    title: 'Pan',
    desc: 'Drag anywhere to move the plot without changing zoom',
  },
  {
    icon: 'mdi-vector-rectangle',
    title: 'Box Select',
    desc: 'Drag a rectangle to select all contained points',
  },
  {
    icon: 'mdi-lasso',
    title: 'Lasso Select',
    desc: 'Draw a free-form shape to select enclosed points',
  },
  {
    icon: 'mdi-magnify-plus',
    title: 'Zoom in / out',
    desc: 'Step the x-axis zoom in or out',
  },
  {
    icon: 'mdi-home-outline',
    title: 'Reset axes',
    desc: 'Return all axes to their original range',
  },
  {
    icon: 'mdi-arrow-collapse-vertical',
    title: 'Autoscale Y',
    desc: 'Fit the Y axis to currently visible data',
  },
  {
    icon: 'mdi-cursor-default-outline',
    title: 'Hover tools',
    desc: 'Show nearest point or compare across traces on hover',
  },
]

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
.plot-tip {
  background-color: rgb(var(--v-theme-primary), 0.06);
  border-bottom: 1px solid rgba(var(--v-theme-primary), 0.15);
}

.plot-help :deep(.v-list-item) {
  min-height: 44px;
}

/*
 * Make the plot's axis drag regions visibly discoverable.
 *
 * Plotly renders invisible drag handles over the axis labels so users can
 * drag to rescale an axis. By default they blend in, so few users notice
 * them. We keep them transparent at rest (so they don't fight the axis
 * labels) but tint them on hover so the affordance is obvious when the
 * user's cursor is over a draggable region. The native browser cursor
 * (ns-resize, ew-resize, etc.) continues to come from Plotly.
 */
:deep(.js-plotly-plot .plotly) {
  .drag.cursor-ns-resize,
  .drag.cursor-n-resize,
  .drag.cursor-s-resize,
  .drag.cursor-w-resize,
  .drag.cursor-ew-resize,
  .drag.cursor-e-resize,
  .drag.cursor-sw-resize,
  .drag.cursor-nw-resize,
  .drag.cursor-ne-resize,
  .drag.cursor-se-resize {
    fill: transparent !important;
    stroke: transparent !important;
    transition: fill 120ms ease, stroke 120ms ease;
  }

  .drag.cursor-ns-resize:hover,
  .drag.cursor-n-resize:hover,
  .drag.cursor-s-resize:hover,
  .drag.cursor-w-resize:hover,
  .drag.cursor-ew-resize:hover,
  .drag.cursor-e-resize:hover {
    fill: rgba(var(--v-theme-primary), 0.12) !important;
    stroke: rgba(var(--v-theme-primary), 0.35) !important;
    stroke-width: 1px !important;
  }

  .drag.cursor-sw-resize:hover,
  .drag.cursor-nw-resize:hover,
  .drag.cursor-ne-resize:hover,
  .drag.cursor-se-resize:hover {
    fill: rgba(var(--v-theme-primary), 0.18) !important;
    stroke: rgba(var(--v-theme-primary), 0.45) !important;
    stroke-width: 1px !important;
  }
}

/* Give the modebar buttons a clearer hover state so icons feel clickable. */
:deep(.js-plotly-plot .modebar-btn:hover) {
  background-color: rgba(var(--v-theme-primary), 0.12) !important;
  border-radius: 4px;
}

:deep(.v-window__container) {
  height: 100%;
}
</style>
