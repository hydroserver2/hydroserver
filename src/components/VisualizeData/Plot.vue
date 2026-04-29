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

        <v-chip
          v-if="selectedData?.length || hasSelectionShape"
          class="plot-toolbar__selection"
          size="small"
          color="red"
          variant="tonal"
          prepend-icon="mdi-selection-drag"
          closable
          close-icon="mdi-close"
          @click:close="clearSelected()"
        >
          <b class="mr-1">{{ selectedData?.length ?? 0 }}</b>
          point{{ (selectedData?.length ?? 0) === 1 ? '' : 's' }} selected
        </v-chip>

        <v-spacer />

        <div
          v-if="tab === 'plot'"
          class="plot-toolbar__points-combo"
          :class="{
            'plot-toolbar__points-combo--on': areTooltipsEnabled,
            'plot-toolbar__points-combo--off': !areTooltipsEnabled,
            'plot-toolbar__points-combo--auto': tooltipsMode === 'auto',
          }"
        >
          <!-- Auto mode: show live counter in place of the toggle button -->
          <div
            v-if="tooltipsMode === 'auto'"
            class="plot-toolbar__points-cell plot-toolbar__points-cell--counter"
            aria-live="polite"
            :title="
              tooltipsAutoDisabled
                ? `Data points disabled — ${visiblePoints.toLocaleString()} visible, threshold ${tooltipsMaxDataPoints.toLocaleString()}`
                : `${visiblePoints.toLocaleString()} of ${tooltipsMaxDataPoints.toLocaleString()} threshold points visible`
            "
          >
            <span
              class="plot-toolbar__points-count"
              :class="{ 'plot-toolbar__points-count--over': tooltipsAutoDisabled }"
            >{{ visiblePoints.toLocaleString() }}</span>
            <span class="plot-toolbar__points-count-sep">/{{ tooltipsMaxDataPoints.toLocaleString() }}</span>
          </div>
          <!-- Manual mode: toggle button -->
          <button
            v-else
            type="button"
            data-testid="tooltips-toggle-btn"
            class="plot-toolbar__points-cell plot-toolbar__points-cell--toggle"
            :aria-label="`Data points: ${areTooltipsEnabled ? 'on' : 'off'} — click to toggle`"
            :aria-pressed="areTooltipsEnabled"
            @click="toggleTooltips"
          >
            <v-icon icon="mdi-chart-timeline-variant" size="18" />
          </button>

          <span class="plot-toolbar__points-divider" aria-hidden="true" />

          <v-menu
            v-model="modeMenuOpen"
            :close-on-content-click="false"
            location="bottom end"
            offset="6"
          >
            <template #activator="{ props: caretProps }">
              <button
                v-bind="caretProps"
                type="button"
                data-testid="tooltips-mode-btn"
                class="plot-toolbar__points-cell plot-toolbar__points-cell--caret"
                :aria-label="`Data points mode: ${tooltipsModeLabel}`"
              >
                <v-icon icon="mdi-menu-down" size="18" />
              </button>
            </template>
            <v-list
              density="compact"
              min-width="240"
              data-testid="tooltips-mode-menu"
            >
              <v-list-subheader
                class="text-uppercase text-caption font-weight-bold"
              >
                Data points
              </v-list-subheader>
              <v-list-item
                v-for="opt in tooltipsModeOptions"
                :key="opt.value"
                :data-testid="`tooltips-mode-${opt.value}`"
                :active="tooltipsMode === opt.value"
                @click="setTooltipsMode(opt.value)"
              >
                <template #prepend>
                  <v-icon
                    :icon="
                      tooltipsMode === opt.value
                        ? 'mdi-check-circle'
                        : 'mdi-circle-outline'
                    "
                    :color="tooltipsMode === opt.value ? 'primary' : 'grey'"
                    size="18"
                  />
                </template>
                <v-list-item-title class="text-body-2">
                  {{ opt.title }}
                </v-list-item-title>
                <v-list-item-subtitle class="text-caption">
                  {{ opt.subtitle }}
                </v-list-item-subtitle>
              </v-list-item>

              <!-- Threshold form — only shown when automatic is active -->
              <template v-if="tooltipsMode === 'auto'">
                <v-divider class="my-1" />
                <div class="px-3 pt-1 pb-3">
                  <div class="text-caption text-medium-emphasis mb-2">
                    Points stop rendering above this count — only the line remains.<br>Raise on fast machines, lower on slow ones.
                  </div>
                  <div class="d-flex align-center gap-2">
                    <v-text-field
                      v-model.number="pendingThreshold"
                      data-testid="threshold-input"
                      type="number"
                      min="100"
                      step="1000"
                      density="compact"
                      variant="outlined"
                      hide-details
                      single-line
                      suffix="pts"
                      class="flex-grow-1"
                      @keyup.enter="applyThreshold"
                    />
                    <v-btn
                      data-testid="threshold-apply-btn"
                      color="primary"
                      size="small"
                      variant="flat"
                      :disabled="!isPendingThresholdValid"
                      @click="applyThreshold"
                    >
                      Apply
                    </v-btn>
                  </div>
                </div>
              </template>
            </v-list>
          </v-menu>
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
            </v-list>
          </v-card>
        </v-menu>

        <v-select
          v-model="editorDateBtnId"
          :items="editorDateOptions"
          item-title="editorLabel"
          item-value="id"
          density="compact"
          variant="outlined"
          hide-details
          prepend-inner-icon="mdi-magnify-scan"
          title="Zoom to range (does not reload data)"
          class="plot-toolbar__range"
          style="max-width: 12rem"
          @update:model-value="(id: any) => onEditorDatePreset(id as number)"
        />
      </div>
    </div>

    <v-divider v-if="!preview"></v-divider>

    <div class="d-flex flex-row flex-grow-1">
      <v-tabs-window v-model="tab" class="flex-grow-1">
        <v-tabs-window-item value="plot" class="fill-height">
          <div class="plot-container fill-height">
            <div ref="plot" class="plot-main"></div>
            <template v-if="!preview">
              <div
                class="plot-context-strip"
                :title="contextPlotCollapsed ? 'Expand overview' : 'Collapse overview'"
                @click="contextPlotCollapsed = !contextPlotCollapsed"
              >
                <v-icon
                  size="12"
                  :icon="contextPlotCollapsed ? 'mdi-chevron-up' : 'mdi-chevron-down'"
                />
              </div>
              <ContextPlot v-show="!contextPlotCollapsed" />
            </template>
            <div
              v-for="chip in axisChips"
              :key="chip.id"
              :ref="(el) => registerChipRef(chip.id, el as Element | null)"
              class="plot-axis-chip"
              :class="{
                'plot-axis-chip--right': chipPlacements[chip.id] === 'right',
              }"
              :style="{
                '--chip-line': chip.lineX + 'px',
                '--chip-idx': chip.chipIdx,
                '--chip-color': chip.color,
              }"
              aria-hidden="true"
            >
              <span class="plot-axis-chip__text" :title="chip.title">
                {{ chip.title }}
              </span>
              <v-icon
                class="plot-axis-chip__tri"
                icon="mdi-triangle-small-down"
                size="18"
              />
            </div>
            <!-- Crosshair droplines. Two absolute-positioned CSS lines
                 driven by `processMouseMove` via the `crosshair` store
                 field. Replaces Plotly's `showspikes`, which (a) lags
                 the cursor noticeably on scattergl and (b) disappears
                 together with tooltips when visible points exceed
                 `tooltipsMaxDataPoints` because its render path is
                 gated on `hoverinfo !== 'skip'`. CSS driver stays
                 active regardless of tooltip state. -->
            <div
              v-show="crosshair.visible && tab === 'plot'"
              class="plot-crosshair plot-crosshair--v"
              :style="{
                left: crosshair.cursorX + 'px',
                top: crosshair.cursorY + 'px',
                height:
                  Math.max(0, crosshair.plotBottom - crosshair.cursorY) + 'px',
              }"
              aria-hidden="true"
            />
            <div
              v-show="crosshair.visible && tab === 'plot'"
              class="plot-crosshair plot-crosshair--h"
              :style="{
                left: crosshair.plotLeft + 'px',
                top: crosshair.cursorY + 'px',
                width:
                  Math.max(0, crosshair.cursorX - crosshair.plotLeft) + 'px',
              }"
              aria-hidden="true"
            />
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
import { computed, nextTick, ref, onMounted, onBeforeUnmount, watch } from 'vue'

