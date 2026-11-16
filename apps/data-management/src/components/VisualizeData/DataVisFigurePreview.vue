<template>
  <v-dialog
    v-model="open"
    fullscreen
    :persistent="exporting"
    transition="dialog-bottom-transition"
    aria-label="Download plot image"
  >
    <div class="figure-preview">
      <header class="figure-header">
        <h1 class="hs-subheading">Download plot image</h1>
        <div class="figure-actions">
          <v-btn variant="text" :disabled="exporting" @click="resetFigure"
            >Reset image</v-btn
          >
          <v-btn-dialog-action
            :prepend-icon="mdiDownload"
            :loading="exporting"
            :disabled="
              !ready || !dimensionsValid || !exportValid || !textSizeValid
            "
            @click="download"
            >Download PNG</v-btn-dialog-action
          >
          <v-btn-icon
            :icon="mdiClose"
            aria-label="Close image preview"
            :disabled="exporting"
            @click="open = false"
          />
        </div>
      </header>
      <div class="figure-body">
        <aside
          class="figure-editor"
          aria-label="Image settings"
          :inert="exporting"
        >
          <section class="figure-settings-section">
            <h2 class="hs-subheading">Image</h2>
            <v-btn-toggle
              v-model="exportMode"
              mandatory
              divided
              color="primary"
              variant="outlined"
              rounded="md"
              class="figure-export-mode"
              role="group"
              aria-label="Export destination"
            >
              <v-btn
                value="screen"
                :prepend-icon="mdiMonitor"
                :aria-pressed="exportMode === 'screen'"
                >Screen</v-btn
              >
              <v-btn
                value="print"
                :prepend-icon="mdiPrinter"
                :aria-pressed="exportMode === 'print'"
                >Print</v-btn
              >
            </v-btn-toggle>
            <v-textarea
              v-model="settings.title"
              label="Image title"
              rows="2"
              auto-grow
              hide-details
            />
            <v-select
              v-if="exportMode === 'screen'"
              v-model="imageShape"
              label="Image shape"
              :items="shapes"
              hide-details
            />
            <v-select
              v-else
              v-model="printPreset"
              label="Print size"
              :items="printSizes"
              hide-details
            />
            <div v-if="exportMode === 'screen'" class="figure-dimensions">
              <v-text-field
                v-model.number="settings.width"
                @update:model-value="imageShape = 0"
                label="Width"
                type="number"
                suffix="px"
                :min="MIN_IMAGE_WIDTH"
                :max="maxLayoutDimension"
                step="1"
                :rules="[(value) => dimensionRule(value, MIN_IMAGE_WIDTH)]"
                hide-details="auto"
              />
              <v-text-field
                v-model.number="settings.height"
                @update:model-value="imageShape = 0"
                label="Height"
                type="number"
                suffix="px"
                :min="MIN_IMAGE_HEIGHT"
                :max="maxLayoutDimension"
                step="1"
                :rules="[(value) => dimensionRule(value, MIN_IMAGE_HEIGHT)]"
                hide-details="auto"
              />
            </div>
            <template v-else>
              <div class="figure-dimensions">
                <v-text-field
                  v-model.number="printWidth"
                  label="Print width"
                  type="number"
                  :suffix="printUnit"
                  min="0.5"
                  step="0.5"
                  :rules="[(value) => printDimensionRule(value, 'width')]"
                  hide-details="auto"
                />
                <v-text-field
                  v-model.number="printHeight"
                  label="Print height"
                  type="number"
                  :suffix="printUnit"
                  min="0.5"
                  step="0.5"
                  :rules="[(value) => printDimensionRule(value, 'height')]"
                  hide-details="auto"
                />
              </div>
              <v-select
                v-model="printUnit"
                label="Units"
                :items="[
                  { title: 'Inches', value: 'in' },
                  { title: 'cm', value: 'cm' },
                ]"
                hide-details
              />
              <v-select
                v-model="printQuality"
                label="Print quality"
                :items="printQualities"
                hint="Available quality levels depend on image size."
                persistent-hint
                hide-details="auto"
              />
              <v-text-field
                v-if="printQuality === 'custom'"
                v-model.number="customDpi"
                label="Custom DPI"
                type="number"
                min="72"
                :max="maxPrintDpi"
                step="1"
                :error-messages="customDpiError"
                hide-details="auto"
              />
            </template>
            <v-select
              v-if="exportMode === 'screen'"
              v-model="screenScale"
              label="Resolution"
              :items="screenResolutions"
              hide-details
            />
            <div
              v-if="!customDpiError"
              class="figure-export-summary hs-text-sm"
              aria-live="polite"
              aria-atomic="true"
            >
              <template v-if="dimensionsValid && exportValid">
                <span class="hs-font-data"
                  >{{ exportSize.width }} × {{ exportSize.height }} px</span
                >
                <span
                  v-if="exportMode === 'print'"
                  class="text-medium-emphasis"
                >
                  {{ formatSize(printWidth) }} × {{ formatSize(printHeight) }}
                  {{ printUnit }} · {{ printDpi }} DPI
                </span>
              </template>
              <span v-else class="text-error" role="alert">
                {{ exportError || 'Enter valid image dimensions.' }}
              </span>
            </div>
            <v-text-field
              v-model.number="textSize"
              label="Text size"
              type="number"
              :min="1"
              step="1"
              suffix="px"
              :rules="[textSizeRule]"
              hide-details="auto"
              data-testid="figure-text-size"
            />
          </section>
          <section class="figure-settings-section">
            <h2 class="hs-subheading">Legend</h2>
            <v-checkbox
              v-model="settings.showLegend"
              label="Show legend"
              hide-details
            />
            <v-checkbox
              v-if="settings.showLegend"
              v-model="settings.showSiteNames"
              label="Show site names"
              hide-details
            />
            <v-select
              v-if="settings.showLegend"
              v-model="settings.legendPosition"
              label="Legend position"
              :items="[
                { title: 'Above plot', value: 'above' },
                { title: 'Below plot', value: 'below' },
              ]"
              hide-details
            />
          </section>
          <section class="figure-settings-section">
            <h2 class="hs-subheading">Traces</h2>
            <div
              v-for="(trace, index) in settings.traces"
              :key="trace.id"
              class="figure-trace-fields"
              role="group"
              :aria-label="`Trace ${index + 1} settings`"
            >
              <h3 class="hs-title figure-trace-heading">
                <span
                  class="figure-trace-marker"
                  :style="{ backgroundColor: trace.color }"
                  aria-hidden="true"
                />
                Trace {{ index + 1 }}
              </h3>
              <div
                class="figure-trace-colors"
                role="group"
                :aria-label="`Trace ${index + 1} color`"
              >
                <span class="hs-title">Color</span>
                <v-menu :close-on-content-click="false" location="bottom start">
                  <template #activator="{ props: menuProps }">
                    <v-btn
                      v-bind="menuProps"
                      class="figure-color-trigger"
                      variant="outlined"
                      size="small"
                      :aria-label="`Choose color for trace ${index + 1}`"
                    >
                      <span
                        class="figure-current-color"
                        :style="{ backgroundColor: trace.color }"
                      />
                      <span class="hs-font-data">{{ trace.color }}</span>
                    </v-btn>
                  </template>
                  <v-card
                    class="figure-color-popup"
                    role="group"
                    @keydown.tab.stop
                    :aria-label="`Trace ${index + 1} color picker`"
                  >
                    <div class="figure-color-palette">
                      <v-btn-icon
                        v-for="swatch in palette"
                        :key="swatch.color"
                        :color="swatch.color"
                        :style="{ backgroundColor: swatch.color }"
                        variant="flat"
                        size="x-small"
                        class="figure-color-swatch"
                        :class="{
                          'figure-color-swatch--selected':
                            trace.color.toLowerCase() ===
                            swatch.color.toLowerCase(),
                        }"
                        :aria-label="`Use ${swatch.name} for trace ${index + 1}`"
                        :aria-pressed="
                          trace.color.toLowerCase() ===
                          swatch.color.toLowerCase()
                        "
                        :title="swatch.name"
                        @click="trace.color = swatch.color"
                      />
                    </div>
                    <v-color-picker
                      v-model="trace.color"
                      mode="hex"
                      :modes="['hex']"
                      width="100%"
                    />
                  </v-card>
                </v-menu>
                <v-btn
                  variant="text"
                  size="small"
                  @click="resetTraceColor(trace.id)"
                  >Reset color</v-btn
                >
              </div>
              <v-textarea
                v-model="trace.name"
                :label="`Trace ${index + 1} name`"
                rows="2"
                auto-grow
                hide-details
              />
              <v-textarea
                v-if="settings.showLegend && settings.showSiteNames"
                v-model="trace.siteName"
                :label="`Trace ${index + 1} site name`"
                rows="2"
                auto-grow
                hide-details
              />
            </div>
          </section>
          <section class="figure-settings-section">
            <h2 class="hs-subheading">Axes</h2>
            <v-textarea
              v-for="axis in settings.axes"
              :key="axis.key"
              v-model="axis.label"
              :label="axisCaption(axis.key)"
              rows="2"
              auto-grow
              hide-details
            />
          </section>
        </aside>
        <main ref="stage" class="figure-stage" aria-label="Image canvas">
          <div
            v-if="figure"
            class="figure-frame"
            :style="{
              width: `${figure.layout.width * scale}px`,
              height: `${figure.layout.height * scale}px`,
            }"
          >
            <div
              class="figure-paper"
              :style="{
                width: `${figure.layout.width}px`,
                height: `${figure.layout.height}px`,
                transform: `scale(${scale})`,
              }"
            >
              <div ref="plotContainer" data-testid="figure-plot" />
            </div>
          </div>
        </main>
      </div>
    </div>
  </v-dialog>
