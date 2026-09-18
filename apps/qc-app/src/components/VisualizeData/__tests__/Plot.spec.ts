import { flushPromises, mount } from '@vue/test-utils'
import { reactive, ref } from 'vue'
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { createTestPinia } from '@/utils/test/pinia'
import { createTestVuetify } from '@/utils/test/vuetify'

const plotly = {
  isUpdating: ref(false),
  areTooltipsEnabled: ref(true),
  visiblePoints: ref(0),
  tooltipsMaxDataPoints: ref(1000),
  tooltipsMode: ref<'auto' | 'manual'>('auto'),
  tooltipsManualEnabled: ref(true),
  hover: ref({ x: 0, y: 0 }),
  showCoordinates: ref(false),
  crosshair: ref({ visible: false }),
  axisChips: ref<any[]>([]),
  previewMode: ref(false),
  plotlyRef: ref<any>(null),
  activeTab: ref('plot'),
  pendingShareZoom: ref<any>(null),
}
const updateOptions = vi.fn()
const requestTableScroll = vi.fn()

vi.mock('@/store/plotly', () => ({
  usePlotlyStore: () =>
    reactive({ ...plotly, updateOptions, requestTableScroll }),
}))

vi.mock('@/store/dataVisualization', () => ({
  useDataVisStore: () =>
    reactive({
      selectedData: ref(null),
      hasSelectionShape: ref(false),
      qcDatastream: ref(null),
    }),
}))

const viewedSession = ref<any>(null)

vi.mock('@/store/qcSession', () => ({
  useQcSessionStore: () =>
    reactive({ viewedSession, inProgressSession: ref(null) }),
}))

vi.mock('@/composables/useDataSelection', () => ({
  useDataSelection: () => ({
    setPlotSelection: vi.fn(),
    clearSelected: vi.fn(),
  }),
}))

vi.mock('@/composables/useResizable', () => ({
  usePersistedFlag: (_key: string, initial: boolean) => ref(initial),
}))

const { handleNewPlot, zoomXaxisTo } = vi.hoisted(() => ({
  handleNewPlot: vi.fn(),
  zoomXaxisTo: vi.fn(),
}))

vi.mock('@/utils/plotting/plotly', () => ({
  handleNewPlot,
  handleRelayout: vi.fn(),
  zoomXaxisTo,
}))

vi.mock('plotly.js-dist', () => ({ default: { Plots: { resize: vi.fn() } } }))

import Plot from '@/components/VisualizeData/Plot.vue'

function mountIt(preview = true) {
  return mount(Plot, {
    props: { preview },
    global: {
      plugins: [createTestPinia(), createTestVuetify()],
      stubs: { ContextPlot: true, DataTable: true, DataVisTimeFilters: true },
    },
  })
}

describe('Plot.vue delayed mount', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    handleNewPlot.mockReset().mockResolvedValue(undefined)
    zoomXaxisTo.mockClear()
    plotly.plotlyRef.value = null
    viewedSession.value = null
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('draws into the plot element after the mount delay', async () => {
    const wrapper = mountIt()
    await vi.advanceTimersByTimeAsync(200)
    expect(handleNewPlot).toHaveBeenCalledTimes(1)
    expect(handleNewPlot).toHaveBeenCalledWith(
      wrapper.find('[data-testid="main-plot"]').element
    )
    wrapper.unmount()
  })

  it('does not draw when unmounted before the delay fires', async () => {
    const wrapper = mountIt()
    wrapper.unmount()
    await vi.advanceTimersByTimeAsync(200)
    expect(handleNewPlot).not.toHaveBeenCalled()
  })

  describe('editor zoom to the session window', () => {
    let resolveDraw: () => void

    beforeEach(() => {
      plotly.plotlyRef.value = {}
      viewedSession.value = {
        phenomenonTimeStart: '2020-01-01T00:00:00Z',
        phenomenonTimeEnd: '2020-01-02T00:00:00Z',
      }
      handleNewPlot.mockImplementation(
        () => new Promise<void>((resolve) => (resolveDraw = resolve))
      )
    })

    it('zooms once the mount draw finishes', async () => {
      const wrapper = mountIt(false)
      await vi.advanceTimersByTimeAsync(200)
      resolveDraw()
      await flushPromises()
      expect(zoomXaxisTo).toHaveBeenCalledTimes(1)
      wrapper.unmount()
    })

    it('does not zoom when unmounted while the mount draw is pending', async () => {
      const wrapper = mountIt(false)
      await vi.advanceTimersByTimeAsync(200)
      expect(handleNewPlot).toHaveBeenCalledTimes(1)
      wrapper.unmount()
      resolveDraw()
      await flushPromises()
      expect(zoomXaxisTo).not.toHaveBeenCalled()
    })
  })
})
