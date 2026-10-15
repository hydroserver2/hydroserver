/**
 * The managed datastream the editor was last open on, kept across reloads.
 * A store of its own because persisting `qcSession` would deep-watch its
 * sessions and saved edits on every change (see `qcPreferences`).
 */

import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useEditResumeStore = defineStore(
  'editResume',
  () => {
    const resumeDatastreamId = ref<string | null>(null)
    return { resumeDatastreamId }
  },
  { persist: { key: 'qc:editResume:v1' } }
)
