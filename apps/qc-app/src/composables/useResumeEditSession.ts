/**
 * Reopen the editor after a page reload on the managed datastream it was last
 * open on. `resume` does the entering; this only waits for the catalog and
 * drops a pointer to a datastream that no longer exists.
 * Not a `once` watcher: with `immediate` it fires on the empty catalog at
 * mount and stops.
 */

import { ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { Snackbar } from '@uwrl/qc-utils'
import { useDataVisStore } from '@/store/dataVisualization'
import { useQcSessionStore } from '@/store/qcSession'

export function useResumeEditSession(
  resume: (managedId: string) => Promise<void>
) {
  const { datastreams } = storeToRefs(useDataVisStore())
  const { resumeDatastreamId } = storeToRefs(useQcSessionStore())

  let attempted = false
  /** True once the resume finished or there was nothing to resume. */
  const settled = ref(false)

  async function run(): Promise<void> {
    const id = resumeDatastreamId.value
    if (!id) return
    if (!datastreams.value.some((d) => d.id === id)) {
      resumeDatastreamId.value = null
      return
    }
    try {
      await resume(id)
    } catch (e) {
      resumeDatastreamId.value = null
      throw e
    }
  }

  // The chance to resume closes as soon as the catalog lands: a pointer set
  // after that belongs to an entry that is already navigating on its own, and
  // a later catalog refresh (a commit rewrites the managed datastream) must
  // not re-enter behind the user.
  watch(
    datastreams,
    (list) => {
      if (attempted || !list.length) return
      attempted = true
      if (!resumeDatastreamId.value) {
        settled.value = true
        return
      }
      run()
        .catch((e) => {
          Snackbar.error(
            e instanceof Error ? e.message : 'Could not reopen the edit session.'
          )
        })
        .finally(() => {
          settled.value = true
        })
    },
    { immediate: true }
  )

  return { settled }
}
