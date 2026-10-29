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
            :disabled="!ready || !dimensionsValid"
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
            <v-textarea
              v-model="settings.title"
              label="Image title"
              rows="2"
              auto-grow
              hide-details
            />
            <v-select
              v-model="imageShape"
              label="Image shape"
              :items="shapes"
              hide-details
            />
            <div class="figure-dimensions">
              <v-text-field
                v-model.number="settings.width"
                @update:model-value="imageShape = 0"
                label="Width"
                type="number"
                suffix="px"
                :min="MIN_IMAGE_WIDTH"
                :max="MAX_IMAGE_DIMENSION"
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
                :max="MAX_IMAGE_DIMENSION"
                step="1"
                :rules="[(value) => dimensionRule(value, MIN_IMAGE_HEIGHT)]"
                hide-details="auto"
              />
            </div>
            <v-select
              v-model="settings.fontSize"
              label="Text size"
              :items="[16, 18, 20, 22, 24, 28, 32, 40]"
              suffix="px"
              hide-details
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
import { mdiClose, mdiDownload } from '@mdi/js'
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
  MAX_IMAGE_DIMENSION,
  type FigureSettings,
} from '@/utils/plotting/figurePreview'
import { Snackbar } from '@/utils/notifications'
import { PlotlyColors } from '@/utils/materialColors'

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
const shapes = [
  { title: 'Landscape (4:3)', value: 4 / 3 },
  { title: 'Widescreen (16:9)', value: 16 / 9 },
  { title: 'Square (1:1)', value: 1 },
  { title: 'Portrait (3:4)', value: 3 / 4 },
  { title: 'Custom', value: 0 },
]
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
      number <= MAX_IMAGE_DIMENSION) ||
    `${min}–${MAX_IMAGE_DIMENSION} px, whole numbers`
  )
}
const dimensionsValid = computed(
  () =>
    dimensionRule(settings.value.width, MIN_IMAGE_WIDTH) === true &&
    dimensionRule(settings.value.height, MIN_IMAGE_HEIGHT) === true
)
const selectedShape = ref(4 / 3)
const imageShape = computed({
  get: () => selectedShape.value,
  set: (ratio: number) => {
    selectedShape.value = ratio
    if (ratio <= 0) return
    settings.value.width = DEFAULT_IMAGE_WIDTH
    settings.value.height = Math.round(DEFAULT_IMAGE_WIDTH / ratio)
  },
})
const figure = computed<ReturnType<typeof buildFigurePreview> | null>(
  (previous) => {
    if (!source.value) return null
    if (!dimensionsValid.value) return previous ?? null
    void fontVersion.value
    if (context)
      context.font = `${settings.value.fontSize}px ${fontFamily.value}`
    return buildFigurePreview(
      source.value,
      settings.value,
      fontFamily.value,
      (text) =>
        context?.measureText(text).width ??
        Array.from(text).length * settings.value.fontSize * 0.65
    )
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
    selectedShape.value = 4 / 3
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
  if (exporting.value || !ready.value || !dimensionsValid.value) return
  exporting.value = true
  try {
    await renderFigure()
    if (!chart || !figure.value) return
    const filename =
      settings.value.title
        .trim()
        .replace(/[\\/:*?"<>|]+/g, '-')
        .replace(/\s+/g, '_') || 'HydroServer_image'
    await downloadPlotlyImage(chart, { filename, format: 'png', scale: 1 })
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
