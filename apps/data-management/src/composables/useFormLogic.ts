import { ApiResponse } from '@hydroserver/client'
import { ref, Ref, computed, onMounted } from 'vue'
import { VForm } from 'vuetify/components'

interface WithId {
  id: string
}

export function useFormLogic<T extends WithId>(
  createItem: (item: T) => Promise<ApiResponse<T>>,
  updateItem: (item: T, originalItem: T) => Promise<ApiResponse<T>>,
  ItemClass: new () => T,
  initialItem?: T
) {
  const item = ref(new ItemClass()) as Ref<T>
  const isEdit = computed(() => !!initialItem)
  const valid = ref(false)
  const myForm = ref<VForm>()

  async function uploadItem() {
    await myForm.value?.validate()
    if (!valid.value) return
    if (initialItem) {
      const res = await updateItem(item.value, initialItem!)
      return res.data
    }
    const res = await createItem(item.value)
    return res.data
  }

  onMounted(() => {
    if (initialItem) item.value = JSON.parse(JSON.stringify(initialItem))
  })

  return { item, isEdit, valid, myForm, uploadItem }
}
