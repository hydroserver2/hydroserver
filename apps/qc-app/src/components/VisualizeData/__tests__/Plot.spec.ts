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
  plotlyRef: ref<any>(null),
  activeTab: ref('plot'),
  pendingShareZoom: ref<any>(null),
  shareZoomEditTarget: ref<string | null>(null),
}
const updateOptions = vi.fn()
const requestTableScroll = vi.fn()

vi.mock('@/store/plotly', () => ({
  usePlotlyStore: () =>
    reactive({ ...plotly, updateOptions, requestTableScroll }),
}))

const pendingPlotWork = ref(0)
async function trackPlotWork(work: () => Promise<void>) {
  pendingPlotWork.value++
  try {
    await work()
  } finally {
    pendingPlotWork.value--
  }
}

const qcDatastream = ref<{ id: string } | null>(null)

vi.mock('@/store/dataVisualization', () => ({
  useDataVisStore: () =>
    reactive({
      selectedData: ref(null),
      hasSelectionShape: ref(false),
      qcDatastream,
      trackPlotWork,
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

const isPlotPreview = ref(true)

vi.mock('@/store/userInterface', () => ({
  useUIStore: () => reactive({ isPlotPreview }),
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

function mountIt(preview = true, slots: Record<string, string> = {}) {
  isPlotPreview.value = preview
  return mount(Plot, {
    slots,
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
    pendingPlotWork.value = 0
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

  describe('opening on the Table tab', () => {
    beforeEach(() => {
      plotly.activeTab.value = 'table'
    })
    afterEach(() => {
      plotly.activeTab.value = 'plot'
    })

    it('waits for the plot element instead of drawing into nothing', async () => {
      const wrapper = mountIt()
      await vi.advanceTimersByTimeAsync(200)
      expect(wrapper.find('[data-testid="main-plot"]').exists()).toBe(false)
      expect(handleNewPlot).not.toHaveBeenCalled()
      wrapper.unmount()
    })

    it('draws once the Plot tab renders the element', async () => {
      const wrapper = mountIt()
      await vi.advanceTimersByTimeAsync(200)
      plotly.activeTab.value = 'plot'
      await flushPromises()
      await vi.advanceTimersByTimeAsync(200)
      expect(handleNewPlot).toHaveBeenCalledTimes(1)
      expect(handleNewPlot).toHaveBeenCalledWith(
        wrapper.find('[data-testid="main-plot"]').element
      )
      wrapper.unmount()
    })
  })

  it('counts the mount draw as plot work from mount until it is drawn', async () => {
    let finishDraw!: () => void
    handleNewPlot.mockImplementationOnce(
      () => new Promise<void>((r) => (finishDraw = r))
    )
    const wrapper = mountIt()
    await flushPromises()
    expect(pendingPlotWork.value).toBe(1)
    await vi.advanceTimersByTimeAsync(200)
    expect(pendingPlotWork.value).toBe(1)
    finishDraw()
    await flushPromises()
    expect(pendingPlotWork.value).toBe(0)
    wrapper.unmount()
  })

  it('releases the plot work when unmounted before the delay fires', async () => {
    const wrapper = mountIt()
    await flushPromises()
    wrapper.unmount()
    await flushPromises()
    expect(pendingPlotWork.value).toBe(0)
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

  describe('a share link zoom against the session window', () => {
    const windowA = {
      phenomenonTimeStart: '2020-01-01T00:00:00Z',
      phenomenonTimeEnd: '2020-01-02T00:00:00Z',
    }
    const windowB = {
      phenomenonTimeStart: '2020-02-01T00:00:00Z',
      phenomenonTimeEnd: '2020-02-02T00:00:00Z',
    }

    beforeEach(() => {
      plotly.plotlyRef.value = {}
      plotly.pendingShareZoom.value = { xRange: [1, 2], source: 'user' }
      handleNewPlot.mockResolvedValue(undefined)
    })

    afterEach(() => {
      plotly.pendingShareZoom.value = null
      plotly.shareZoomEditTarget.value = null
      qcDatastream.value = null
    })

    it('leaves a later editor to open on its own session window', async () => {
      // A Select-view link: a zoom, and no edit target for it to outrank.
      const wrapper = mountIt(true)
      await vi.advanceTimersByTimeAsync(200)
      await flushPromises()
      expect(zoomXaxisTo).not.toHaveBeenCalled()

      // The user opens the editor later in the same page life.
      isPlotPreview.value = false
      qcDatastream.value = { id: 'mgd-1' }
      viewedSession.value = windowA
      await flushPromises()

      expect(zoomXaxisTo).toHaveBeenCalledTimes(1)
      wrapper.unmount()
    })

    it('outranks the session window of the editor the link opened', async () => {
      plotly.shareZoomEditTarget.value = 'mgd-1'
      qcDatastream.value = { id: 'mgd-1' }
      const wrapper = mountIt(false)
      await vi.advanceTimersByTimeAsync(200)
      await flushPromises()

      viewedSession.value = windowA
      await flushPromises()
      expect(zoomXaxisTo).not.toHaveBeenCalled()

      // Only the window the link landed on; viewing another one zooms.
      viewedSession.value = windowB
      await flushPromises()
      expect(zoomXaxisTo).toHaveBeenCalledTimes(1)
      wrapper.unmount()
    })
  })

  it('renders the body overlay under the toolbar, not over it', () => {
    const wrapper = mountIt(false, {
      'body-overlay': '<div data-testid="overlay-probe" />',
    })
    expect(wrapper.find('.plot-header [data-testid="overlay-probe"]').exists()).toBe(false)
    expect(wrapper.find('.plot-body [data-testid="overlay-probe"]').exists()).toBe(true)
    wrapper.unmount()
  })
})
