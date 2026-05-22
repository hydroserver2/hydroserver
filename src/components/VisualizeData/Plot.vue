<template>
  <div class="plot-root d-flex flex-column">
    <div v-if="!preview" class="plot-header">
      <div class="plot-toolbar d-flex align-center flex-wrap ga-1 px-3 py-1">
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
          class="plot-toolbar__selection flex-grow-0 flex-shrink-0"
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
          class="plot-toolbar__points-combo d-inline-flex align-stretch rounded-lg"
          :class="{
            'plot-toolbar__points-combo--on': areTooltipsEnabled,
            'plot-toolbar__points-combo--off': !areTooltipsEnabled,
          }"
        >
          <div
            v-if="tooltipsMode === 'auto'"
            data-testid="tooltips-counter"
            class="plot-toolbar__points-cell plot-toolbar__points-cell--counter d-inline-flex align-center justify-center"
            aria-live="polite"
            :title="
              tooltipsAutoDisabled
                ? `Data points disabled: ${visiblePoints.toLocaleString()} visible, threshold ${tooltipsMaxDataPoints.toLocaleString()}`
                : `${visiblePoints.toLocaleString()} of ${tooltipsMaxDataPoints.toLocaleString()} threshold points visible`
            "
          >
            <span
              class="plot-toolbar__points-count"
              :class="{
                'plot-toolbar__points-count--over': tooltipsAutoDisabled,
              }"
              >{{ visiblePoints.toLocaleString() }}</span
            >
            <span class="plot-toolbar__points-count-sep"
              >/{{ tooltipsMaxDataPoints.toLocaleString() }}</span
            >
          </div>
          <button
            v-else
            type="button"
            data-testid="tooltips-toggle-btn"
            class="plot-toolbar__points-cell plot-toolbar__points-cell--toggle d-inline-flex align-center justify-center cursor-pointer"
            :aria-label="`Data points: ${areTooltipsEnabled ? 'on' : 'off'} (click to toggle)`"
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
                class="plot-toolbar__points-cell plot-toolbar__points-cell--caret d-inline-flex align-center justify-center cursor-pointer"
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
                class="text-uppercase text-body-small font-weight-bold"
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
                <v-list-item-title class="text-body-medium">
                  {{ opt.title }}
                </v-list-item-title>
                <v-list-item-subtitle class="text-body-small">
                  {{ opt.subtitle }}
                </v-list-item-subtitle>
              </v-list-item>

              <template v-if="tooltipsMode === 'auto'">
                <v-divider class="my-1" />
                <div class="px-3 pt-1 pb-3">
                  <div class="text-body-small text-medium-emphasis mb-2">
                    Points stop rendering above this count; only the line
                    remains.<br />Raise on fast machines, lower on slow ones.
                  </div>
                  <div class="d-flex align-center ga-2">
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
              icon="mdi-help-circle-outline"
              title="Plot controls"
              aria-label="Plot controls"
            />
          </template>

          <v-card max-width="360" class="plot-help">
            <v-card-title class="text-title-medium d-flex align-center ga-2">
              Plot tips
            </v-card-title>
            <v-divider />
            <v-list density="compact" class="py-1" lines="two">
              <v-list-subheader
                class="text-uppercase text-body-small font-weight-bold"
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
                <v-list-item-title class="text-body-medium font-weight-medium">
                  {{ g.title }}
                </v-list-item-title>
                <v-list-item-subtitle class="text-body-small">
                  {{ g.desc }}
                </v-list-item-subtitle>
              </v-list-item>

              <v-divider class="my-1" />

              <v-list-subheader
                class="text-uppercase text-body-small font-weight-bold"
              >
                Keyboard
              </v-list-subheader>
              <v-list-item
                v-for="(k, i) in keyboardShortcuts"
                :key="`k-${i}`"
                class="px-4"
              >
                <template v-slot:prepend>
                  <v-icon :icon="k.icon" size="18" class="mr-2" />
                </template>
                <v-list-item-title class="text-body-medium font-weight-medium">
                  {{ k.title }}
                </v-list-item-title>
                <v-list-item-subtitle class="text-body-small">
                  <kbd class="plot-help__kbd">{{ k.keys }}</kbd>
                  {{ k.desc }}
                </v-list-item-subtitle>
              </v-list-item>
            </v-list>
          </v-card>
        </v-menu>

        <v-speed-dial
          v-model="rangeDialOpen"
          location="bottom center"
          transition="fade-transition"
        >
          <template #activator="{ props: activatorProps }">
            <v-btn
              v-bind="activatorProps"
              size="small"
              variant="text"
              icon="mdi-magnify-scan"
              title="Zoom to range (does not reload data)"
              aria-label="Zoom to range"
            />
          </template>

          <v-btn
            v-for="option in editorDateOptions"
            :key="option.id"
            color="surface"
            variant="flat"
            size="small"
            :title="option.editorLabel"
            class="text-none text-body-small font-weight-medium border elevation-2"
            @click="selectRangePreset(option.id)"
          >
            {{ option.label }}
          </v-btn>
        </v-speed-dial>
      </div>
    </div>

    <v-divider v-if="!preview"></v-divider>

    <div class="d-flex flex-row flex-grow-1">
      <v-tabs-window v-model="tab" class="flex-grow-1">
        <v-tabs-window-item value="plot" class="fill-height">
          <div class="fill-height position-relative d-flex flex-column">
            <div ref="plot" class="flex-fill" style="min-height: 0"></div>
            <template v-if="!preview">
              <div
                class="plot-context-strip d-flex align-center justify-center cursor-pointer user-select-none"
                :title="
                  contextPlotCollapsed ? 'Expand overview' : 'Collapse overview'
                "
                @click="contextPlotCollapsed = !contextPlotCollapsed"
              >
                <v-icon
                  size="12"
                  :icon="
                    contextPlotCollapsed ? 'mdi-chevron-up' : 'mdi-chevron-down'
                  "
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
            <!-- CSS crosshair, driven by the `crosshair` store. Plotly's
                 showspikes lags on scattergl and disappears when tooltips
                 are off. -->
            <div
              v-show="crosshair.visible && tab === 'plot'"
              class="plot-crosshair plot-crosshair--v position-absolute pointer-events-none"
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
              class="plot-crosshair plot-crosshair--h position-absolute pointer-events-none"
              :style="{
                left: crosshair.plotLeft + 'px',
                top: crosshair.cursorY + 'px',
                width:
                  Math.max(0, crosshair.cursorX - crosshair.plotLeft) + 'px',
              }"
              aria-hidden="true"
            />
            <div
              v-show="showCoordinates && tab === 'plot'"
              class="plot-coords position-absolute pointer-events-none"
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
          <!-- Don't keep DataTable mounted when not on the table tab. -->
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

