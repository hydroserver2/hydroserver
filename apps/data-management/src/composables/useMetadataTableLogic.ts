import { computed, ref, type Ref } from 'vue'
import type { ApiResponse } from '@hydroserver/client'
import { usePagedList } from './usePagedList'
import type { Scoped } from './tableScope'

const UUID = /^[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}$/i

interface MetadataRow {
  id: string
  workspaceId?: string | null
}

/**
 * A paged metadata table (methods, units, ...) showing a workspace's own
 * items, the shared system items, or both, searched and sorted by the server.
 */
export function useMetadataTableLogic<T extends MetadataRow>(
  service: {
    list: (params: any) => Promise<ApiResponse<T[]>>
    get: (id: string) => Promise<ApiResponse<T>>
    delete: (id: string) => Promise<unknown>
  },
  ItemClass: new () => T,
  workspaceId: Ref<string | undefined>,
  scope: Ref<'workspace' | 'system' | 'all'>,
  search: Ref<string | undefined>
) {
  const openEdit = ref(false)
  const openDelete = ref(false)
  const item = ref(new ItemClass()) as Ref<Scoped<T>>

  const page = usePagedList(
    () => ({
      workspaceId:
        !workspaceId.value || scope.value === 'system'
          ? ['null']
          : scope.value === 'workspace'
            ? [workspaceId.value]
            : [workspaceId.value, 'null'],
      q: search.value?.trim() || undefined,
      sortby: ['name'],
    }),
    async (query, range) => {
      // UUIDs aren't in the full-text search index, so look them up directly.
      if (!query.q || !UUID.test(query.q))
        return service.list({ ...query, ...range })
      const res = await service.get(query.q)
      const rows =
        res.ok && query.workspaceId.includes(res.data.workspaceId ?? 'null')
          ? [res.data]
          : []
      return {
        ok: true,
        status: 200,
        data: rows,
        meta: { numberMatched: rows.length },
      }
    }
  )
  const items = computed(() =>
    page.items.value.map((row) =>
      Object.assign(row, {
        _scope: row.workspaceId ? ('workspace' as const) : ('system' as const),
      })
    )
  )

  function openDialog(selectedItem: Scoped<T>, dialog: string) {
    item.value = selectedItem
    if (dialog === 'edit') openEdit.value = true
    else if (dialog === 'delete') openDelete.value = true
  }

  const onUpdate = (updatedItem: T) => {
    page.items.value = page.items.value.map((row) =>
      row.id === updatedItem.id ? updatedItem : row
    )
  }

  const onDelete = async () => {
    try {
      await service.delete(item.value.id)
      page.items.value = page.items.value.filter(
        (row) => row.id !== item.value.id
      )
      if (page.total.value) page.total.value--
      openDelete.value = false
    } catch (error) {
      console.error(`Error deleting table item`, error)
    }
  }

  return {
    openEdit,
    openDelete,
    item,
    items,
    isLoading: page.loading,
    hasMore: page.hasMore,
    error: page.error,
    loadMore: page.loadMore,
    retry: page.retry,
    openDialog,
    onUpdate,
    onDelete,
  }
}
