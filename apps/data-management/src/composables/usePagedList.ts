import { computed, onScopeDispose, ref, watch, type Ref } from 'vue'
import type { ApiResponse } from '@hydroserver/client'

export const PAGE_SIZE = 25

/** Server paging with debounced query changes and lazy loading for hidden tabs. */
export function usePagedList<T, Q>(
  query: () => Q,
  fetchPage: (
    query: Q,
    page: { offset: number; limit: number }
  ) => Promise<ApiResponse<T[]>>,
  active: () => boolean = () => true
) {
  const items = ref([]) as Ref<T[]>
  const total = ref<number | null>(null)
  const loading = ref(false)
  const error = ref('')
  const hasMore = computed(
    () => total.value === null || items.value.length < total.value
  )
  let generation = 0
  let disposed = false
  let timer: ReturnType<typeof setTimeout> | undefined
  let stale = !active()

  function invalidate() {
    generation++
    clearTimeout(timer)
    timer = undefined
    items.value = []
    total.value = null
    loading.value = false
    error.value = ''
  }

  async function loadMore() {
    if (
      disposed ||
      !active() ||
      stale ||
      timer ||
      loading.value ||
      error.value ||
      !hasMore.value
    )
      return
    const current = generation
    loading.value = true
    try {
      const res = await fetchPage(query(), {
        offset: items.value.length,
        limit: PAGE_SIZE,
      })
      if (current !== generation) return
      if (!res.ok) throw new Error(res.message || 'Unable to load rows.')
      items.value = [...items.value, ...res.data]
      const matched = res.meta?.numberMatched
      // An empty response always ends paging, even if a stale total says otherwise.
      total.value = !res.data.length
        ? items.value.length
        : typeof matched === 'number'
          ? matched
          : res.data.length < PAGE_SIZE
            ? items.value.length
            : null
    } catch (e) {
      if (current === generation)
        error.value = e instanceof Error ? e.message : 'Unable to load rows.'
    } finally {
      if (current === generation) loading.value = false
    }
  }

  function reload() {
    invalidate()
    stale = !active()
    return loadMore()
  }

  function retry() {
    error.value = ''
    return loadMore()
  }

  watch(
    () => JSON.stringify(query()),
    () => {
      // Invalidate immediately: an old response must not append during debounce.
      invalidate()
      stale = !active()
      if (!stale)
        timer = setTimeout(() => {
          timer = undefined
          void loadMore()
        }, 250)
    },
    { flush: 'sync' }
  )
  watch(active, (isActive) => {
    if (!isActive) {
      if (timer) stale = true
      clearTimeout(timer)
      timer = undefined
    } else if (stale) {
      void reload()
    }
  })
  onScopeDispose(() => {
    disposed = true
    clearTimeout(timer)
    generation++
  })
  if (!stale) void reload()

  return { items, total, loading, error, hasMore, loadMore, reload, retry }
}
