import { defineStore } from 'pinia'
import { ref } from 'vue'
import { Snackbar } from '@/utils/notifications'
import hs, { ApiResponse, LinkedResource } from '@hydroserver/client'

export const usePhotosStore = defineStore('photos', () => {
  const photos = ref<LinkedResource[]>([])
  const newPhotos = ref<File[]>([])
  const newLinks = ref<string[]>([])
  const photosToDelete = ref<string[]>([])
  const loading = ref(false)

  const uploadNewPhotos = async (monitoringSiteId: string) => {
    if (!newPhotos.value.length && !newLinks.value.length) return

    const filePromises = newPhotos.value.map((file) => {
      const data = new FormData()
      data.append('name', file.name)
      data.append('type', 'Photo')
      data.append('file', file)
      return hs.monitoringSites.createLinkedResource(monitoringSiteId, data)
    })

    const linkPromises = newLinks.value.map((link) => {
      const data = new FormData()
      data.append('name', link)
      data.append('type', 'Photo')
      data.append('link', link)
      return hs.monitoringSites.createLinkedResource(monitoringSiteId, data)
    })

    const responses: ApiResponse<LinkedResource>[] = await Promise.all([
      ...filePromises,
      ...linkPromises,
    ])

    const photoData: LinkedResource[] = []
    responses.forEach((res) => {
      if (res.ok) {
        photoData.push(res.data)
      } else {
        console.error('Error uploading photo', res)
        Snackbar.error(res.message || 'Unable to upload photo.')
      }
    })
    photos.value = [...photos.value, ...photoData]
  }

  const deleteSelectedPhotos = async (monitoringSiteId: string) => {
    if (!photosToDelete.value.length) return
    const responses = await Promise.all(
      photosToDelete.value.map((id) =>
        hs.monitoringSites.deleteLinkedResource(monitoringSiteId, id)
      )
    )
    const deletedIds: string[] = []
    responses.forEach((res, i) => {
      const id = photosToDelete.value[i]
      if (res.ok) {
        deletedIds.push(id)
      } else {
        console.error('Error deleting photo', res)
        Snackbar.error(res.message || 'Unable to delete photo.')
      }
    })
    photos.value = photos.value.filter((p) => !deletedIds.includes(p.id))
  }

  const updatePhotos = async (monitoringSiteId: string) => {
    try {
      loading.value = true
      await uploadNewPhotos(monitoringSiteId)
      await deleteSelectedPhotos(monitoringSiteId)
    } catch (error) {
      console.error('Error updating photos', error)
      Snackbar.error('Unable to update photos.')
    } finally {
      loading.value = false
      newPhotos.value = []
      newLinks.value = []
      photosToDelete.value = []
    }
  }

  return {
    photos,
    newPhotos,
    newLinks,
    photosToDelete,
    loading,
    updatePhotos,
  }
})
