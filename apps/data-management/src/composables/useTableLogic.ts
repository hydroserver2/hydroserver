import { Ref, ref, watch } from 'vue'

interface WithId {
  id: string
}

export function useTableLogic<T extends WithId>(
  fetchFn: (wsId: string) => Promise<T[]>,
  deleteFn: (id: string) => Promise<any>,
  ItemClass: new () => T,
  idRef: Ref<string | null | undefined>
) {
  const openEdit = ref(false)
  const openDelete = ref(false)
  const openAccessControl = ref(false)
  const item = ref(new ItemClass()) as Ref<T>
  const items: Ref<T[]> = ref([])

  function openDialog(selectedItem: T, dialog: string) {
    item.value = selectedItem
    if (dialog === 'edit') openEdit.value = true
    else if (dialog === 'delete') openDelete.value = true
    else if (dialog === 'accessControl') openAccessControl.value = true
  }

  // For emitting the updated item to parent. Assume child calls api update.
  const onUpdate = (updatedItem: T) => {
    const index = items.value.findIndex((u: any) => u.id === updatedItem.id)
    if (index !== -1) items.value[index] = updatedItem
  }

  const onDelete = async () => {
    if (!item.value) return
    try {
      await deleteFn(item.value.id)
      items.value = items.value.filter((u: any) => u.id !== item.value.id)
      openDelete.value = false
    } catch (error) {
      console.error(`Error deleting table item`, error)
    }
  }

  async function loadData() {
    try {
      if (!idRef.value) {
        items.value = []
        return
      }
      items.value = await fetchFn(idRef.value)
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
    openAccessControl,
    item,
    items,
    openDialog,
    onUpdate,
    onDelete,
  }
}
