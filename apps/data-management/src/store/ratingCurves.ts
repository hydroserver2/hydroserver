import { defineStore } from 'pinia'
import { ref } from 'vue'
import hs, {
  RATING_CURVE_ATTACHMENT_TYPE,
  type RatingCurvePreviewRow,
  type ThingFileAttachment,
} from '@hydroserver/client'

export const EXISTING_RATING_CURVE_RENAME_MESSAGE =
  'Renaming existing rating curves is not supported. Create a new rating curve instead.'

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

type ReplaceExistingRatingCurveOptions = {
  thingId: string
  attachment: ThingFileAttachment
  description: string
  file?: File | Blob | null
}

type ReplaceExistingRatingCurveResult = {
  ok: boolean
  message: string
  data?: ThingFileAttachment
}

function getCsrfToken() {
  if (typeof document === 'undefined') return ''

  const decodedCookies = decodeURIComponent(document.cookie || '')
  for (const part of decodedCookies.split(';')) {
    const cookie = part.trim()
    if (cookie.startsWith('csrftoken=')) {
      return cookie.substring('csrftoken='.length)
    }
  }

  return ''
}

function toNamedUploadFile(file: File | Blob, name: string) {
  if (file instanceof File && file.name === name) {
    return file
  }

  return new File([file], name, {
    type: file.type || 'application/octet-stream',
    lastModified: file instanceof File ? file.lastModified : Date.now(),
  })
}

function extractResponseMessage(body: unknown, fallback: string) {
  if (!body) return fallback
  if (typeof body === 'string') return body.trim() || fallback
  if (typeof body !== 'object') return fallback

  const possibleKeys = ['message', 'detail', 'error']
  for (const key of possibleKeys) {
    const value = (body as Record<string, unknown>)[key]
    if (typeof value === 'string' && value.trim()) {
      return value
    }
  }

  const errors = (body as Record<string, unknown>).errors
  if (Array.isArray(errors) && errors.length > 0) {
    return extractResponseMessage(errors[0], fallback)
  }

  return fallback
}

async function readResponseBody(response: Response) {
  const contentType = response.headers.get('content-type') || ''
  if (contentType.includes('application/json')) {
    return response.json().catch(() => null)
  }

  return response.text().catch(() => '')
}

async function fetchExistingAttachmentBlob(attachment: ThingFileAttachment) {
  const response = await fetch(attachment.link, {
    method: 'GET',
    credentials: 'include',
    headers: {
      Accept: 'text/csv, text/plain, application/octet-stream',
    },
  })

  if (!response.ok) {
    const body = await readResponseBody(response)
    throw new Error(
      extractResponseMessage(body, 'Unable to load rating curve file.')
    )
  }

  return response.blob()
}

export async function replaceExistingRatingCurveAttachment({
  thingId,
  attachment,
  description,
  file,
}: ReplaceExistingRatingCurveOptions): Promise<ReplaceExistingRatingCurveResult> {
  const uploadFile = toNamedUploadFile(
    file ?? (await fetchExistingAttachmentBlob(attachment)),
    attachment.name
  )
  const formData = new FormData()
  formData.append('file', uploadFile, uploadFile.name)
  formData.append(
    'file_attachment_type',
    attachment.fileAttachmentType || RATING_CURVE_ATTACHMENT_TYPE
  )
  if (description) {
    formData.append('description', description)
  }

  const response = await fetch(`${hs.baseRoute}/things/${thingId}/file-attachments`, {
    method: 'PUT',
    body: formData,
    credentials: 'include',
    headers: {
      'X-CSRFToken': getCsrfToken(),
    },
  })
  const body = await readResponseBody(response)
  const message = extractResponseMessage(body, response.statusText || 'OK')

  if (!response.ok) {
    return {
      ok: false,
      message,
    }
  }

  const attachmentItems = await hs.thingFileAttachments.listItems(thingId, {
    type: RATING_CURVE_ATTACHMENT_TYPE,
  })
  const updatedAttachment =
    attachmentItems.find((item) => item.name === attachment.name) ?? attachment

  return {
    ok: true,
    message,
    data: updatedAttachment,
  }
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
    const metadataUpdatesById = new Map(
      pendingMetadataUpdates.value.map((item) => [String(item.attachmentId), item])
    )
    const replacesById = new Map(
      pendingReplaces.value.map((item) => [String(item.attachmentId), item])
    )

    try {
      if (pendingDeleteIds.value.length) {
        for (const id of pendingDeleteIds.value) {
          try {
            const attachment = existingRatingCurves.value.find(
              (item) => String(item.id) === String(id)
            )
            const res = attachment
              ? await hs.things.deleteAttachment(thingId, attachment.name)
              : await hs.thingFileAttachments.delete(thingId, id)
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
        const attachment = existingRatingCurves.value.find(
          (item) => String(item.id) === key
        )

        if (!attachment) {
          if (metadataUpdate) {
            failedMetadataUpdates.push({
              id: metadataUpdate.attachmentId,
              message: 'Unable to find rating curve attachment.',
            })
          }
          if (replace) {
            failedReplaces.push({
              id: replace.attachmentId,
              message: 'Unable to find rating curve attachment.',
            })
          }
          continue
        }

        if (metadataUpdate && metadataUpdate.name !== attachment.name) {
          failedMetadataUpdates.push({
            id: metadataUpdate.attachmentId,
            message: EXISTING_RATING_CURVE_RENAME_MESSAGE,
          })
          if (replace) {
            failedReplaces.push({
              id: replace.attachmentId,
              message: EXISTING_RATING_CURVE_RENAME_MESSAGE,
            })
          }
          continue
        }

        try {
          const res = await replaceExistingRatingCurveAttachment({
            thingId,
            attachment,
            description: metadataUpdate?.description ?? (attachment.description || ''),
            file: replace?.file,
          })

          if (!res.ok || !res.data) {
            if (metadataUpdate) {
              failedMetadataUpdates.push({
                id: metadataUpdate.attachmentId,
                message: res.message || 'Unable to update rating curve metadata.',
              })
            }
            if (replace) {
              failedReplaces.push({
                id: replace.attachmentId,
                message: res.message || 'Unable to replace rating curve file.',
              })
            }
            continue
          }

          if (metadataUpdate) appliedMetadataUpdateIds.add(key)
          if (replace) appliedReplaceIds.add(key)
        } catch (error: any) {
          if (metadataUpdate) {
            failedMetadataUpdates.push({
              id: metadataUpdate.attachmentId,
              message: error?.message || 'Unable to update rating curve metadata.',
            })
          }
          if (replace) {
            failedReplaces.push({
              id: replace.attachmentId,
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