import { usePlotlyStore } from '@/store/plotly'
import { storeToRefs } from 'pinia'
import Plotly from 'plotly.js-dist'
import {
  handleNewPlot,
  handleRelayout,
  zoomXaxisTo,
} from '@/utils/plotting/plotly'
import { subtractDays, subtractMonths, subtractYears } from '@/utils/dateMath'
import DataTable from '@/components/VisualizeData/DataTable.vue'
import ContextPlot from '@/components/VisualizeData/ContextPlot.vue'
import { useDataSelection } from '@/composables/useDataSelection'
import { useBufferedNumber } from '@/composables/useBufferedNumber'
import { usePersistedFlag } from '@/composables/useResizable'
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

const { setPlotSelection, clearSelected } = useDataSelection()
const { updateOptions } = usePlotlyStore()
const plot = ref<HTMLDivElement>()
const {
  isUpdating,
  areTooltipsEnabled,
  visiblePoints,
  tooltipsMaxDataPoints,
  tooltipsMode,
  tooltipsManualEnabled,
  hover,
  showCoordinates,
  crosshair,
  axisChips,
  previewMode,
  plotlyRef,
} = storeToRefs(usePlotlyStore())
const { selectedData, hasSelectionShape, qcDatastream, dateOptions, endDate } =
  storeToRefs(useDataVisStore())

