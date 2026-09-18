/**
 * Reopen the editor after a page reload on the managed datastream it was last
 * open on. `resume` does the entering; this only waits for the catalog and
 * drops a pointer to a datastream that no longer exists.
 *
 * The watcher must not use `once` with `immediate`: that fires on the
 * initial empty catalog and stops, which is the cold-reload case this
 * exists for. The flag gives once-only semantics without that trap.
 */

import { watch } from 'vue'
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

  /** Returns true when the editor was reopened. */
  async function run(): Promise<boolean> {
    const id = resumeDatastreamId.value
    if (!id) return false
    if (!datastreams.value.some((d) => d.id === id)) {
      resumeDatastreamId.value = null
      return false
    }
    try {
      await resume(id)
      return true
    } catch (e) {
      resumeDatastreamId.value = null
      throw e
    }
  }

  watch(
    datastreams,
    (list) => {
      if (attempted || !list.length || !resumeDatastreamId.value) return
      attempted = true
      run().catch((e) => {
        Snackbar.error(
          e instanceof Error ? e.message : 'Could not reopen the edit session.'
        )
      })
    },
    { immediate: true }
  )

  return { resume: run }
}
