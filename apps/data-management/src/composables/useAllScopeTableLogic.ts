import { Ref, ref, watch } from 'vue'
import { Scoped } from './tableScope'

interface WithId {
  id: string
}

/**
 * Like useTableLogic, but for the merged "All" metadata view: fetches a
 * workspace's own items alongside the shared system items and tags each with
 * where it came from, so the table can show a Scope column and only allow
 * editing the rows this workspace actually owns.
 */
export function useAllScopeTableLogic<T extends WithId>(
  fetchWorkspaceFn: (wsId: string) => Promise<T[]>,
  fetchSystemFn: () => Promise<T[]>,
  deleteFn: (id: string) => Promise<any>,
  ItemClass: new () => T,
  idRef: Ref<string | null | undefined>
) {
  const openEdit = ref(false)
  const openDelete = ref(false)
  const item = ref(new ItemClass()) as Ref<Scoped<T>>
  const items: Ref<Scoped<T>[]> = ref([])

  function openDialog(selectedItem: T, dialog: string) {
    item.value = selectedItem
    if (dialog === 'edit') openEdit.value = true
    else if (dialog === 'delete') openDelete.value = true
  }

  const onUpdate = (updatedItem: T) => {
    const index = items.value.findIndex((u) => u.id === updatedItem.id)
    if (index !== -1)
      items.value[index] = Object.assign(updatedItem, {
        _scope: items.value[index]._scope,
      })
  }

  const onDelete = async () => {
    if (!item.value) return
    try {
      await deleteFn(item.value.id)
      items.value = items.value.filter((u) => u.id !== item.value.id)
      openDelete.value = false
    } catch (error) {
      console.error(`Error deleting table item`, error)
    }
  }

  async function loadData() {
    if (!idRef.value) {
      items.value = []
      return
    }
    try {
      const [workspaceItems, systemItems] = await Promise.all([
        fetchWorkspaceFn(idRef.value),
        fetchSystemFn(),
      ])
      items.value = [
        ...workspaceItems.map((i) => Object.assign(i, { _scope: 'workspace' as const })),
        ...systemItems.map((i) => Object.assign(i, { _scope: 'system' as const })),
      ]
    } catch (error) {
      console.error(`Error fetching table items`, error)
    }
  }

  watch(
    idRef,
    async (newVal, oldVal) => {
      if (newVal !== oldVal) await loadData()
    },
    { immediate: true }
  )

  return {
    openEdit,
    openDelete,
    item,
    items,
    openDialog,
    onUpdate,
    onDelete,
  }
}