const allPresetId = computed(
  () => dateOptions.value.find((o) => o.label === 'All')?.id ?? null
)
const editorDateBtnId = ref<number | null>(allPresetId.value)

/**
 * UI flags derived from `tooltipsMode` + the live point count.
 *
 * `tooltipsActive` mirrors `areTooltipsEnabled` from the store —
 * it's the actual rendered state. `tooltipsAutoDisabled` is only
 * meaningful in `auto` mode: it's the case where the threshold
 * suppressed an otherwise-on toggle. Manual modes ignore the
 * threshold so it's never "auto-disabled" there.
 */
const tooltipsAutoDisabled = computed(
  () =>
    tooltipsMode.value === 'auto' &&
    visiblePoints.value > tooltipsMaxDataPoints.value
)
const tooltipsActive = computed(() => areTooltipsEnabled.value)
const tooltipsModeOptions = [
  {
    value: 'manual',
    title: 'Manual toggle',
    subtitle: 'Click the icon to turn data points on or off',
  },
  {
    value: 'auto',
    title: 'Automatic',
    subtitle: 'Show until the visible-points threshold is reached',
  },
] as const
const tooltipsModeLabel = computed(
  () =>
    tooltipsModeOptions.find((o) => o.value === tooltipsMode.value)?.title ??
    'Automatic'
)
const modeMenuOpen = ref(false)
function setTooltipsMode(mode: 'manual' | 'auto') {
  tooltipsMode.value = mode
  if (mode === 'manual') modeMenuOpen.value = false
  handleRelayout(null)
}
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
 * Axis-chip placement. Each chip defaults to the left of its axis
 * line (the fit-always fallback — right edge anchored at `lineX`).
 * After render we measure the rendered chip and, if there's enough
 * room between the axis line and the plot's right edge, promote it
 * to right placement. The measurement doesn't depend on placement
 * (width is content-driven, capped by max-width), so toggling the
 * class never oscillates.
 */
const chipEls = new Map<string, HTMLElement>()
const chipPlacements = ref<Record<string, 'left' | 'right'>>({})
const CHIP_EDGE_BUFFER = 4

const registerChipRef = (id: string, el: Element | null) => {
  if (el instanceof HTMLElement) chipEls.set(id, el)
  else chipEls.delete(id)
}

const computeChipPlacements = () => {
  const next: Record<string, 'left' | 'right'> = {}
  for (const chip of axisChips.value) {
    const el = chipEls.get(chip.id)
    if (!el) {
      next[chip.id] = 'left'
      continue
    }
    const width = el.getBoundingClientRect().width
    const roomRight = chip.graphWidth - chip.lineX - CHIP_EDGE_BUFFER
    next[chip.id] = width > 0 && roomRight >= width ? 'right' : 'left'
  }
  chipPlacements.value = next
}

