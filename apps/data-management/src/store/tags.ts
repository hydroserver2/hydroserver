import { defineStore } from 'pinia'
import { ref } from 'vue'
import hs, { getTagValue, Tags } from '@hydroserver/client'

export const useTagStore = defineStore('tags', () => {
  const tags = ref<Tags>({})
  const previewTags = ref<Tags>({})

  function buildTagsPatch(oldTags: Tags, newTags: Tags) {
    const patch: Record<string, string | null> = {}

    for (const [key, value] of Object.entries(newTags)) {
      if (getTagValue(oldTags, key) !== value) patch[key] = value
    }
    for (const key of Object.keys(oldTags)) {
      if (!Object.hasOwn(newTags, key)) patch[key] = null
    }

    return patch
  }

  const updateTags = async (monitoringSiteId: string) => {
    const patch = buildTagsPatch(tags.value, previewTags.value)
    if (Object.keys(patch).length === 0) {
      previewTags.value = {}
      return
    }

    try {
      const updated = await hs.monitoringSites.updateItem({
        id: monitoringSiteId,
        tags: patch as unknown as Tags,
      })
      tags.value = updated?.tags ?? {}
      previewTags.value = {}
    } catch (error) {
      console.error('Error updating tags', error)
    }
  }

  return {
    tags,
    previewTags,
    updateTags,
  }
})
