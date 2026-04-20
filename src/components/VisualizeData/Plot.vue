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
      <div class="plot-toolbar d-flex align-center flex-wrap gap-1 px-3 py-1">
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

        <v-progress-circular
          v-if="isUpdating"
          color="primary"
          size="16"
          width="2"
          indeterminate
          class="ml-1"
        />

        <!-- Active selection indicator. Doubles as a shortcut to clear
             the selection. Hidden when nothing is selected. -->
        <v-chip
          v-if="selectedData?.length"
          class="plot-toolbar__selection"
          size="small"
          color="red"
          variant="tonal"
          prepend-icon="mdi-selection-drag"
          closable
          close-icon="mdi-close"
          @click:close="clearSelected()"
        >
          <b class="mr-1">{{ selectedData.length }}</b>
          point{{ selectedData.length === 1 ? '' : 's' }} selected
        </v-chip>

        <v-spacer />

        <!-- Right group reads right-to-left: date range (rightmost),
             help menu, tooltip toggle, and finally the conditional
             tooltips-hidden notice to the left of the toggle so it
             explains the toggle's disabled/off state inline. -->

        <v-btn
          v-if="tab === 'plot'"
          size="small"
          variant="text"
          density="compact"
          class="plot-toolbar__icon-btn"
          :disabled="visiblePoints > tooltipsMaxDataPoints"
          :icon="areTooltipsEnabled ? 'mdi-tooltip' : 'mdi-tooltip-outline'"
          :color="areTooltipsEnabled ? 'primary' : undefined"
          @click="toggleTooltips"
        />

        <div
          v-if="tab === 'plot' && !tooltipsActive && tooltipsAutoDisabled"
          class="plot-toolbar__tooltips-notice d-inline-flex align-center"
          aria-live="polite"
          :title="
            tooltipsAutoDisabled
              ? 'Tooltips disabled while more points are visible than the performance threshold.'
              : 'Tooltips are turned off. Toggle them back on with the button to the right.'
          "
        >
          <div class="plot-toolbar__tooltips-notice-text">
            <template v-if="tooltipsAutoDisabled">
              <div>Tooltips hidden</div>
              <div>zoom in to re-enable</div>
            </template>
          </div>
        </div>

        <v-btn
          v-if="tab === 'plot'"
          size="small"
          variant="text"
          density="compact"
          class="plot-toolbar__icon-btn"
          icon="mdi-share-variant-outline"
          title="Copy shareable link"
          aria-label="Copy shareable link"
          @click="copyShareableLink"
        />

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
              density="compact"
              class="plot-toolbar__icon-btn"
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

              <v-divider class="my-1" />

              <v-list-subheader
                class="text-uppercase text-caption font-weight-bold"
              >
                Preferences
              </v-list-subheader>
              <v-list-item class="px-4">
                <v-list-item-title class="text-body-2 font-weight-medium mb-1">
                  Tooltip point limit
                </v-list-item-title>
                <v-list-item-subtitle class="text-caption mb-2">
                  Tooltips auto-disable when more than this many points are
                  visible. Raise on fast machines, lower on slow ones.
                </v-list-item-subtitle>
                <v-text-field
                  v-model.number="tooltipsMaxDataPoints"
                  type="number"
                  min="100"
                  step="1000"
                  density="compact"
                  variant="outlined"
                  hide-details
                  single-line
                  suffix="points"
                />
              </v-list-item>
            </v-list>
          </v-card>
        </v-menu>

        <v-btn-toggle
          v-model="selectedDateBtnId"
          density="compact"
          color="primary"
          variant="outlined"
          mandatory
          class="plot-toolbar__range"
          @update:model-value="(id: any) => onEditorDatePreset(id as number)"
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
              <span>
                <b>{{ yReadoutLabel }}</b> {{ hover.y }}{{ yReadoutUnit }}
              </span>
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
import { computed, ref, onMounted, onBeforeUnmount } from 'vue'