</template>

<script setup lang="ts">
import {
  computed,
  nextTick,
  onBeforeUnmount,
  ref,
  shallowRef,
  watch,
} from 'vue'
import { storeToRefs } from 'pinia'
import { cloneDeep } from 'lodash-es'
import { mdiClose, mdiDownload, mdiMonitor, mdiPrinter } from '@mdi/js'
import { useDataVisStore } from '@/store/dataVisualization'
import {
  downloadPlotlyImage,
  type PlotlyOptions,
} from '@/utils/plotting/plotly'
import {
  buildFigurePreview,
  DEFAULT_IMAGE_WIDTH,
  DEFAULT_IMAGE_HEIGHT,
  MIN_IMAGE_WIDTH,
  MIN_IMAGE_HEIGHT,
  type FigureSettings,
} from '@/utils/plotting/figurePreview'
import { Snackbar } from '@/utils/notifications'
import { PlotlyColors } from '@/utils/materialColors'
import { getFigureExportSize } from '@/utils/plotting/imageExport'
import {
  DEFAULT_EXPORT_LIMITS,
  detectImageExportLimits,
  getMaxPrintDpi,
  supportsImageExport,
} from '@/utils/plotting/imageExportLimits'

const props = defineProps<{ getPlot: () => any }>()
const colorNames = [
  'blue',
  'orange',
  'green',
  'red',
  'purple',
  'brown',
  'pink',
  'gray',
  'yellow-green',
  'teal',
]
const palette = PlotlyColors.map((color, index) => ({
  color,
  name: colorNames[index],
}))
const { plotLabelItems } = storeToRefs(useDataVisStore())
const open = ref(false)
const exporting = ref(false)
const ready = ref(false)
const source = shallowRef<PlotlyOptions | null>(null)
const defaults = shallowRef<FigureSettings | null>(null)
const settings = ref<FigureSettings>({
  title: '',
  showLegend: true,
  showSiteNames: true,
  legendPosition: 'below',
  fontSize: 24,
  width: DEFAULT_IMAGE_WIDTH,
  height: DEFAULT_IMAGE_HEIGHT,
  traces: [],
  axes: [],
})
const textSize = ref<number | string>(settings.value.fontSize)
function textSizeRule(value: unknown) {
  return (
    (Number.isFinite(Number(value)) && Number(value) >= 1) ||
    'Enter a text size of at least 1 px.'
  )
}
const textSizeValid = computed(() => textSizeRule(textSize.value) === true)
watch(textSize, (value) => {
  if (textSizeRule(value) === true) settings.value.fontSize = Number(value)
})
const shapes = [
  { title: 'Landscape (4:3)', value: 4 / 3 },
  { title: 'Widescreen (16:9)', value: 16 / 9 },
  { title: 'Square (1:1)', value: 1 },
  { title: 'Portrait (3:4)', value: 3 / 4 },
  { title: 'Custom', value: 0 },
]
const printPresets = [
  { title: '3.5 × 2.5 in', value: '3.5x2.5', width: 3.5, height: 2.5 },
  { title: '7 × 3.5 in', value: '7x3.5', width: 7, height: 3.5 },
  { title: '6 × 4 in', value: '6x4', width: 6, height: 4 },
  { title: '4 × 6 in', value: '4x6', width: 4, height: 6 },
  { title: '5 × 5 in', value: '5x5', width: 5, height: 5 },
  { title: '7 × 5 in', value: '7x5', width: 7, height: 5 },
  { title: '5 × 7 in', value: '5x7', width: 5, height: 7 },
  { title: '8 × 10 in', value: '8x10', width: 8, height: 10 },
  { title: '8.5 × 11 in', value: '8.5x11', width: 8.5, height: 11 },
] as const
const qualityPresets = [
  { title: 'Draft · 150 DPI', value: 150 },
  { title: 'Standard · 300 DPI', value: 300 },
  { title: 'Mixed artwork · 500 DPI', value: 500 },
  { title: 'Fine detail · 600 DPI', value: 600 },
  { title: 'Line art · 1000 DPI', value: 1000 },
  { title: 'Fine line art · 1200 DPI', value: 1200 },
]
const exportLimits = shallowRef({ ...DEFAULT_EXPORT_LIMITS })
// Keep the interactive layout bounded independently of the final PNG dimensions.
const maxLayoutDimension = computed(() =>
  Math.min(
    exportLimits.value.maxWidth,
    exportLimits.value.maxHeight,
    exportLimits.value.maxGlDimension
  )
)
const stage = ref<HTMLElement | null>(null)
const plotContainer = ref<HTMLElement | null>(null)
const stageSize = ref({ width: 800, height: 600 })
const fontFamily = ref('Arial, sans-serif')
const fontVersion = ref(0)
const context = document.createElement('canvas').getContext('2d')
function dimensionRule(value: unknown, min: number) {
  const number = Number(value)
  return (
    (Number.isInteger(number) &&
      number >= min &&
      number <= maxLayoutDimension.value) ||
    `${min}–${maxLayoutDimension.value} px, whole numbers`
  )
}
const dimensionsValid = computed(
  () =>
    dimensionRule(settings.value.width, MIN_IMAGE_WIDTH) === true &&
    dimensionRule(settings.value.height, MIN_IMAGE_HEIGHT) === true
)
const exportMode = ref<'screen' | 'print'>('screen')
const screenScale = ref(1)
const printUnit = ref<'in' | 'cm'>('in')
const printWidthInches = ref(6)
const printHeightInches = ref(4.5)
const selectedPrintPreset = ref('custom')
const printSizeInitialized = ref(false)
const printQuality = ref<number | 'custom'>(300)
const customDpi = ref(300)
const printDpi = computed(() =>
  Number(printQuality.value === 'custom' ? customDpi.value : printQuality.value)
)
const maxPrintDpi = computed(() =>
  getMaxPrintDpi(
    printWidthInches.value,
    printHeightInches.value,
    exportLimits.value
  )
)
watch(printQuality, (quality) => {
  if (quality !== 'custom' || maxPrintDpi.value < 72) return
  if (
    !Number.isInteger(customDpi.value) ||
    customDpi.value < 72 ||
    customDpi.value > maxPrintDpi.value
  )
    customDpi.value = Math.min(300, maxPrintDpi.value)
})
const printSizes = computed(() => [
  ...printPresets
    .filter(
      (preset) =>
        supportsImageExport(
          Math.round(preset.width * printDpi.value),
          Math.round(preset.height * printDpi.value),
          exportLimits.value
        ) || preset.value === selectedPrintPreset.value
    )
    .map(({ title, value, width, height }) => ({
      title,
      value,
      props: {
        disabled: !supportsImageExport(
          Math.round(width * printDpi.value),
          Math.round(height * printDpi.value),
          exportLimits.value
        ),
      },
    })),
  { title: 'Custom', value: 'custom' },
])
const printQualities = computed(() => [
  ...qualityPresets
    .filter(
      ({ value }) => value <= maxPrintDpi.value || value === printQuality.value
    )
    .map((item) => ({
      ...item,
      props: { disabled: item.value > maxPrintDpi.value },
    })),
  {
    title: 'Custom DPI',
    value: 'custom',
    props: { disabled: maxPrintDpi.value < 72 },
  },
])
const screenResolutions = computed(() =>
  [
    { title: 'Standard · 1×', value: 1 },
    { title: 'High · 2×', value: 2 },
    { title: 'Very high · 4×', value: 4 },
  ]
    .filter(
      ({ value }) =>
        supportsImageExport(
          Math.floor(Number(settings.value.width) * value),
          Math.floor(Number(settings.value.height) * value),
          exportLimits.value
        ) || value === screenScale.value
    )
    .map((item) => ({
      ...item,
      props: {
        disabled: !supportsImageExport(
          Math.floor(Number(settings.value.width) * item.value),
          Math.floor(Number(settings.value.height) * item.value),
          exportLimits.value
        ),
      },
    }))
)
const printWidth = computed({
  get: () =>
    Number.isFinite(printWidthInches.value)
      ? Number(
          (
            printWidthInches.value * (printUnit.value === 'cm' ? 2.54 : 1)
          ).toFixed(3)
        )
      : '',
  set: (value: number | string) => {
    printWidthInches.value =
      value === '' ? NaN : Number(value) / (printUnit.value === 'cm' ? 2.54 : 1)
    selectedPrintPreset.value = 'custom'
  },
})
const printHeight = computed({
  get: () =>
    Number.isFinite(printHeightInches.value)
      ? Number(
          (
            printHeightInches.value * (printUnit.value === 'cm' ? 2.54 : 1)
          ).toFixed(3)
        )
      : '',
  set: (value: number | string) => {
    printHeightInches.value =
      value === '' ? NaN : Number(value) / (printUnit.value === 'cm' ? 2.54 : 1)
    selectedPrintPreset.value = 'custom'
  },
})
const exportSize = computed(() => {
  const size = getFigureExportSize(
    Number(settings.value.width),
    Number(settings.value.height),
    exportMode.value === 'print'
      ? {
          mode: 'print',
          widthInches: printWidthInches.value,
          heightInches: printHeightInches.value,
          dpi: printDpi.value,
        }
      : { mode: 'screen', scale: screenScale.value }
  )
  if (exportMode.value !== 'print' || !(size.width > 0 && size.height > 0))
    return size
  // Fit tall and wide print layouts within the preview's rendering limits.
  // Plotly requires at least 10 logical pixels in each dimension.
  const ratio = size.width / size.height
  const layoutWidth = Math.min(
    maxLayoutDimension.value,
    maxLayoutDimension.value * ratio,
    Math.max(10 * ratio, Number(settings.value.width))
  )
  return { ...size, scale: size.width / layoutWidth }
})
function printDimensionRule(value: unknown, dimension: 'width' | 'height') {
  return (
    (Number.isFinite(Number(value)) && Number(value) > 0) ||
    `Enter a ${dimension} greater than zero.`
  )
}
function dpiRule(value: unknown) {
  const dpi = Number(value)
  if (!Number.isInteger(dpi) || dpi < 72)
    return 'Enter a whole-number DPI of at least 72.'
  if (dpi > maxPrintDpi.value)
    return (
      'This DPI exceeds your browser’s export limits for this print size. ' +
      (maxPrintDpi.value >= 72
        ? `Use ${maxPrintDpi.value} DPI or less.`
        : 'Reduce the print width or height.')
    )
  return true
}
const customDpiError = computed(() => {
  if (exportMode.value !== 'print' || printQuality.value !== 'custom') return ''
  const error = dpiRule(printDpi.value)
  return error === true ? '' : error
})
const exportError = computed(() => {
  if (exportMode.value === 'print') {
    const widthError = printDimensionRule(printWidth.value, 'width')
    if (widthError !== true) return widthError
    const heightError = printDimensionRule(printHeight.value, 'height')
    if (heightError !== true) return heightError
    const dpiError = dpiRule(printDpi.value)
    if (dpiError !== true) return dpiError
  }
  const { width, height } = exportSize.value
  if (!supportsImageExport(width, height, exportLimits.value))
    return 'Reduce image size or resolution to fit this browser’s export limit.'
  if (
    exportMode.value === 'print' &&
    Math.min(width, height) / exportSize.value.scale < 10
  )
    return 'Choose print dimensions with a less extreme aspect ratio.'
  return ''
})
const exportValid = computed(() => !exportError.value)
const formatSize = (value: number | string) =>
  Number(Number(value).toFixed(2)).toLocaleString()
