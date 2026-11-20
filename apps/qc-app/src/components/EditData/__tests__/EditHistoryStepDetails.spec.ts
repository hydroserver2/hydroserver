import { mount } from '@vue/test-utils'
import { describe, it, expect } from 'vitest'
import { createTestVuetify } from '@/utils/test/vuetify'
import EditHistoryStepDetails from '@/components/EditData/EditHistoryStepDetails.vue'
import { formatDateTime } from '@/utils/time'
;(globalThis as any).ResizeObserver ||= class {
  observe() {}
  unobserve() {}
  disconnect() {}
}

const T0 = Date.UTC(2026, 2, 3, 12, 5)
const MIN = 60_000

const mountDetails = (entry: Record<string, unknown>) =>
  mount(EditHistoryStepDetails, {
    props: {
      entry: { args: [], execution: { startedAt: 0, inFlight: false }, ...entry } as any,
      index: 0,
      applied: true,
      readOnly: true,
    },
    global: { plugins: [createTestVuetify()] },
  })

describe('EditHistoryStepDetails', () => {
  it('lists the time of every point a step changed', () => {
    const times = Float64Array.from([T0, T0 + 7 * MIN, T0 + 30 * MIN])
    const w = mountDetails({
      method: 'DELETE_POINTS',
      execution: { startedAt: 0, inFlight: false, times },
    })
    const points = w.find('[data-testid="history-points-0"]')
    expect(points.text()).toContain('Points (3)')
    for (const t of times) expect(points.text()).toContain(formatDateTime(t))
  })

  it('shows a selection by its points rather than their positions', () => {
    const w = mountDetails({
      method: 'SELECTION',
      args: [[4, 11, 40]],
      execution: {
        startedAt: 0,
        inFlight: false,
        times: Float64Array.from([T0, T0 + MIN, T0 + 2 * MIN]),
      },
    })
    expect(w.find('[data-testid="history-points-0"]').exists()).toBe(true)
    expect(w.text()).not.toContain('Arguments')
    expect(w.text()).not.toContain('[4, 11, 40]')
  })

  it('keeps the arguments of a step that has more to it than points', () => {
    const w = mountDetails({
      method: 'CHANGE_VALUES',
      args: ['ADD', 2],
      execution: { startedAt: 0, inFlight: false, times: Float64Array.from([T0]) },
    })
    expect(w.text()).toContain('Arguments')
    expect(w.text()).toContain('Points (1)')
  })

  it('has no points list for a step that touched none', () => {
    const w = mountDetails({ method: 'FIND_GAPS', args: [15, 'MINUTE'] })
    expect(w.find('[data-testid="history-points-0"]').exists()).toBe(false)
  })
})