// Preview strips the in-plot chrome for the Select view.
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
  activeTab,
} = storeToRefs(usePlotlyStore())
const { selectedData, hasSelectionShape, qcDatastream, dateOptions } =
  storeToRefs(useDataVisStore())

const allPresetId = computed(
  () => dateOptions.value.find((o) => o.label === 'All')?.id ?? null
)

const tooltipsAutoDisabled = computed(
  () =>
    tooltipsMode.value === 'auto' &&
    visiblePoints.value > tooltipsMaxDataPoints.value
)
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
// Stored on the plotly store so the share URL picks it up.
const tab = computed({
  get: () => activeTab.value,
  set: (v: string) => {
    activeTab.value = v === 'table' ? 'table' : 'plot'
  },
})

// Label/unit come from the QC datastream so the readout is unambiguous
// when other traces live on right-side axes.
const yReadoutLabel = computed(() => {
  // Wire response enriches observedProperty/unit even though the
  // published Datastream type only carries their ids.
  const ds = qcDatastream.value as
    | (typeof qcDatastream.value & {
        observedProperty?: { name?: string }
        unit?: { symbol?: string }
      })
    | null
  const name = ds?.observedProperty?.name
  return name ? name : 'y'
})
const yReadoutUnit = computed(() => {
  const ds = qcDatastream.value as
    | (typeof qcDatastream.value & {
        observedProperty?: { name?: string }
        unit?: { symbol?: string }
      })
    | null
  const symbol = ds?.unit?.symbol
  return symbol ? ` ${symbol}` : ''
})

const { graphSeriesArray } = storeToRefs(usePlotlyStore())

// Default left placement; promote to right when the measured chip
// fits between the axis line and the plot's right edge.
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

async function copyShareableLink() {
  const url = window.location.href
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(url)
    } else {
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
    Snackbar.error('Could not copy link; copy the address bar manually')
  }
}

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

const rangeDialOpen = ref(false)

function selectRangePreset(id: number) {
  onEditorDatePreset(id)
  rangeDialOpen.value = false
}

// Editor presets are a pure x-axis zoom (no refetch) so they don't
// blow away the edit history. Relative presets (1w/1m/6m/1y) anchor
// to the loaded data's end. "All" snaps to the data extent.
function onEditorDatePreset(id: number) {
  const option = dateOptions.value.find((o) => o.id === id)
  if (!option) return

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
  // Manual override; switching back to auto must go through the
  // dropdown so a stray click doesn't drop the user out of the
  // threshold-driven behaviour they configured.
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
    title: 'Click a point to toggle it',
    desc: 'Adds or removes a single point from the selection without affecting the rest.',
  },
  {
    icon: 'mdi-mouse',
    title: 'Scroll to zoom time',
    desc: 'Wheel up zooms in on the cursor, wheel down zooms out. Y axes stay put.',
  },
  {
    icon: 'mdi-arrow-expand-vertical',
    title: 'Rescale one axis',
    desc: 'Drag near either end of an axis to stretch it',
  },
  {
    icon: 'mdi-arrow-up-down',
    title: 'Pan one axis',
    desc: 'Drag the middle of an axis to translate only that axis.',
  },
  {
    icon: 'mdi-chart-areaspline',
    title: 'Use the overview strip',
    desc: 'Drag the band on the bottom mini-plot to set the visible time window.',
  },
  {
    icon: 'mdi-cursor-move',
    title: 'Crosshair on hover',
    desc: 'Lines up the cursor across X and Y axes, even when tooltips are off.',
  },
]

