import { defineStore } from 'pinia'
import { ref } from 'vue'
import hs, { ApiResponse, FileAttachment } from '@hydroserver/client'

export const usePhotosStore = defineStore('photos', () => {
  const photos = ref<FileAttachment[]>([])
  const newPhotos = ref<File[]>([])
  const photosToDelete = ref<string[]>([])
  const loading = ref(false)

  const uploadNewPhotos = async (thingId: string) => {
    if (!newPhotos.value.length) return

    const promises = newPhotos.value.map(async (file) => {
      const data = new FormData()
      data.append('file', file)
      data.append('file_attachment_type', 'Photo')
      return await hs.things.uploadAttachments(thingId, data)
    })

    const newPhotoResponses: ApiResponse<FileAttachment>[] = await Promise.all(promises)
    const photoData = newPhotoResponses.map(
      (res: ApiResponse<FileAttachment>) => res.data
    )
    photos.value = [...photos.value, ...photoData]
  }

  const deleteSelectedPhotos = async (thingId: string) => {
    if (!photosToDelete.value.length) return
    await Promise.all(
      photosToDelete.value.map((p) => hs.things.deleteAttachment(thingId, p))
    )
    photos.value = photos.value.filter(
      (p) => !photosToDelete.value.includes(p.name)
    )
  }

  const updatePhotos = async (thingId: string) => {
    try {
      loading.value = true
      await uploadNewPhotos(thingId)
      await deleteSelectedPhotos(thingId)
    } catch (error) {
      console.error('Error updating photos', error)
    } finally {
      loading.value = false
      newPhotos.value = []
      photosToDelete.value = []
    }
  }

  return {
    photos,
    newPhotos,
    photosToDelete,
    loading,
    updatePhotos,
  }
})