import { usePlotlyStore } from '@/store/plotly'
import { storeToRefs } from 'pinia'
import {
  handleNewPlot,
  handleRelayout,
  zoomXaxisTo,
} from '@/utils/plotting/plotly'
import { subtractDays, subtractMonths, subtractYears } from '@/utils/dateMath'
import DataTable from '@/components/VisualizeData/DataTable.vue'
import { useDataSelection } from '@/composables/useDataSelection'
import { formatDate, Snackbar } from '@uwrl/qc-utils'
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
const plot = ref<HTMLDivElement>()
const {
  isUpdating,
  areTooltipsEnabled,
  visiblePoints,
  tooltipsMaxDataPoints,
  hover,
  showCoordinates,
  previewMode,
  plotlyRef,
} = storeToRefs(usePlotlyStore())
const { selectedData, qcDatastream, dateOptions, selectedDateBtnId, endDate } =
  storeToRefs(useDataVisStore())

/**
 * Mirrors the logic in `handleRelayout` that decides whether Plotly's
 * `hoverinfo` gets set to `'skip'`: tooltips are hidden when the user
 * toggled them off, or when the visible point count exceeds the perf
 * threshold. The overlay notice in the template uses these to decide
 * whether to show and which copy to show.
 */
const tooltipsAutoDisabled = computed(
  () => visiblePoints.value > tooltipsMaxDataPoints.value
)
const tooltipsActive = computed(
  () => areTooltipsEnabled.value && !tooltipsAutoDisabled.value
)
const tab = ref('plot')

// The floating hover readout shows y in the QC trace's native coord
// space (handleMouseMove converts via the primary yaxis `p2c`). Label
// and unit come from the QC datastream so users don't have to infer
// "what series is this and in what units" — especially important when
// other traces live on their own right-side axes.
const yReadoutLabel = computed(() => {
  const name = qcDatastream.value?.observedProperty?.name
  return name ? name : 'y'
})
const yReadoutUnit = computed(() => {
  const symbol = qcDatastream.value?.unit?.symbol
  return symbol ? ` ${symbol}` : ''
})

const { graphSeriesArray } = storeToRefs(usePlotlyStore())

/**
 * Copy the current page URL to the clipboard. `VisualizeData.vue` keeps
 * the URL query string in sync with plotted datastreams, QC selection,
 * date range, and sidebar filters, so the address bar is already a
 * shareable representation of plot state.
 */
async function copyShareableLink() {
  const url = window.location.href
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(url)
    } else {
      // Legacy fallback for browsers without the Clipboard API.
      const ta = document.createElement('textarea')
      ta.value = url
      ta.setAttribute('readonly', '')
      ta.style.position = 'fixed'
      ta.style.opacity = '0'
      document.body.appendChild(ta)
      ta.select()
      document.execCommand('copy')
      document.body.removeChild(ta)
    }
    Snackbar.success('Shareable link copied to clipboard')
  } catch (err) {
    console.error('Failed to copy link', err)
    Snackbar.error('Could not copy link — copy the address bar manually')
  }
}

/**
 * Minimum x-value across every plotted trace. Used by the "All"
 * preset to zoom out to the actual rendered data extent rather than
 * trusting the store's `beginDate`, which is the *requested* window
 * start and can precede the earliest returned observation.
 */
const earliestDataX = computed<number | null>(() => {
  let min = Infinity
  for (const s of graphSeriesArray.value) {
    const xs = s.data?.dataX
    if (!xs?.length) continue
    const first = xs[0] as number
    if (first < min) min = first
  }
  return Number.isFinite(min) ? min : null
})

/**
 * Editor-mode date presets are a visual x-axis zoom, not a data
 * refetch. The Select-view sidebar's sibling buttons drive
 * `useDataVisStore#onDateBtnClick`, which changes `beginDate` /
 * `endDate` and reloads observations — appropriate when the user is
 * picking a working window before they start editing. Once editing
 * begins, refetching would blow away pending edits and the history
 * stack; we just zoom the already-loaded window instead.
 *
 * Relative presets (1w / 1m / 6m / 1y) anchor to the loaded data's
 * end so they always land on real data. YTD is the exception: it
 * means "current calendar year so far" regardless of where the data
 * sits. "All" snaps to the actual data extent.
 */
