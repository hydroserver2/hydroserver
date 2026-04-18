<template>
  <div class="plot-root d-flex flex-column">
    <!-- Two-line plot header:
         • Row 1 — the plot title (the QC datastream name) with a quiet
           loading indicator to its right.
         • Row 2 — controls: view switch, selection chip, date range,
           tooltips toggle, help menu.
         Splitting the title onto its own line gives it the prominence
         it deserves and keeps the controls row at a predictable
         height regardless of title length. -->
    <div v-if="!preview" class="plot-header">
      <div class="plot-header__title-row px-3 py-1 d-flex align-center gap-2">
        <v-icon
          icon="mdi-chart-line"
          color="primary"
          size="18"
          class="flex-shrink-0"
        />
        <div
          class="plot-header__title text-subtitle-2 font-weight-bold text-truncate flex-grow-1"
          :title="qcDatastream?.name"
        >
          {{ qcDatastream?.name ?? 'Data preview' }}
        </div>
        <v-progress-circular
          v-if="isUpdating"
          color="primary"
          size="16"
          width="2"
          indeterminate
        />
      </div>

      <v-divider />

      <div class="plot-toolbar d-flex align-center flex-wrap gap-2 px-3 py-1">
        <!-- Plot ↔ Table segmented control. -->
        <v-btn-toggle
          v-model="tab"
          density="compact"
          color="primary"
          variant="flat"
          mandatory
          rounded="lg"
          class="plot-toolbar__tabs"
          @update:model-value="onTabChange"
        >
          <v-btn value="plot" size="small" prepend-icon="mdi-chart-line">
            Plot
          </v-btn>
          <v-btn value="table" size="small" prepend-icon="mdi-table">
            Table
          </v-btn>
        </v-btn-toggle>

        <!-- Active selection indicator. Doubles as a shortcut to clear
             the selection. Hidden when nothing is selected. -->
        <v-chip
          v-if="selectedData?.length"
          class="plot-toolbar__selection"
          size="small"
          color="red"
          variant="tonal"
          prepend-icon="mdi-checkbox-marked-circle"
          closable
          close-icon="mdi-close"
          @click:close="clearSelected()"
        >
          <b class="mr-1">{{ selectedData.length }}</b>
          point{{ selectedData.length === 1 ? '' : 's' }} selected
        </v-chip>

        <v-spacer />

        <v-btn-toggle
          v-model="selectedDateBtnId"
          density="compact"
          color="primary"
          variant="outlined"
          mandatory
          class="plot-toolbar__range"
          @update:model-value="(id: any) => onDateBtnClick(id as number)"
        >
          <v-btn
            v-for="opt in dateOptions"
            :key="opt.id"
            :value="opt.id"
            size="small"
            :title="(opt as any).title ?? opt.label"
          >
            {{ opt.label }}
          </v-btn>
        </v-btn-toggle>

        <v-tooltip
          v-if="tab === 'plot'"
          location="bottom"
          :text="
            visiblePoints > tooltipsMaxDataPoints
              ? 'Too many points visible — tooltips disabled'
              : areTooltipsEnabled
                ? 'Tooltips on'
                : 'Tooltips off'
          "
        >
          <template #activator="{ props: tp }">
            <v-btn
              v-bind="tp"
              size="small"
              variant="text"
              :disabled="visiblePoints > tooltipsMaxDataPoints"
              :icon="areTooltipsEnabled ? 'mdi-tooltip' : 'mdi-tooltip-outline'"
              :color="areTooltipsEnabled ? 'primary' : undefined"
              @click="toggleTooltips"
            />
          </template>
        </v-tooltip>

        <v-menu
          v-model="showHelp"
          v-if="tab === 'plot'"
          :close-on-content-click="false"
          location="bottom end"
          offset="6"
        >
          <template v-slot:activator="{ props: menuProps }">
            <v-btn
              v-bind="menuProps"
              variant="text"
              size="small"
              icon="mdi-help-circle-outline"
              title="Plot controls"
              aria-label="Plot controls"
            />
          </template>

          <v-card max-width="360" class="plot-help">
            <v-card-title class="text-subtitle-1 d-flex align-center gap-2">
              <v-icon icon="mdi-gesture-tap" size="20" />
              Plot controls
            </v-card-title>
            <v-divider />
            <v-list density="compact" class="py-1" lines="two">
              <v-list-subheader
                class="text-uppercase text-caption font-weight-bold"
              >
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

              <v-list-subheader
                class="text-uppercase text-caption font-weight-bold"
              >
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

    <v-divider v-if="!preview"></v-divider>

    <div class="d-flex flex-row flex-grow-1">
      <v-tabs-window v-model="tab" class="flex-grow-1">
        <v-tabs-window-item value="plot" class="fill-height">
          <div class="plot-container fill-height">
            <div ref="plot" class="fill-height"></div>
            <!-- Floating hover-coordinates chip, anchored inside the
                 plot area. Absolute positioning means it appears and
                 disappears without touching the toolbar layout. -->
            <div
              v-show="showCoordinates && tab === 'plot'"
              class="plot-coords"
              aria-live="polite"
            >
              <span class="mr-2">
                <b>x</b> {{ formatDate(new Date(hover.x)) }}
              </span>
              <span> <b>y</b> {{ hover.y }} </span>
            </div>
          </div>
        </v-tabs-window-item>

        <v-tabs-window-item value="table" class="fill-height">
          <!-- Important to NOT keep the DataTable component in memory if the tab is not shown -->
          <DataTable v-if="tab === 'table' && !preview" class="fill-height"
        /></v-tabs-window-item>
      </v-tabs-window>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue'

