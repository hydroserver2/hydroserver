import { defineStore } from 'pinia'
import { ref } from 'vue'
import hs, { Tag } from '@hydroserver/client'

export const useTagStore = defineStore('tags', () => {
  const tags = ref<Tag[]>([])
  const previewTags = ref<Tag[]>([])

  function findTagChanges(oldTags: Tag[], newTags: Tag[]) {
    const tagsToEdit = newTags.filter((nt) =>
      oldTags.some((ot) => nt.key === ot.key && nt.value !== ot.value)
    )

    const tagsToDelete = oldTags.filter(
      (ot) => !newTags.some((nt) => nt.key === ot.key)
    )

    const tagsToAdd = newTags.filter(
      (nt) => !oldTags.some((ot) => ot.key === nt.key)
    )

    return [tagsToEdit, tagsToDelete, tagsToAdd]
  }

  const updateTags = async (thingId: string) => {
    try {
      const [tagsToEdit, tagsToDelete, tagsToAdd] = findTagChanges(
        tags.value,
        previewTags.value
      )

      const requests = [
        ...tagsToAdd.map((tag) => hs.things.createTag(thingId, tag)),
        ...tagsToEdit.map((tag) => hs.things.updateTag(thingId, tag)),
        ...tagsToDelete.map((tag) => hs.things.deleteTag(thingId, tag)),
      ]

      await Promise.all(requests)

      const res = await hs.things.getTags(thingId)
      tags.value = res.data
      previewTags.value = []
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
