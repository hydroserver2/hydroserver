import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { ref } from 'vue'

// Snackbar stub on the @uwrl/qc-utils seam.
vi.mock('@uwrl/qc-utils', () => ({
  Snackbar: {
    success: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
  },
}))

// Stub the HydroServer store with a resolving createObservations.
// Individual tests override the mock implementation as needed.
const createObservations = vi.fn().mockResolvedValue(undefined)
vi.mock('@/store/hydroserver', () => {
  const hs = ref({
    datastreams: {
      createObservations: (...args: unknown[]) => createObservations(...args),
    },
  } as any)
  return {
    useHydroServer: () => ({ hs }),
  }
})

// Shared mutable history array — the SAME reference is handed to both
// `selectedSeries.data.history` and `editHistory.value`. This mirrors the
// production sync at src/utils/plotting/plotly.ts:207/:387 and is what makes
// the in-place `length = 0` fix in useQcSubmission observable from both seams.
const historyArr: any[] = [
  { method: 'delete', indices: [0], values: [1] } as any,
]

const selectedSeries = ref({
  id: 'qc',
  name: 'qc',
  data: {
    history: historyArr,
    dataX: [1700000000000],
    dataY: [42],
  },
} as any)
const editHistory = ref(historyArr)
const isSubmitting = ref(false)

vi.mock('@/store/plotly', () => ({
  usePlotlyStore: () => ({
    selectedSeries,
    editHistory,
    isSubmitting,
  }),
}))

vi.mock('@/store/dataVisualization', () => {
  const qcDatastream = ref({ id: 'datastream-x' } as any)
  return {
    useDataVisStore: () => ({ qcDatastream }),
  }
})

describe('useQcSubmission.submitQcEdits', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()

    // Reset shared state to a single pending edit, preserving the
    // shared-array-reference invariant between editHistory and data.history.
    historyArr.length = 0
    historyArr.push({ method: 'delete', indices: [0], values: [1] } as any)
    selectedSeries.value.data.history = historyArr
    editHistory.value = historyArr
    isSubmitting.value = false
    createObservations.mockReset()
    createObservations.mockResolvedValue(undefined)
  })

  it('clears editHistory in-place on success', async () => {
    const { useQcSubmission } = await import('@/composables/useQcSubmission')
    const { Snackbar } = await import('@uwrl/qc-utils')

    // Pre-condition: shared reference between data.history and editHistory.
    expect(selectedSeries.value.data.history).toBe(editHistory.value)
    expect(editHistory.value.length).toBe(1)

    const { submitQcEdits } = useQcSubmission()
    await submitQcEdits()

    expect(createObservations).toHaveBeenCalledTimes(1)
    expect(createObservations).toHaveBeenCalledWith(
      'datastream-x',
      expect.objectContaining({
        fields: ['phenomenonTime', 'result'],
      }),
      { mode: 'replace' }
    )
    expect(Snackbar.success).toHaveBeenCalledWith(
      'Quality-controlled observations submitted'
    )
    expect(editHistory.value.length).toBe(0)
    expect(selectedSeries.value.data.history.length).toBe(0)
    expect(isSubmitting.value).toBe(false)
  })

  it('leaves editHistory untouched on error', async () => {
    createObservations.mockRejectedValueOnce(new Error('boom'))

    const { useQcSubmission } = await import('@/composables/useQcSubmission')
    const { Snackbar } = await import('@uwrl/qc-utils')

    const { submitQcEdits } = useQcSubmission()
    await submitQcEdits()

    expect(Snackbar.error).toHaveBeenCalledTimes(1)
    expect(editHistory.value.length).toBe(1)
    expect(selectedSeries.value.data.history.length).toBe(1)
    expect(isSubmitting.value).toBe(false)
  })

  it('fires Snackbar.info and skips network when there are no edits', async () => {
    historyArr.length = 0

    const { useQcSubmission } = await import('@/composables/useQcSubmission')
    const { Snackbar } = await import('@uwrl/qc-utils')

    const { submitQcEdits } = useQcSubmission()
    await submitQcEdits()

    expect(Snackbar.info).toHaveBeenCalledWith('No edits to submit')
    expect(createObservations).not.toHaveBeenCalled()
  })
})
