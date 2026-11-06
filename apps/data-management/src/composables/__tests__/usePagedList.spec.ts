import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { effectScope, nextTick, ref } from 'vue'
import { usePagedList } from '../usePagedList'

const page = (offset: number) => ({
  ok: true as const,
  status: 200,
  data: [{ id: offset }],
  meta: { numberMatched: 100 },
})

describe('usePagedList', () => {
  beforeEach(() => vi.useFakeTimers())
  afterEach(() => vi.useRealTimers())

  it('waits while hidden and refetches once when shown after the query changed', async () => {
    const search = ref('')
    const active = ref(false)
    const fetchPage = vi.fn(async (_query: string, { offset }) => page(offset))
    const scope = effectScope()
    scope.run(() =>
      usePagedList(
        () => search.value,
        fetchPage,
        () => active.value
      )
    )

    search.value = 'n'
    await nextTick()
    search.value = 'na'
    await vi.advanceTimersByTimeAsync(500)
    expect(fetchPage).not.toHaveBeenCalled()

    active.value = true
    await vi.advanceTimersByTimeAsync(500)
    expect(fetchPage).toHaveBeenCalledTimes(1)
    expect(fetchPage).toHaveBeenLastCalledWith('na', { offset: 0, limit: 25 })

    // Hiding and showing again without a query change doesn't refetch.
    active.value = false
    await nextTick()
    active.value = true
    await vi.advanceTimersByTimeAsync(500)
    expect(fetchPage).toHaveBeenCalledTimes(1)
    scope.stop()
  })

  it('refetches the visible list once per debounced query change', async () => {
    const search = ref('')
    const fetchPage = vi.fn(async (_query: string, { offset }) => page(offset))
    const scope = effectScope()
    scope.run(() => usePagedList(() => search.value, fetchPage))
    await vi.advanceTimersByTimeAsync(0)
    expect(fetchPage).toHaveBeenCalledTimes(1)

    for (const value of ['n', 'na', 'nam']) {
      search.value = value
      await vi.advanceTimersByTimeAsync(50)
    }
    await vi.advanceTimersByTimeAsync(500)
    expect(fetchPage).toHaveBeenCalledTimes(2)
    expect(fetchPage).toHaveBeenLastCalledWith('nam', { offset: 0, limit: 25 })
    scope.stop()
  })
})
