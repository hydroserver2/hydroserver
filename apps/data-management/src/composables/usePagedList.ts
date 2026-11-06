import { computed, onScopeDispose, ref, watch, type Ref } from 'vue'
import type { ApiResponse } from '@hydroserver/client'

export const PAGE_SIZE = 25

/**
 * Loads a server collection one page at a time for an infinite-scroll table.
 * The list restarts (debounced) whenever `query` changes; responses for an
 * outdated query are ignored.
 */
export function usePagedList<T, Q>(
  query: () => Q,
  fetchPage: (
    query: Q,
    page: { offset: number; limit: number }
  ) => Promise<ApiResponse<T[]>>
) {
  const items = ref([]) as Ref<T[]>
  const total = ref<number | null>(null)
  const loading = ref(false)
  const error = ref('')
  const hasMore = computed(
    () => total.value === null || items.value.length < total.value
  )
  let generation = 0

  async function loadMore() {
    if (loading.value || error.value || !hasMore.value) return
    const current = generation
    loading.value = true
    try {
      const res = await fetchPage(query(), {
        offset: items.value.length,
        limit: PAGE_SIZE,
      })
      if (current !== generation) return
      if (!res.ok) throw new Error(res.message)
      items.value = [...items.value, ...res.data]
      const matched = res.meta?.numberMatched
      total.value =
        typeof matched === 'number' && res.data.length
          ? matched
          : items.value.length
    } catch (e) {
      if (current === generation)
        error.value = e instanceof Error ? e.message : 'Unable to load rows.'
    } finally {
      if (current === generation) loading.value = false
    }
  }

  function reload() {
    generation++
    items.value = []
    total.value = null
    loading.value = false
    error.value = ''
    return loadMore()
  }

  function retry() {
    error.value = ''
    return loadMore()
  }

  let timer: ReturnType<typeof setTimeout> | undefined
  watch(
    () => JSON.stringify(query()),
    () => {
      clearTimeout(timer)
      timer = setTimeout(reload, 250)
    }
  )
  onScopeDispose(() => {
    clearTimeout(timer)
    generation++
  })
  void reload()

  return { items, total, loading, error, hasMore, loadMore, reload, retry }
}
