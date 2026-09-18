import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { ref } from 'vue'

const { serializeHistory } = vi.hoisted(() => ({
  serializeHistory: vi.fn(() => ({ version: 1 })),
}))

vi.mock('@uwrl/qc-utils', () => ({
  serializeHistory,
  parseHistory: vi.fn(),
  applyHistory: vi.fn(),
}))

const selectedSeries = ref<any>({ data: { id: 'record' } })
const qcDatastream = ref<any>({ id: 'mgd', name: 'Managed' })
const beginDate = ref(new Date('2020-01-01T00:00:00Z'))
const endDate = ref(new Date('2020-12-31T00:00:00Z'))
const viewedSession = ref<any>(null)
const inProgressSession = ref<any>(null)

vi.mock('@/store/plotly', () => ({
  usePlotlyStore: () => ({ selectedSeries }),
}))
vi.mock('@/store/dataVisualization', () => ({
  useDataVisStore: () => ({ qcDatastream, beginDate, endDate }),
}))
vi.mock('@/store/observations', () => ({
  useObservationStore: () => ({ fetchObservationsInRange: vi.fn() }),
}))
vi.mock('@/store/qcSession', () => ({
  useQcSessionStore: () => ({ viewedSession, inProgressSession }),
}))

import { useQcHistory } from '../useQcHistory'

const session = (start: string, end: string) => ({
  phenomenonTimeStart: start,
  phenomenonTimeEnd: end,
})

describe('useQcHistory.exportHistory window', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    selectedSeries.value = { data: { id: 'record' } }
    viewedSession.value = null
    inProgressSession.value = null
    URL.createObjectURL = vi.fn(() => 'blob:history')
    URL.revokeObjectURL = vi.fn()
    // jsdom does not implement the download navigation.
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  const exportedWindow = () =>
    (serializeHistory.mock.calls[0] as unknown as [unknown, unknown])[1]

  it('uses the viewed session window while editing', async () => {
    viewedSession.value = session('2023-03-01T00:00:00Z', '2023-04-01T00:00:00Z')
    inProgressSession.value = session(
      '2024-01-01T00:00:00Z',
      '2024-02-01T00:00:00Z'
    )

    await useQcHistory().exportHistory()

    expect(serializeHistory).toHaveBeenCalledWith(
      { id: 'record' },
      expect.anything()
    )
    expect(exportedWindow()).toEqual({
      startDate: '2023-03-01T00:00:00.000Z',
      endDate: '2023-04-01T00:00:00.000Z',
    })
  })

  it('falls back to the in-progress session when none is viewed', async () => {
    inProgressSession.value = session(
      '2024-01-01T00:00:00Z',
      '2024-02-01T00:00:00Z'
    )

    await useQcHistory().exportHistory()

    expect(exportedWindow()).toEqual({
      startDate: '2024-01-01T00:00:00.000Z',
      endDate: '2024-02-01T00:00:00.000Z',
    })
  })

  it('uses the loaded window when there is no session', async () => {
    await useQcHistory().exportHistory()

    expect(exportedWindow()).toEqual({
      startDate: '2020-01-01T00:00:00.000Z',
      endDate: '2020-12-31T00:00:00.000Z',
    })
  })

  it('throws when no series is loaded', async () => {
    selectedSeries.value = null

    await expect(useQcHistory().exportHistory()).rejects.toThrow(
      'No QC series loaded.'
    )
    expect(serializeHistory).not.toHaveBeenCalled()
  })
})
