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
  it('ignores a response that arrives during the next query debounce', async () => {
    const search = ref('old')
    let resolveOld!: (result: ReturnType<typeof page>) => void
    const fetchPage = vi
      .fn()
      .mockImplementationOnce(
        () =>
          new Promise((resolve) => {
            resolveOld = resolve
          })
      )
      .mockResolvedValue(page(25))
    const scope = effectScope()
    const list = scope.run(() => usePagedList(() => search.value, fetchPage))!
    search.value = 'new'
    resolveOld(page(0))
    await vi.advanceTimersByTimeAsync(100)
    expect(list.items.value).toEqual([])
    await list.loadMore()
    expect(fetchPage).toHaveBeenCalledTimes(1)
    await vi.advanceTimersByTimeAsync(200)
    expect(list.items.value).toEqual([{ id: 25 }])
    expect(fetchPage).toHaveBeenLastCalledWith('new', { offset: 0, limit: 25 })
    scope.stop()
  })

  it('retains loaded rows after a page failure and retries the same offset', async () => {
    const fetchPage = vi
      .fn()
      .mockResolvedValueOnce(page(0))
      .mockResolvedValueOnce({ ok: false, status: 503, message: 'Try again' })
      .mockResolvedValueOnce({ ...page(1), meta: { numberMatched: 2 } })
    const scope = effectScope()
    const list = scope.run(() => usePagedList(() => '', fetchPage))!
    await vi.advanceTimersByTimeAsync(0)
    await list.loadMore()
    expect(list.error.value).toBe('Try again')
    expect(list.items.value).toEqual([{ id: 0 }])
    await list.retry()
    expect(fetchPage).toHaveBeenLastCalledWith('', { offset: 1, limit: 25 })
    expect(list.items.value).toEqual([{ id: 0 }, { id: 1 }])
    expect(list.hasMore.value).toBe(false)
    await list.loadMore()
    expect(fetchPage).toHaveBeenCalledTimes(3)
    scope.stop()
  })

  it('uses page length when totals are absent and stops on an empty page', async () => {
    const fetchPage = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        data: Array.from({ length: 25 }, (_, id) => ({ id })),
      })
      .mockResolvedValueOnce({ ...page(25), data: [] })
    const scope = effectScope()
    const list = scope.run(() => usePagedList(() => '', fetchPage))!
    await vi.advanceTimersByTimeAsync(0)
    expect(list.hasMore.value).toBe(true)
    await list.loadMore()
    expect(list.total.value).toBe(25)
    expect(list.hasMore.value).toBe(false)
    scope.stop()
  })

  it('does not fetch hidden lists or update after disposal', async () => {
    const active = ref(true)
    let resolve!: (result: ReturnType<typeof page>) => void
    const fetchPage = vi.fn(
      () =>
        new Promise<ReturnType<typeof page>>((done) => {
          resolve = done
        })
    )
    const scope = effectScope()
    const list = scope.run(() =>
      usePagedList(
        () => '',
        fetchPage,
        () => active.value
      )
    )!
    active.value = false
    await nextTick()
    await list.loadMore()
    expect(fetchPage).toHaveBeenCalledTimes(1)
    scope.stop()
    resolve(page(0))
    await vi.advanceTimersByTimeAsync(0)
    expect(list.items.value).toEqual([])
    await list.reload()
    expect(fetchPage).toHaveBeenCalledTimes(1)
  })
})