const selectedShape = ref(4 / 3)
const imageShape = computed({
  get: () => selectedShape.value,
  set: (ratio: number) => {
    selectedShape.value = ratio
    if (ratio <= 0) return
    settings.value.width = Math.min(
      DEFAULT_IMAGE_WIDTH,
      maxLayoutDimension.value
    )
    settings.value.height = Math.round(settings.value.width / ratio)
  },
})
const printPreset = computed({
  get: () => selectedPrintPreset.value,
  set: (value: string) => {
    const preset = printPresets.find((preset) => preset.value === value)
    selectedPrintPreset.value = preset?.value ?? 'custom'
    if (!preset) return
    printWidthInches.value = preset.width
    printHeightInches.value = preset.height
  },
})
watch(exportMode, (mode) => {
  if (mode !== 'print' || printSizeInitialized.value) return
  // Start with the screen figure's proportions; retain print edits on later visits.
  printHeightInches.value =
    (printWidthInches.value * settings.value.height) / settings.value.width
  selectedPrintPreset.value =
    printPresets.find(
      (preset) =>
        Math.abs(preset.width - printWidthInches.value) < 0.001 &&
        Math.abs(preset.height - printHeightInches.value) < 0.001
    )?.value ?? 'custom'
  printSizeInitialized.value = true
})
const figure = computed<ReturnType<typeof buildFigurePreview> | null>(
  (previous) => {
    if (!source.value) return null
    if (!dimensionsValid.value || !exportValid.value || !textSizeValid.value)
      return previous ?? null
    void fontVersion.value
    if (context)
      context.font = `${settings.value.fontSize}px ${fontFamily.value}`
    const preview = buildFigurePreview(
      source.value,
      exportMode.value === 'print'
        ? {
            ...settings.value,
            // Reflow the chart to the print aspect ratio rather than stretching it.
            width: exportSize.value.width / exportSize.value.scale,
            height: exportSize.value.height / exportSize.value.scale,
          }
        : settings.value,
      fontFamily.value,
      (text) =>
        context?.measureText(text).width ??
        Array.from(text).length * settings.value.fontSize * 0.65
    )
    return {
      ...preview,
      config: {
        ...preview.config,
        // WebGL traces need denser backing pixels as well as a larger PNG.
        plotGlPixelRatio: exportValid.value
          ? Math.max(
              1,
              Math.min(
                4,
                Math.max(2, exportSize.value.scale),
                exportLimits.value.maxGlDimension /
                  Math.max(preview.layout.width, preview.layout.height)
              )
            )
          : 2,
      },
    }
  }
)
const scale = computed(() =>
  Math.min(
    1,
    stageSize.value.width / (figure.value?.layout.width || DEFAULT_IMAGE_WIDTH),
    stageSize.value.height / (figure.value?.layout.height || 900)
  )
)