import { usePlotlyStore } from '@/store/plotly'
import { storeToRefs } from 'pinia'
import { handleNewPlot, handleRelayout } from '@/utils/plotting/plotly'
import DataTable from '@/components/VisualizeData/DataTable.vue'
import { useDataSelection } from '@/composables/useDataSelection'
import { formatDate } from '@uwrl/qc-utils'
import { useDataVisStore } from '@/store/dataVisualization'

/**
 * `preview` strips the in-plot chrome (tooltip toggle, plot-controls help
 * menu, Plot/Table tab rail) for the Select view, where the plot is shown
 * purely as a data preview and editing affordances aren't relevant yet.
 */
const props = defineProps<{
  preview?: boolean
}>()

const { dispatchSelection, clearSelected } = useDataSelection()
const { updateOptions } = usePlotlyStore()
const dataVisStore = useDataVisStore()
const plot = ref<HTMLDivElement>()
const {
  isUpdating,
  areTooltipsEnabled,
  visiblePoints,
  tooltipsMaxDataPoints,
  hover,
  showCoordinates,
  previewMode,
} = storeToRefs(usePlotlyStore())
const { selectedData, qcDatastream, dateOptions, selectedDateBtnId } =
  storeToRefs(useDataVisStore())
const { onDateBtnClick } = dataVisStore
const tab = ref('plot')

function toggleTooltips() {
  areTooltipsEnabled.value = !areTooltipsEnabled.value
  handleRelayout(null)
}

const showHelp = ref(false)

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
  // Flip the store's preview flag before `handleNewPlot` so
  // `createPlotlyOption` emits the preview-friendly layout (no qualifier
  // band, no built-in title, no select/lasso, tight margins).
  previewMode.value = !!props.preview
  updateOptions()

  // This timeout halts the execution of handleNewPlot until the view switching animation is complete, and the container has expanded.
  setTimeout(() => {
    handleNewPlot(plot.value)
  }, 200)
})

onBeforeUnmount(() => {
  // Reset so a subsequent Plot mount in Edit view doesn't inherit preview.
  if (previewMode.value) previewMode.value = false
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
.plot-root {
  min-height: 0;
}

.plot-header {
  display: flex;
  flex-direction: column;
}

.plot-header__title-row {
  background-color: rgba(var(--v-theme-primary), 0.12);
  border-bottom: 1px solid rgba(var(--v-theme-primary), 0.18);
  min-height: 36px;
}

.plot-header__title {
  min-width: 0;
  letter-spacing: 0;
  color: rgb(var(--v-theme-on-surface));
}

.plot-toolbar {
  background-color: rgba(var(--v-theme-primary), 0.02);
  min-height: 40px;
}

.plot-toolbar__tabs {
  flex: 0 0 auto;
  background-color: rgba(var(--v-theme-on-surface), 0.06);
  border-radius: 8px;
  padding: 2px;
}

.plot-toolbar__tabs :deep(.v-btn) {
  min-width: 72px;
  letter-spacing: 0;
  text-transform: none;
  font-weight: 500;
  border: none !important;
}

/* Inactive segment renders as a subtle button on the muted backdrop;
   the active segment gets Vuetify's colour="primary" treatment already. */
.plot-toolbar__tabs :deep(.v-btn:not(.v-btn--active)) {
  color: rgba(var(--v-theme-on-surface), 0.65);
  background-color: transparent !important;
}

.plot-toolbar__tabs :deep(.v-btn:not(.v-btn--active):hover) {
  background-color: rgba(var(--v-theme-on-surface), 0.06) !important;
  color: rgb(var(--v-theme-on-surface));
}

.plot-toolbar__title {
  flex: 1 1 auto;
  min-width: 0;
}

.plot-toolbar__selection {
  flex: 0 0 auto;
  font-variant-numeric: tabular-nums;
}

.plot-toolbar__range :deep(.v-btn) {
  min-width: 32px !important;
  padding: 0 8px !important;
  font-size: 0.75rem;
  letter-spacing: 0;
}

/* Floating hover-coordinates chip overlaid on the plot. Absolute
   positioning keeps it out of the toolbar layout so showing/hiding it
   as the cursor enters and leaves the chart never shifts the range or
   help controls. Pointer-events off so it doesn't steal hover from the
   chart beneath it. */
.plot-container {
  position: relative;
}

.plot-coords {
  position: absolute;
  top: 8px;
  left: 12px;
  padding: 3px 8px;
  font-size: 0.75rem;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
  background-color: rgba(255, 255, 255, 0.92);
  border: 1px solid rgba(var(--v-theme-primary), 0.2);
  border-radius: 4px;
  color: rgba(var(--v-theme-on-surface), 0.75);
  pointer-events: none;
  z-index: 2;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
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
    transition:
      fill 120ms ease,
      stroke 120ms ease;
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
