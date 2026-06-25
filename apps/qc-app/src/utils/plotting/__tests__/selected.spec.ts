import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { ref } from 'vue'

vi.mock('@uwrl/qc-utils', () => ({
  EnumFilterOperations: { SELECTION: 'SELECTION' },
}))

const plotlyRef = ref<any>(null)
const dispatchFilter = vi.fn().mockResolvedValue(undefined)
const selectedSeries = ref<any>(null)
const isUpdating = ref(false)
const suppressedEchoSelection = ref<number[] | null>(null)

vi.mock('@/store/plotly', () => ({
  usePlotlyStore: () => ({
    plotlyRef,
    selectedSeries,
    isUpdating,
    editHistory: ref([]),
    suppressedEchoSelection,
  }),
}))

const selectedData = ref<number[] | null>(null)
const qcDatastream = ref<{ id: string } | null>(null)

vi.mock('@/store/dataVisualization', () => ({
  useDataVisStore: () => ({
    selectedData,
    qcDatastream,
  }),
}))

import { handleSelected } from '../selected'

/** Build a minimal Plotly stub with one trace tagged as the QC trace. */
const makePlot = (
  qcId: string,
  selectedpoints: number[] | undefined,
  windowStartIdx = 0
) => ({
  data: [
    {
      id: qcId,
      _windowStartIdx: windowStartIdx,
      selectedpoints,
    },
  ],
})

const resetState = () => {
  plotlyRef.value = null
  selectedSeries.value = null
  isUpdating.value = false
  suppressedEchoSelection.value = null
  selectedData.value = null
  qcDatastream.value = null
  dispatchFilter.mockClear()
}

describe('handleSelected', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    resetState()
  })

  it('exports handleSelected as a function', () => {
    expect(typeof handleSelected).toBe('function')
  })

  it('does not throw when called with undefined and plotlyRef is null', async () => {
    await expect(handleSelected(undefined)).resolves.toBeUndefined()
  })

  it('does not throw when called with null', async () => {
    await expect(handleSelected(null)).resolves.toBeUndefined()
  })

  it('mirrors selectedpoints into selectedData, offset by the trace windowStartIdx', () => {
    qcDatastream.value = { id: 'qc' }
    plotlyRef.value = makePlot('qc', [3, 5, 7], 10)
    void handleSelected(null)
    expect(selectedData.value).toEqual([13, 15, 17])
  })

  it('clears selectedData to null when the trace has no selectedpoints', () => {
    qcDatastream.value = { id: 'qc' }
    plotlyRef.value = makePlot('qc', undefined)
    selectedData.value = [1, 2]
    void handleSelected(null)
    expect(selectedData.value).toBeNull()
  })

  it('early-returns without dispatching when the event is a dragmode-change relayout', async () => {
    qcDatastream.value = { id: 'qc' }
    selectedSeries.value = { data: { dispatchFilter } }
    plotlyRef.value = makePlot('qc', [1])
    await handleSelected({ dragmode: 'pan' } as any)
    expect(dispatchFilter).not.toHaveBeenCalled()
  })

  it('early-returns without dispatching when the event is a zoom relayout', async () => {
    qcDatastream.value = { id: 'qc' }
    selectedSeries.value = { data: { dispatchFilter } }
    plotlyRef.value = makePlot('qc', [1])
    // The source checks `relayout?.['xaxis.range[0]']` as a truthy
    // value; pass a non-zero number so the guard actually fires.
    await handleSelected({ 'xaxis.range[0]': 1000 } as any)
    expect(dispatchFilter).not.toHaveBeenCalled()
  })

  it('suppresses the echo dispatch when fromRelayout=true and the suppression sentinel matches', async () => {
    qcDatastream.value = { id: 'qc' }
    selectedSeries.value = { data: { dispatchFilter } }
    plotlyRef.value = makePlot('qc', [4, 5])
    suppressedEchoSelection.value = [4, 5]
    await handleSelected({} as any, { fromRelayout: true })
    expect(dispatchFilter).not.toHaveBeenCalled()
    // Sentinel is one-shot; cleared even when matched.
    expect(suppressedEchoSelection.value).toBeNull()
  })

  it('still dispatches when fromRelayout=true but the suppression sentinel mismatches', async () => {
    qcDatastream.value = { id: 'qc' }
    selectedSeries.value = { data: { dispatchFilter } }
    plotlyRef.value = makePlot('qc', [4, 5])
    // Programmatic write expected [9, 10], user gesture landed [4, 5]
    // — mismatch should fall through to dispatch.
    suppressedEchoSelection.value = [9, 10]
    await handleSelected({} as any, { fromRelayout: true })
    expect(dispatchFilter).toHaveBeenCalledWith('SELECTION', [4, 5])
    expect(suppressedEchoSelection.value).toBeNull()
  })

  it('does not dispatch while isUpdating is true (programmatic re-render guard)', async () => {
    qcDatastream.value = { id: 'qc' }
    selectedSeries.value = { data: { dispatchFilter } }
    isUpdating.value = true
    plotlyRef.value = makePlot('qc', [1, 2])
    await handleSelected({} as any)
    expect(dispatchFilter).not.toHaveBeenCalled()
  })

  it('dispatches SELECTION with the offset-mapped indices on a real user gesture', async () => {
    qcDatastream.value = { id: 'qc' }
    selectedSeries.value = { data: { dispatchFilter } }
    plotlyRef.value = makePlot('qc', [2], 100)
    await handleSelected({ points: [] } as any)
    expect(dispatchFilter).toHaveBeenCalledWith('SELECTION', [102])
  })
})