const keyboardShortcuts = [
  {
    icon: 'mdi-undo-variant',
    title: 'Undo',
    keys: 'Ctrl+Z',
    desc: 'Reverts the last filter or edit.',
  },
  {
    icon: 'mdi-redo-variant',
    title: 'Redo',
    keys: 'Ctrl+Y',
    desc: 'Re-applies the last undone step (Ctrl+Shift+Z also works).',
  },
]

let plotResizeObserver: ResizeObserver | null = null
let pendingResizeFrame: number | null = null

onMounted(async () => {
  // Flip before handleNewPlot so createPlotlyOption emits the
  // preview layout (no qualifier band, no title, tight margins).
  previewMode.value = !!props.preview
  updateOptions()

  // Wait for the view-switch animation to expand the container.
  setTimeout(() => {
    updateOptions()
    handleNewPlot(plot.value)
    if (!props.preview && allPresetId.value != null) {
      onEditorDatePreset(allPresetId.value)
    }

    const target = plot.value
    if (target && typeof ResizeObserver !== 'undefined') {
      // Skip the initial "observe started" notification so we don't
      // resize on top of the freshly-built plot.
      let initialFired = false
      plotResizeObserver = new ResizeObserver(() => {
        if (!initialFired) {
          initialFired = true
          return
        }
        if (pendingResizeFrame != null) return
        pendingResizeFrame = requestAnimationFrame(() => {
          pendingResizeFrame = null
          const gd = plot.value
          if (!gd) return
          // Plotly.Plots.resize throws when gd has no _fullLayout
          // (observer can fire before handleNewPlot finishes).
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
  // Reset so the next Plot mount in Edit view doesn't inherit preview.
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

.plot-toolbar__tabs :deep(.v-btn:not(.v-btn--active)) {
  color: rgba(var(--v-theme-on-surface), 0.65);
  background-color: transparent !important;
}

.plot-toolbar__tabs :deep(.v-btn:not(.v-btn--active):hover) {
  background-color: rgba(var(--v-theme-on-surface), 0.06) !important;
  color: rgb(var(--v-theme-on-surface));
}

.plot-toolbar__selection {
  font-variant-numeric: tabular-nums;
}

/* Axis-title chips. CSS vars set per-element on the chip. Default
   left placement; .plot-axis-chip--right flips after measuring. */
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
  /* Re-enable so the native title tooltip fires. */
  pointer-events: auto;
}

.plot-axis-chip__tri {
  margin-top: -7px;
  transform: translateX(calc(50% - 18px));
  color: inherit;
}

.plot-axis-chip--right .plot-axis-chip__tri {
  transform: translateX(calc(-50% + 18px));
}

.plot-crosshair {
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
  z-index: 2;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
}

/* Combobox-style data-points control. Wrapper owns the chrome
   so the two cells read as one control. */
.plot-toolbar__points-combo {
  height: 28px;
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
  background: transparent;
  border: none;
  padding: 0;
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

/* Allow the menu subtitle to wrap (Vuetify default is nowrap). */
.plot-help :deep(.v-card-subtitle) {
  white-space: normal;
  overflow: visible;
  text-overflow: clip;
  line-height: 1.4;
}

.plot-help__kbd {
  display: inline-block;
  padding: 0 4px;
  margin-right: 6px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 0.7rem;
  line-height: 1.4;
  border: 1px solid rgba(var(--v-theme-on-surface), 0.18);
  border-radius: 3px;
  background-color: rgba(var(--v-theme-on-surface), 0.04);
}

.plot-context-strip {
  flex-basis: 14px;
  border-top: 1px solid rgba(var(--v-theme-on-surface), 0.12);
  background-color: rgba(var(--v-theme-on-surface), 0.02);
  color: rgba(var(--v-theme-on-surface), 0.35);
  transition:
    background-color 120ms ease,
    color 120ms ease;
}

.plot-context-strip:hover {
  background-color: rgba(var(--v-theme-primary), 0.06);
  color: rgb(var(--v-theme-primary));
}

/* Tint Plotly's invisible axis drag handles on hover so the affordance
   is discoverable. */
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

/* The crosshair keyword renders as no cursor at all under our
   cross-origin-isolated context (Chromium quirk with COOP/COEP).
   Inline SVG cursor sidesteps the keyword lookup. */
:deep(.js-plotly-plot .plotly .cursor-crosshair),
:deep(.js-plotly-plot .plotly .cursor-crosshair *) {
  cursor:
    url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='24' height='24' viewBox='0 0 24 24'><path d='M12 1v22M1 12h22' stroke='white' stroke-width='3' stroke-linecap='round'/><path d='M12 1v22M1 12h22' stroke='black' stroke-width='1' stroke-linecap='round'/></svg>")
      12 12,
    crosshair !important;
}

:deep(.js-plotly-plot .modebar-btn:hover) {
  background-color: rgba(var(--v-theme-primary), 0.12) !important;
  border-radius: 4px;
}

/* Wider gap between modebar groups (Plotly default ~5px). */
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
