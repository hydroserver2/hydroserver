import { onMounted, Ref, ref } from 'vue'

interface WithId {
  id: string
}

export function useSystemTableLogic<T extends WithId>(
  fetchFn: () => Promise<T[]>,
  deleteFn: (id: string) => Promise<any>,
  ItemClass: new () => T
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

  onMounted(async () => {
    try {
      items.value = await fetchFn()
    } catch (error) {
      console.error(`Error fetching table items`, error)
    }
  })

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