function axisCaption(key: string) {
  const match = key.match(/^([xy])axis(\d*)$/)
  return `${match?.[1].toUpperCase()}-axis${match?.[2] ? ` ${match[2]}` : ''} label`
}

function openPreview() {
  const gd = props.getPlot()
  if (!gd?.data || !gd?.layout) return
  exportLimits.value = detectImageExportLimits()
  const layout = cloneDeep(gd.layout)
  const axes = Object.keys(layout).filter((key) => /^[xy]axis\d*$/.test(key))
  for (const key of axes) {
    const liveAxis = gd._fullLayout?.[key]
    if (liveAxis?.range) {
      layout[key].range = [...liveAxis.range]
      layout[key].autorange = false
    }
  }
  source.value = {
    traces: cloneDeep(gd.data),
    layout,
    config: {},
    xRange: null,
  }
  defaults.value = {
    title: '',
    showLegend: true,
    showSiteNames: true,
    legendPosition: 'below',
    fontSize: 24,
    width: DEFAULT_IMAGE_WIDTH,
    height: DEFAULT_IMAGE_HEIGHT,
    traces: gd.data.map((trace: any, index: number) => {
      const item = plotLabelItems.value.find((item) => item.id === trace.id)
      const color = trace.line?.color ?? trace.marker?.color
      return {
        id: trace.id,
        name: item?.name ?? trace.name.replace(/<br>/g, '\n'),
        siteName: item?.siteName ?? '',
        color:
          typeof color === 'string' && /^#[\da-f]{6}$/i.test(color)
            ? color
            : PlotlyColors[index % PlotlyColors.length],
      }
    }),
    axes: axes.map((key) => ({
      key,
      label: (layout[key].title?.text ?? '').replace(/<br>/g, '\n'),
    })),
  }
  resetFigure()
  fontFamily.value =
    getComputedStyle(document.documentElement)
      .getPropertyValue('--hs-font-body')
      .trim() || 'Arial, sans-serif'
  void document.fonts?.ready.then(() => fontVersion.value++)
  open.value = true
}