function onEditorDatePreset(id: number) {
  const option = dateOptions.value.find((o) => o.id === id)
  if (!option) return
  selectedDateBtnId.value = id

  const dataEnd = endDate.value
  let begin: Date | null = null
  let end: Date | null = null

  switch (option.label) {
    case '1w':
      if (!dataEnd) return
      end = dataEnd
      begin = subtractDays(dataEnd, 7)
      break
    case '1m':
      if (!dataEnd) return
      end = dataEnd
      begin = subtractMonths(dataEnd, 1)
      break
    case '6m':
      if (!dataEnd) return
      end = dataEnd
      begin = subtractMonths(dataEnd, 6)
      break
    case '1y':
      if (!dataEnd) return
      end = dataEnd
      begin = subtractYears(dataEnd, 1)
      break
    case 'YTD': {
      const now = new Date()
      end = now
      begin = new Date(now.getFullYear(), 0, 1)
      break
    }
    case 'All':
      if (!dataEnd || earliestDataX.value == null) return
      end = dataEnd
      begin = new Date(earliestDataX.value)
      break
    default:
      return
  }

  if (!begin || !end) return
  zoomXaxisTo(plotlyRef.value, begin.getTime(), end.getTime())
}

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
    title: 'Reset view',
    desc: 'Return to the default zoom. Does not change the begin/end dates in the sidebar.',
  },
  {
    icon: 'mdi-arrow-collapse-horizontal',
    title: 'Fit X to visible',
    desc: 'Fit the X axis to currently visible data',
  },
  {
    icon: 'mdi-arrow-collapse-vertical',
    title: 'Fit Y to visible',
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


/* Inline notice in the plot toolbar, sits to the left of the tooltip
   toggle. Subtle so it doesn't compete with the primary controls. The
   two-line variant stacks its copy so the toolbar stays the same
   height as a single-line row. */
.plot-toolbar__tooltips-notice {
  color: rgba(var(--v-theme-on-surface), 0.65);
  white-space: nowrap;
  font-size: 0.7rem;
  line-height: 1.1;
}

.plot-toolbar__tooltips-notice-text {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
}

/* Tighten the icon-only tooltip toggle and help button so they sit
   closer to their neighbours. `density="compact"` on v-btn already
   trims ~8px of vertical padding; pairing it with a narrower min-width
   removes the extra horizontal slack Vuetify keeps around icon buttons. */
.plot-toolbar__icon-btn.v-btn {
  min-width: 28px;
  padding-inline: 4px;
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

/*
 * Plotly drives the select/lasso cursor through a dynamically injected
 * `.cursor-crosshair { cursor: crosshair }` rule. On this app the
 * `crosshair` keyword renders as no cursor at all in Chromium — the
 * same is true of any element we apply it to, so it's a platform-level
 * quirk with the keyword (reproducible under cross-origin-isolated
 * contexts, which this app is because of the SharedArrayBuffer-gated
 * COEP/COOP headers in vite.config.ts). Supplying an inline SVG cursor
 * sidesteps the keyword lookup entirely; `crosshair` stays as a
 * fallback for browsers that don't honour the URL form.
 */
:deep(.js-plotly-plot .plotly .cursor-crosshair),
:deep(.js-plotly-plot .plotly .cursor-crosshair *) {
  cursor:
    url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='24' height='24' viewBox='0 0 24 24'><path d='M12 1v22M1 12h22' stroke='white' stroke-width='3' stroke-linecap='round'/><path d='M12 1v22M1 12h22' stroke='black' stroke-width='1' stroke-linecap='round'/></svg>")
      12 12,
    crosshair !important;
}

/* Give the modebar buttons a clearer hover state so icons feel clickable. */
:deep(.js-plotly-plot .modebar-btn:hover) {
  background-color: rgba(var(--v-theme-primary), 0.12) !important;
  border-radius: 4px;
}

/* Wider gap between modebar functional groups. Plotly's default
   inter-group spacing is ~5px and easy to miss; bumping it keeps the
   grouping legible without adding a divider line. */
:deep(.js-plotly-plot .modebar-group) {
  margin-right: 12px !important;
}
:deep(.js-plotly-plot .modebar-group:last-child) {
  margin-right: 0 !important;
}

:deep(.v-window__container) {
  height: 100%;
}
</style>
