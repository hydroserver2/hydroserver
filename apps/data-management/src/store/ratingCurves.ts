import { defineStore } from 'pinia'
import { ref } from 'vue'
import hs, {
  type RatingCurve,
  type RatingCurveFittingMethod,
  type RatingCurvePoint,
  type RatingCurvePreviewRow,
} from '@hydroserver/client'

export type PendingRatingCurveCreate = {
  tempId: string
  name: string
  description: string
  fittingMethod: RatingCurveFittingMethod
  points: RatingCurvePoint[]
  previewRows: RatingCurvePreviewRow[]
}

export type PendingRatingCurveReplace = {
  ratingCurveId: string
  points: RatingCurvePoint[]
  previewRows: RatingCurvePreviewRow[]
}

export type PendingRatingCurveMetadataUpdate = {
  ratingCurveId: string
  name: string
  description: string
  fittingMethod: RatingCurveFittingMethod
}

export type UpdateRatingCurvesResult = {
  ok: boolean
  message?: string
  failedCreates: Array<{ tempId: string; name: string; message: string }>
  failedMetadataUpdates: Array<{ id: string; message: string }>
  failedReplaces: Array<{ id: string; message: string }>
  failedDeletes: Array<{ id: string; message: string }>
}

export const useRatingCurveStore = defineStore('ratingCurves', () => {
  const existingRatingCurves = ref<RatingCurve[]>([])
  const pendingCreates = ref<PendingRatingCurveCreate[]>([])
  const pendingMetadataUpdates = ref<PendingRatingCurveMetadataUpdate[]>([])
  const pendingReplaces = ref<PendingRatingCurveReplace[]>([])
  const pendingDeleteIds = ref<string[]>([])
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
      const items = await hs.ratingCurves.listItemsForThing(thingId, {
        order_by: ['name'],
      })
      existingRatingCurves.value = [...items].sort((a, b) =>
        a.name.localeCompare(b.name)
      )
    } finally {
      loading.value = false
    }
  }

  const queueRatingCurveCreate = (
    name: string,
    description: string,
    fittingMethod: RatingCurveFittingMethod,
    points: RatingCurvePoint[],
    previewRows: RatingCurvePreviewRow[]
  ) => {
    const tempId = `pending-rating-curve-${++tempIdCounter}`
    pendingCreates.value.push({
      tempId,
      name,
      description,
      fittingMethod,
      points,
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
      name?: string
      description?: string
      fittingMethod?: RatingCurveFittingMethod
      points?: RatingCurvePoint[]
      previewRows?: RatingCurvePreviewRow[]
    }
  ) => {
    const index = pendingCreates.value.findIndex((item) => item.tempId === tempId)
    if (index === -1) return false
    pendingCreates.value[index] = {
      ...pendingCreates.value[index],
      ...(updates.name !== undefined ? { name: updates.name } : {}),
      ...(updates.description !== undefined
        ? { description: updates.description }
        : {}),
      ...(updates.fittingMethod !== undefined
        ? { fittingMethod: updates.fittingMethod }
        : {}),
      ...(updates.points ? { points: updates.points } : {}),
      ...(updates.previewRows ? { previewRows: updates.previewRows } : {}),
    }
    return true
  }

  const queueExistingRatingCurveMetadataUpdate = (
    ratingCurveId: string,
    name: string,
    description: string,
    fittingMethod: RatingCurveFittingMethod
  ) => {
    const key = String(ratingCurveId)
    const index = pendingMetadataUpdates.value.findIndex(
      (item) => String(item.ratingCurveId) === key
    )
    const nextItem: PendingRatingCurveMetadataUpdate = {
      ratingCurveId,
      name,
      description,
      fittingMethod,
    }

    if (index === -1) {
      pendingMetadataUpdates.value.push(nextItem)
      return
    }

    pendingMetadataUpdates.value[index] = nextItem
  }

  const removeQueuedRatingCurveMetadataUpdate = (ratingCurveId: string) => {
    const key = String(ratingCurveId)
    pendingMetadataUpdates.value = pendingMetadataUpdates.value.filter(
      (item) => String(item.ratingCurveId) !== key
    )
  }

  const queueExistingRatingCurveReplace = (
    ratingCurveId: string,
    points: RatingCurvePoint[],
    previewRows: RatingCurvePreviewRow[]
  ) => {
    const key = String(ratingCurveId)
    const index = pendingReplaces.value.findIndex(
      (item) => String(item.ratingCurveId) === key
    )
    const nextItem: PendingRatingCurveReplace = {
      ratingCurveId,
      points,
      previewRows,
    }

    if (index === -1) {
      pendingReplaces.value.push(nextItem)
      return
    }

    pendingReplaces.value[index] = nextItem
  }

  const removeQueuedRatingCurveReplace = (ratingCurveId: string) => {
    const key = String(ratingCurveId)
    pendingReplaces.value = pendingReplaces.value.filter(
      (item) => String(item.ratingCurveId) !== key
    )
  }

  const queueExistingRatingCurveDelete = (ratingCurveId: string) => {
    const key = String(ratingCurveId)
    if (pendingDeleteIds.value.some((item) => String(item) === key)) return
    pendingDeleteIds.value.push(ratingCurveId)
    removeQueuedRatingCurveReplace(ratingCurveId)
    removeQueuedRatingCurveMetadataUpdate(ratingCurveId)
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
    const metadataUpdatesById = new Map(
      pendingMetadataUpdates.value.map((item) => [
        String(item.ratingCurveId),
        item,
      ])
    )
    const replacesById = new Map(
      pendingReplaces.value.map((item) => [String(item.ratingCurveId), item])
    )

    try {
      for (const id of pendingDeleteIds.value) {
        try {
          const res = await hs.ratingCurves.delete(String(id))
          if (!res.ok) {
            failedDeletes.push({
              id: String(id),
              message: res.message || 'Unable to delete rating curve.',
            })
            continue
          }
          appliedDeleteIds.add(String(id))
        } catch (error: any) {
          failedDeletes.push({
            id: String(id),
            message: error?.message || 'Unable to delete rating curve.',
          })
        }
      }

      const updateIds = new Set([
        ...metadataUpdatesById.keys(),
        ...replacesById.keys(),
      ])

      for (const key of updateIds) {
        if (appliedDeleteIds.has(key)) {
          if (metadataUpdatesById.has(key)) appliedMetadataUpdateIds.add(key)
          if (replacesById.has(key)) appliedReplaceIds.add(key)
          continue
        }

        const metadataUpdate = metadataUpdatesById.get(key)
        const replace = replacesById.get(key)
        const curve = existingRatingCurves.value.find(
          (item) => String(item.id) === key
        )

        if (!curve) {
          if (metadataUpdate) {
            failedMetadataUpdates.push({
              id: metadataUpdate.ratingCurveId,
              message: 'Unable to find rating curve.',
            })
          }
          if (replace) {
            failedReplaces.push({
              id: replace.ratingCurveId,
              message: 'Unable to find rating curve.',
            })
          }
          continue
        }

        try {
          const res = await hs.ratingCurves.update({
            id: curve.id,
            name: metadataUpdate?.name ?? curve.name,
            description:
              metadataUpdate?.description ?? (curve.description || null),
            fittingMethod: metadataUpdate?.fittingMethod ?? curve.fittingMethod,
            points: replace?.points ?? curve.points ?? [],
          })

          if (!res.ok || !res.data) {
            if (metadataUpdate) {
              failedMetadataUpdates.push({
                id: metadataUpdate.ratingCurveId,
                message:
                  res.message ||
                  'Unable to update rating curve metadata.',
              })
            }
            if (replace) {
              failedReplaces.push({
                id: replace.ratingCurveId,
                message:
                  res.message ||
                  'Unable to replace rating curve points.',
              })
            }
            continue
          }

          if (metadataUpdate) appliedMetadataUpdateIds.add(key)
          if (replace) appliedReplaceIds.add(key)
        } catch (error: any) {
          if (metadataUpdate) {
            failedMetadataUpdates.push({
              id: metadataUpdate.ratingCurveId,
              message: error?.message || 'Unable to update rating curve metadata.',
            })
          }
          if (replace) {
            failedReplaces.push({
              id: replace.ratingCurveId,
              message: error?.message || 'Unable to replace rating curve points.',
            })
          }
        }
      }

      for (const item of pendingCreates.value) {
        try {
          const res = await hs.ratingCurves.create({
            id: '',
            name: item.name,
            description: item.description || null,
            fittingMethod: item.fittingMethod,
            thingId,
            points: item.points,
          })
          if (!res.ok || !res.data) {
            failedCreates.push({
              tempId: item.tempId,
              name: item.name,
              message:
                res.message ||
                'Unable to create rating curve.',
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

      await loadExistingRatingCurves(thingId)
    } catch (error: any) {
      generalError =
        error?.message || 'Unable to synchronize rating curve changes.'
    } finally {
      pendingCreates.value = pendingCreates.value.filter(
        (item) => !appliedCreateTempIds.has(item.tempId)
      )
      pendingMetadataUpdates.value = pendingMetadataUpdates.value.filter(
        (item) => !appliedMetadataUpdateIds.has(String(item.ratingCurveId))
      )
      pendingReplaces.value = pendingReplaces.value.filter(
        (item) => !appliedReplaceIds.has(String(item.ratingCurveId))
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