watch(
  axisChips,
  async () => {
    await nextTick()
    computeChipPlacements()
  },
  { immediate: true, deep: true }
)

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
 * Minimum/maximum x-value across every plotted trace. Used by the
 * editor presets to anchor to actual rendered data rather than the
 * requested fetch window.
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

const latestDataX = computed<number | null>(() => {
  let max = -Infinity
  for (const s of graphSeriesArray.value) {
    const xs = s.data?.dataX
    if (!xs?.length) continue
    const last = xs[xs.length - 1] as number
    if (last > max) max = last
  }
  return Number.isFinite(max) ? max : null
})

const EDITOR_LABELS: Record<string, string> = {
  '1w': 'Last week of data',
  '1m': 'Last month of data',
  '6m': 'Last 6 months of data',
  '1y': 'Last year of data',
  All: 'All data',
}

const editorDateOptions = computed(() =>
  dateOptions.value
    .filter((o) => o.label !== 'YTD')
    .map((o) => ({ ...o, editorLabel: EDITOR_LABELS[o.label] ?? o.label }))
)

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

  // Anchor relative presets to the actual last data point so "1w" always
  // lands on real data rather than today.
  const dataEndMs = latestDataX.value
  const dataEnd = dataEndMs != null ? new Date(dataEndMs) : null

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
    case 'All':
      if (earliestDataX.value == null || dataEndMs == null) return
      begin = new Date(earliestDataX.value)
      end = new Date(dataEndMs)
      break
    default:
      return
  }

  if (!begin || !end) return
  zoomXaxisTo(plotlyRef.value, begin.getTime(), end.getTime())
}

function toggleTooltips() {
  // Left half of the split button: a manual override. Forces manual
  // mode and flips the on/off state. Picking up "auto" again must go
  // through the dropdown so an inadvertent click doesn't drop the
  // user out of the threshold-driven behaviour they configured.
  tooltipsManualEnabled.value = !areTooltipsEnabled.value
  tooltipsMode.value = 'manual'
  handleRelayout(null)
}

const showHelp = ref(false)
const contextPlotCollapsed = usePersistedFlag('qc:contextPlotCollapsed', false)
const {
  pending: pendingThreshold,
  isValid: isPendingThresholdValid,
  apply: applyPendingThreshold,
} = useBufferedNumber(tooltipsMaxDataPoints, modeMenuOpen, { min: 100 })
const applyThreshold = () => {
  if (applyPendingThreshold()) {
    modeMenuOpen.value = false
    handleRelayout(null)
  }
}

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

let plotResizeObserver: ResizeObserver | null = null
let pendingResizeFrame: number | null = null

onMounted(async () => {
  // Flip the store's preview flag before `handleNewPlot` so
  // `createPlotlyOption` emits the preview-friendly layout (no qualifier
  // band, no built-in title, no select/lasso, tight margins).
  previewMode.value = !!props.preview
  updateOptions()

  // This timeout halts the execution of handleNewPlot until the view switching animation is complete, and the container has expanded.
  setTimeout(() => {
    updateOptions()
    handleNewPlot(plot.value)
    // In the editor, seed the toolbar's initial "All" preset by
    // running the same zoom handler a user click would trigger.
    // Done after `handleNewPlot` so the Plotly instance is ready
    // to receive the relayout. Skipped in preview mode because the
    // preset control isn't visible there.
    if (!props.preview && editorDateBtnId.value != null) {
      onEditorDatePreset(editorDateBtnId.value)
    }

    // Attach the container-size observer after the Plotly instance
    // is actually live. Observing earlier is wasted effort because
    // `Plotly.Plots.resize` no-ops on a gd element without an
    // attached layout.
    const target = plot.value
    if (target && typeof ResizeObserver !== 'undefined') {
      let initialFired = false
      plotResizeObserver = new ResizeObserver(() => {
        // The first callback is the synchronous "observe started"
        // notification with the current size — skip it so we don't
        // resize on top of the freshly-built plot.
        if (!initialFired) {
          initialFired = true
          return
        }
        if (pendingResizeFrame != null) return
        pendingResizeFrame = requestAnimationFrame(() => {
          pendingResizeFrame = null
          const gd = plot.value
          if (!gd) return
          // `Plotly.Plots.resize` throws if the gd isn't yet a
          // Plotly plot (no `_fullLayout`). Guard against the
          // race where the observer fires before `handleNewPlot`
          // has finished.
          const anyGd = gd as unknown as { _fullLayout?: unknown }
          if (!anyGd._fullLayout) return
          void Plotly.Plots.resize(gd as unknown as Plotly.Root)
        })
      })
      plotResizeObserver.observe(target)
    }
  }, 200)
})

