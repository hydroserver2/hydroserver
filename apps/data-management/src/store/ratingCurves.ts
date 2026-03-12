import { defineStore } from 'pinia'
import { ref } from 'vue'
import hs, {
  RATING_CURVE_ATTACHMENT_TYPE,
  type RatingCurvePreviewRow,
  type ThingFileAttachment,
} from '@hydroserver/client'

export type PendingRatingCurveCreate = {
  tempId: string
  file: File
  name: string
  description: string
  previewRows: RatingCurvePreviewRow[]
}

export type PendingRatingCurveReplace = {
  attachmentId: string | number
  file: File
  previewRows: RatingCurvePreviewRow[]
}

export type PendingRatingCurveMetadataUpdate = {
  attachmentId: string | number
  name: string
  description: string
}

export type UpdateRatingCurvesResult = {
  ok: boolean
  message?: string
  failedCreates: Array<{ tempId: string; name: string; message: string }>
  failedMetadataUpdates: Array<{ id: string | number; message: string }>
  failedReplaces: Array<{ id: string | number; message: string }>
  failedDeletes: Array<{ id: string | number; message: string }>
}

export const useRatingCurveStore = defineStore('ratingCurves', () => {
  const existingRatingCurves = ref<ThingFileAttachment[]>([])
  const pendingCreates = ref<PendingRatingCurveCreate[]>([])
  const pendingMetadataUpdates = ref<PendingRatingCurveMetadataUpdate[]>([])
  const pendingReplaces = ref<PendingRatingCurveReplace[]>([])
  const pendingDeleteIds = ref<Array<string | number>>([])
  const loading = ref(false)

  let tempIdCounter = 0

  const resetRatingCurves = () => {
    existingRatingCurves.value = []
    pendingCreates.value = []
    pendingMetadataUpdates.value = []
    pendingReplaces.value = []
    pendingDeleteIds.value = []
  }

  const loadExistingRatingCurves = async (thingId?: string | null) => {
    if (!thingId) {
      existingRatingCurves.value = []
      return
    }

    loading.value = true
    try {
      const items = await hs.thingFileAttachments.listItems(thingId, {
        type: RATING_CURVE_ATTACHMENT_TYPE,
      })
      existingRatingCurves.value = items.sort((a, b) =>
        a.name.localeCompare(b.name)
      )
    } finally {
      loading.value = false
    }
  }

  const queueRatingCurveCreate = (
    file: File,
    name: string,
    description: string,
    previewRows: RatingCurvePreviewRow[]
  ) => {
    const tempId = `pending-rating-curve-${++tempIdCounter}`
    pendingCreates.value.push({
      tempId,
      file,
      name,
      description,
      previewRows,
    })
    return tempId
  }

  const removeQueuedRatingCurveCreate = (tempId: string) => {
    pendingCreates.value = pendingCreates.value.filter(
      (item) => item.tempId !== tempId
    )
  }

  const updateQueuedRatingCurveCreate = (
    tempId: string,
    updates: {
      file?: File
      name?: string
      description?: string
      previewRows?: RatingCurvePreviewRow[]
    }
  ) => {
    const index = pendingCreates.value.findIndex((item) => item.tempId === tempId)
    if (index === -1) return false
    pendingCreates.value[index] = {
      ...pendingCreates.value[index],
      ...(updates.file ? { file: updates.file } : {}),
      ...(updates.name !== undefined ? { name: updates.name } : {}),
      ...(updates.description !== undefined
        ? { description: updates.description }
        : {}),
      ...(updates.previewRows ? { previewRows: updates.previewRows } : {}),
    }
    return true
  }

  const queueExistingRatingCurveMetadataUpdate = (
    attachmentId: string | number,
    name: string,
    description: string
  ) => {
    const key = String(attachmentId)
    const index = pendingMetadataUpdates.value.findIndex(
      (item) => String(item.attachmentId) === key
    )
    const nextItem: PendingRatingCurveMetadataUpdate = {
      attachmentId,
      name,
      description,
    }

    if (index === -1) {
      pendingMetadataUpdates.value.push(nextItem)
      return
    }

    pendingMetadataUpdates.value[index] = nextItem
  }

  const removeQueuedRatingCurveMetadataUpdate = (
    attachmentId: string | number
  ) => {
    const key = String(attachmentId)
    pendingMetadataUpdates.value = pendingMetadataUpdates.value.filter(
      (item) => String(item.attachmentId) !== key
    )
  }

  const queueExistingRatingCurveReplace = (
    attachmentId: string | number,
    file: File,
    previewRows: RatingCurvePreviewRow[]
  ) => {
    const key = String(attachmentId)
    const index = pendingReplaces.value.findIndex(
      (item) => String(item.attachmentId) === key
    )
    const nextItem: PendingRatingCurveReplace = {
      attachmentId,
      file,
      previewRows,
    }

    if (index === -1) {
      pendingReplaces.value.push(nextItem)
      return
    }

    pendingReplaces.value[index] = nextItem
  }

  const removeQueuedRatingCurveReplace = (attachmentId: string | number) => {
    const key = String(attachmentId)
    pendingReplaces.value = pendingReplaces.value.filter(
      (item) => String(item.attachmentId) !== key
    )
  }

  const queueExistingRatingCurveDelete = (attachmentId: string | number) => {
    const key = String(attachmentId)
    if (pendingDeleteIds.value.some((item) => String(item) === key)) return
    pendingDeleteIds.value.push(attachmentId)
    removeQueuedRatingCurveReplace(attachmentId)
    removeQueuedRatingCurveMetadataUpdate(attachmentId)
  }

  const updateRatingCurves = async (
    thingId: string
  ): Promise<UpdateRatingCurvesResult> => {
    loading.value = true
    let generalError = ''
    const failedCreates: UpdateRatingCurvesResult['failedCreates'] = []
    const failedMetadataUpdates: UpdateRatingCurvesResult['failedMetadataUpdates'] =
      []
    const failedReplaces: UpdateRatingCurvesResult['failedReplaces'] = []
    const failedDeletes: UpdateRatingCurvesResult['failedDeletes'] = []
    const appliedCreateTempIds = new Set<string>()
    const appliedMetadataUpdateIds = new Set<string>()
    const appliedReplaceIds = new Set<string>()
    const appliedDeleteIds = new Set<string>()

    try {
      if (pendingDeleteIds.value.length) {
        for (const id of pendingDeleteIds.value) {
          try {
            const res = await hs.thingFileAttachments.delete(thingId, id)
            if (!res.ok) {
              failedDeletes.push({
                id,
                message: res.message || 'Unable to delete rating curve.',
              })
              continue
            }
            appliedDeleteIds.add(String(id))
          } catch (error: any) {
            failedDeletes.push({
              id,
              message: error?.message || 'Unable to delete rating curve.',
            })
          }
        }
      }

      if (pendingMetadataUpdates.value.length) {
        for (const item of pendingMetadataUpdates.value) {
          const key = String(item.attachmentId)
          if (appliedDeleteIds.has(key)) {
            appliedMetadataUpdateIds.add(key)
            continue
          }

          try {
            const res = await hs.thingFileAttachments.update(
              thingId,
              item.attachmentId,
              {
                name: item.name,
                description: item.description,
              }
            )
            if (!res.ok || !res.data) {
              failedMetadataUpdates.push({
                id: item.attachmentId,
                message: res.message || 'Unable to update rating curve metadata.',
              })
              continue
            }
            appliedMetadataUpdateIds.add(key)
          } catch (error: any) {
            failedMetadataUpdates.push({
              id: item.attachmentId,
              message: error?.message || 'Unable to update rating curve metadata.',
            })
          }
        }
      }

      if (pendingReplaces.value.length) {
        for (const item of pendingReplaces.value) {
          const replaceKey = String(item.attachmentId)
          if (appliedDeleteIds.has(replaceKey)) {
            appliedReplaceIds.add(replaceKey)
            continue
          }

          try {
            const res = await hs.thingFileAttachments.replaceFile(
              thingId,
              item.attachmentId,
              item.file
            )
            if (!res.ok || !res.data) {
              failedReplaces.push({
                id: item.attachmentId,
                message: res.message || 'Unable to replace rating curve file.',
              })
              continue
            }
            appliedReplaceIds.add(replaceKey)
          } catch (error: any) {
            failedReplaces.push({
              id: item.attachmentId,
              message: error?.message || 'Unable to replace rating curve file.',
            })
          }
        }
      }

      // Process uploads after deletes so a renamed/replaced file can reuse a name.
      if (pendingCreates.value.length) {
        for (const item of pendingCreates.value) {
          try {
            const res = await hs.thingFileAttachments.upload(thingId, item.file, {
              type: RATING_CURVE_ATTACHMENT_TYPE,
              name: item.name,
              description: item.description || undefined,
            })
            if (!res.ok || !res.data) {
              failedCreates.push({
                tempId: item.tempId,
                name: item.name,
                message: res.message || 'Unable to create rating curve.',
              })
              continue
            }
            appliedCreateTempIds.add(item.tempId)
          } catch (error: any) {
            failedCreates.push({
              tempId: item.tempId,
              name: item.name,
              message: error?.message || 'Unable to create rating curve.',
            })
          }
        }
      }

      await loadExistingRatingCurves(thingId)
    } catch (error: any) {
      generalError =
        error?.message || 'Unable to synchronize rating curve changes.'
    } finally {
      pendingCreates.value = pendingCreates.value.filter(
        (item) => !appliedCreateTempIds.has(item.tempId)
      )
      pendingMetadataUpdates.value = pendingMetadataUpdates.value.filter(
        (item) => !appliedMetadataUpdateIds.has(String(item.attachmentId))
      )
      pendingReplaces.value = pendingReplaces.value.filter(
        (item) => !appliedReplaceIds.has(String(item.attachmentId))
      )
      pendingDeleteIds.value = pendingDeleteIds.value.filter(
        (id) => !appliedDeleteIds.has(String(id))
      )
      loading.value = false
    }

    return {
      ok:
        !generalError &&
        failedCreates.length === 0 &&
        failedMetadataUpdates.length === 0 &&
        failedReplaces.length === 0 &&
        failedDeletes.length === 0,
      message: generalError || undefined,
      failedCreates,
      failedMetadataUpdates,
      failedReplaces,
      failedDeletes,
    }
  }

  return {
    existingRatingCurves,
    pendingCreates,
    pendingMetadataUpdates,
    pendingReplaces,
    pendingDeleteIds,
    loading,
    loadExistingRatingCurves,
    queueRatingCurveCreate,
    removeQueuedRatingCurveCreate,
    updateQueuedRatingCurveCreate,
    queueExistingRatingCurveMetadataUpdate,
    removeQueuedRatingCurveMetadataUpdate,
    queueExistingRatingCurveReplace,
    removeQueuedRatingCurveReplace,
    queueExistingRatingCurveDelete,
    updateRatingCurves,
    resetRatingCurves,
  }
})