function resetFigure() {
  if (defaults.value) {
    settings.value = cloneDeep(defaults.value)
    textSize.value = settings.value.fontSize
    selectedShape.value = 4 / 3
    exportMode.value = 'screen'
    screenScale.value = 1
    printWidthInches.value = 6
    printHeightInches.value = 4.5
    selectedPrintPreset.value = 'custom'
    printSizeInitialized.value = false
    printUnit.value = 'in'
    printQuality.value = 300
    customDpi.value = 300
  }
}

function resetTraceColor(id: string) {
  const trace = settings.value.traces.find((trace) => trace.id === id)
  const original = defaults.value?.traces.find((trace) => trace.id === id)
  if (trace && original) trace.color = original.color
}

let plotly: any
let chart: HTMLElement | null = null
let renderChain = Promise.resolve()
let renderRequest = 0
async function ensurePlotly() {
  if (!plotly) {
    const module = await import('plotly.js-dist')
    plotly = (module as any).default ?? module
  }
  return plotly
}

function renderFigure() {
  const request = ++renderRequest
  ready.value = false
  renderChain = renderChain
    .then(async () => {
      if (
        request !== renderRequest ||
        !open.value ||
        !figure.value ||
        !plotContainer.value
      )
        return
      const api = await ensurePlotly()
      if (!open.value || !plotContainer.value || !figure.value) return
      const { traces, layout, config } = figure.value
      chart = plotContainer.value
      await api.react(chart, traces, layout, config)
      if (request === renderRequest) ready.value = true
    })
    .catch((error) => {
      console.error('Unable to render image preview', error)
      Snackbar.error('Unable to render the image. Please try again.')
    })
  return renderChain
}
watch([figure, plotContainer], renderFigure, { flush: 'post' })