onBeforeUnmount(() => {
  // Reset so a subsequent Plot mount in Edit view doesn't inherit preview.
  if (previewMode.value) previewMode.value = false
  if (pendingResizeFrame != null) {
    cancelAnimationFrame(pendingResizeFrame)
    pendingResizeFrame = null
  }
  if (plotResizeObserver) {
    plotResizeObserver.disconnect()
    plotResizeObserver = null
  }
})

const onTabChange = () => {
  if (tab.value === 'plot') {
    setTimeout(() => {
      setPlotSelection(selectedData.value || [])
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
  display: flex;
  flex-direction: column;
}

.plot-main {
  flex: 1 1 auto;
  min-height: 0;
}

/* Axis-title chips. `--chip-line`, `--chip-idx`, `--chip-color` are
   set per-chip on the element; everything else is static. Default
   (left) placement: right edge anchored to `lineX + 18px` via
   `translateX(-100%)` so the body extends leftward and can't overflow
   the right gutter — used when there isn't enough room to place the
   chip to the right of its axis without running past the plot's
   right edge. `.plot-axis-chip--right` flips to right placement
   when the overlay has measured a fit. */
.plot-axis-chip {
  position: absolute;
  left: calc(var(--chip-line) + 18px);
  top: calc(36px + var(--chip-idx) * 34px);
  color: var(--chip-color);
  transform: translateX(-100%);
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  pointer-events: none;
  z-index: 2;
  font-variant-numeric: tabular-nums;
}

.plot-axis-chip--right {
  left: calc(var(--chip-line) - 18px);
  transform: none;
  align-items: flex-start;
}

.plot-axis-chip__text {
  max-width: 200px;
  padding: 2px 8px;
  font-size: 0.8rem;
  font-weight: 600;
  line-height: 1.2;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  background-color: rgba(255, 255, 255, 0.92);
  border: 1px solid rgba(var(--v-theme-primary), 0.2);
  border-radius: 4px;
  color: inherit;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
  /* Re-enable pointer-events so the native `title` tooltip fires. */
  pointer-events: auto;
}

/* Apex lands on the axis line. For the default (left) placement
   the chip body sits 18 px right of `lineX` and is right-aligned,
   so we pull the icon back by that 18 px. For the right-placement
   variant the chip body starts 18 px left of `lineX` and is
   left-aligned, so the offset is mirrored. */
.plot-axis-chip__tri {
  margin-top: -7px;
  transform: translateX(calc(50% - 18px));
  color: inherit;
}

.plot-axis-chip--right .plot-axis-chip__tri {
  transform: translateX(calc(-50% + 18px));
}

/* CSS-based crosshair droplines. Two sibling divs inside
   `.plot-container`, positioned from the `crosshair` store state.
   Dotted 1px lines tinted just enough to read on white without
   competing with the plot's own tick grid. `pointer-events: none` so
   they never steal the mousemove that drives them. */
.plot-crosshair {
  position: absolute;
  pointer-events: none;
  z-index: 1;
}

.plot-crosshair--v {
  width: 0;
  border-left: 1px dotted rgba(60, 60, 60, 0.45);
}

.plot-crosshair--h {
  height: 0;
  border-top: 1px dotted rgba(60, 60, 60, 0.45);
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
  white-space: nowrap;
  font-size: 0.7rem;
  line-height: 1.1;
}

.plot-toolbar__tooltips-notice--over {
  color: rgba(var(--v-theme-on-surface), 0.65);
}

.plot-toolbar__tooltips-notice-text {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
}

.plot-toolbar__tooltips-notice-count {
  font-weight: 600;
}
.plot-toolbar__tooltips-notice-count--over {
  color: rgb(var(--v-theme-warning));
}

/* Inline pencil button that opens the threshold popover. Sized down
   so it fits inside the two-line notice without bumping the toolbar
   row height. */
.plot-toolbar__tooltips-notice-edit.v-btn {
  width: 18px;
  height: 18px;
  margin-left: 4px;
}
.plot-toolbar__tooltips-notice-edit.v-btn :deep(.v-icon) {
  font-size: 12px;
}

/* Tighten the icon-only tooltip toggle and help button so they sit
   closer to their neighbours. `density="compact"` on v-btn already
   trims ~8px of vertical padding; pairing it with a narrower min-width
   removes the extra horizontal slack Vuetify keeps around icon buttons. */
.plot-toolbar__icon-btn.v-btn {
  min-width: 28px;
  padding-inline: 4px;
}

/* Combobox-style data-points control. The wrapper owns the chrome
   (background, border, rounding) so the two cells inside read as one
   control rather than two stacked icon buttons. */
.plot-toolbar__points-combo {
  display: inline-flex;
  align-items: stretch;
  height: 28px;
  border-radius: 8px;
  border: 1px solid transparent;
  transition:
    background-color 120ms ease,
    border-color 120ms ease;
}
.plot-toolbar__points-combo--on {
  background-color: rgba(var(--v-theme-primary), 0.12);
  border-color: rgba(var(--v-theme-primary), 0.22);
  color: rgb(var(--v-theme-primary));
}
.plot-toolbar__points-combo--off {
  background-color: transparent;
  border-color: rgba(var(--v-theme-on-surface), 0.16);
  color: rgba(var(--v-theme-on-surface), 0.6);
}

.plot-toolbar__points-cell {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  padding: 0;
  cursor: pointer;
  color: inherit;
  transition: background-color 120ms ease;
}
.plot-toolbar__points-cell:focus-visible {
  outline: 2px solid rgb(var(--v-theme-primary));
  outline-offset: -2px;
}
.plot-toolbar__points-cell--toggle {
  width: 30px;
  border-top-left-radius: 7px;
  border-bottom-left-radius: 7px;
}

.plot-toolbar__points-cell--counter {
  padding: 0 8px;
  border-top-left-radius: 7px;
  border-bottom-left-radius: 7px;
  cursor: default;
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-size: 0.7rem;
  line-height: 1;
  white-space: nowrap;
}

.plot-toolbar__points-count {
  font-weight: 600;
}

.plot-toolbar__points-count--over {
  color: rgb(var(--v-theme-warning));
}

.plot-toolbar__points-count-sep {
  opacity: 0.6;
}
.plot-toolbar__points-cell--caret {
  width: 22px;
  border-top-right-radius: 7px;
  border-bottom-right-radius: 7px;
}
.plot-toolbar__points-cell:not(:disabled):hover {
  background-color: rgba(var(--v-theme-on-surface), 0.06);
}
.plot-toolbar__points-combo--on
  .plot-toolbar__points-cell:not(:disabled):hover {
  background-color: rgba(var(--v-theme-primary), 0.18);
}
.plot-toolbar__points-cell:disabled {
  cursor: default;
  opacity: 0.5;
}

/* Hairline divider between the two cells. Picks up the wrapper's
   border colour so it reads as a continuation of the chrome. */
.plot-toolbar__points-divider {
  width: 1px;
  align-self: stretch;
  background-color: rgba(var(--v-theme-on-surface), 0.16);
}
.plot-toolbar__points-combo--on .plot-toolbar__points-divider {
  background-color: rgba(var(--v-theme-primary), 0.22);
}

.plot-help :deep(.v-list-item) {
  min-height: 44px;
}

.plot-context-strip {
  flex: 0 0 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  border-top: 1px solid rgba(var(--v-theme-on-surface), 0.12);
  background-color: rgba(var(--v-theme-on-surface), 0.02);
  color: rgba(var(--v-theme-on-surface), 0.35);
  user-select: none;
  transition:
    background-color 120ms ease,
    color 120ms ease;
}

.plot-context-strip:hover {
  background-color: rgba(var(--v-theme-primary), 0.06);
  color: rgb(var(--v-theme-primary));
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