let observer: ResizeObserver | undefined
watch(stage, (element) => {
  observer?.disconnect()
  if (!element) return
  observer = new ResizeObserver(([entry]) => {
    stageSize.value = {
      width: Math.max(1, entry.contentRect.width),
      height: Math.max(1, entry.contentRect.height),
    }
  })
  observer.observe(element)
})

watch(open, async (value) => {
  if (value) {
    await nextTick()
    void renderFigure()
    return
  }
  ++renderRequest
  await renderChain
  if (chart && !open.value) {
    plotly?.purge(chart)
    chart = null
    source.value = null
    ready.value = false
  }
})

async function download() {
  if (
    exporting.value ||
    !ready.value ||
    !dimensionsValid.value ||
    !exportValid.value ||
    !textSizeValid.value
  )
    return
  exporting.value = true
  try {
    await renderFigure()
    if (!chart || !figure.value) return
    const filename =
      settings.value.title
        .trim()
        .replace(/[\\/:*?"<>|]+/g, '-')
        .replace(/\s+/g, '_') || 'HydroServer_image'
    await downloadPlotlyImage(chart, {
      filename,
      format: 'png',
      scale: exportSize.value.scale,
      width: figure.value.layout.width,
      height: figure.value.layout.height,
      dpi: exportSize.value.dpi,
    })
  } catch (error) {
    console.error('Unable to download image', error)
    Snackbar.error('Unable to download the image. Please try again.')
  } finally {
    exporting.value = false
  }
}

onBeforeUnmount(() => {
  ++renderRequest
  observer?.disconnect()
  void renderChain.then(() => {
    if (chart) plotly?.purge(chart)
  })
})

defineExpose({ openPreview })
</script>

<style scoped>
.figure-preview {
  height: 100dvh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: var(--hs-background);
  color: var(--hs-text-primary);
}
.figure-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: var(--hs-space-12);
  padding: var(--hs-space-12) var(--hs-space-20);
  border-bottom: 1px solid var(--hs-border);
  background: var(--hs-surface);
}
.figure-actions {
  display: flex;
  align-items: center;
  gap: var(--hs-space-8);
  flex-wrap: wrap;
}
.figure-body {
  display: flex;
  flex: 1;
  min-height: 0;
}
.figure-editor {
  flex: 0 0 21rem;
  overflow-y: auto;
  padding: var(--hs-space-20);
  border-right: 1px solid var(--hs-border);
  background: var(--hs-surface);
}
.figure-settings-section,
.figure-trace-fields {
  display: flex;
  flex-direction: column;
  gap: var(--hs-space-12);
  min-width: 0;
}
.figure-settings-section + .figure-settings-section {
  margin-top: var(--hs-space-24);
  padding-top: var(--hs-space-20);
  border-top: 1px solid var(--hs-border);
}
.figure-dimensions {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--hs-space-12);
}
.figure-export-mode {
  width: 100%;
}
.figure-export-mode :deep(.v-btn) {
  flex: 1;
}
.figure-export-summary {
  display: flex;
  flex-direction: column;
  gap: var(--hs-space-4);
}
.figure-trace-fields {
  padding: var(--hs-space-12);
  border: 1px solid var(--hs-border);
  border-radius: var(--hs-radius-md);
  background: var(--hs-surface-subtle);
}
.figure-trace-heading {
  display: flex;
  align-items: center;
  gap: var(--hs-space-8);
}
.figure-trace-marker {
  width: var(--hs-space-20);
  height: var(--hs-space-4);
  border-radius: var(--hs-radius-sm);
}
.figure-trace-colors {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--hs-space-8);
}
.figure-color-trigger {
  min-height: var(--hs-space-32);
}
.figure-color-popup {
  width: 20rem;
  max-width: calc(100vw - var(--hs-space-24));
}
.figure-current-color {
  display: inline-block;
  width: var(--hs-space-20);
  height: var(--hs-space-20);
  margin-right: var(--hs-space-8);
  border: 1px solid var(--hs-border);
  border-radius: var(--hs-radius-sm);
}
.figure-color-palette {
  display: flex;
  flex-wrap: wrap;
  gap: var(--hs-space-4);
  padding: var(--hs-space-12);
}
.figure-color-swatch {
  width: var(--hs-space-24);
  min-width: var(--hs-space-24);
  height: var(--hs-space-24);
  border: 2px solid var(--hs-surface);
  outline: 1px solid var(--hs-border);
}
.figure-color-swatch--selected {
  outline: 2px solid var(--hs-primary);
}
.figure-stage {
  display: grid;
  place-items: center;
  flex: 1;
  min-width: 0;
  min-height: 0;
  padding: var(--hs-space-24);
  overflow: hidden;
}
.figure-frame {
  position: relative;
}
.figure-paper {
  position: absolute;
  transform-origin: top left;
  background: var(--hs-surface);
  box-shadow: var(--hs-shadow-popover);
}
@media (max-width: 800px) {
  .figure-body {
    flex-direction: column;
  }
  .figure-editor {
    flex: 0 1 42dvh;
    border-right: 0;
    border-bottom: 1px solid var(--hs-border);
  }
  .figure-header {
    padding: var(--hs-space-8) var(--hs-space-12);
  }
  .figure-actions {
    gap: var(--hs-space-4);
  }
  .figure-stage {
    padding: var(--hs-space-12);
  }
}
</style>
