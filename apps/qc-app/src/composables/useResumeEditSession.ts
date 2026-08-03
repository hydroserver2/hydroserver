/**
 * Reopen the editor after a page reload, from the last saved state:
 * `beginEditing` rebuilds the session and working copy from the server.
 *
 * The watcher must not use `once` with `immediate` — that fires on the
 * initial empty catalog and stops, which is the cold-reload case this
 * exists for. The flag gives once-only semantics without that trap.
 */

import { watch } from 'vue'
import { storeToRefs } from 'pinia'
import { Snackbar } from '@uwrl/qc-utils'
import { useDataVisStore } from '@/store/dataVisualization'
import { useQcSessionStore } from '@/store/qcSession'

export function useResumeEditSession(enterEdit: () => Promise<void>) {
  const dataVis = useDataVisStore()
  const { datastreams } = storeToRefs(dataVis)
  const { resumeDatastreamId } = storeToRefs(useQcSessionStore())

  let attempted = false

  /** Returns true when the editor was reopened. */
  async function resume(): Promise<boolean> {
    const id = resumeDatastreamId.value
    if (!id) return false
    const managed = datastreams.value.find((d) => d.id === id)
    if (!managed) {
      resumeDatastreamId.value = null
      return false
    }
    try {
      await dataVis.plotDatastream(managed)
      await dataVis.setQcDatastream(id)
      await enterEdit()
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
      resume().catch((e) => {
        Snackbar.error(
          e instanceof Error ? e.message : 'Could not reopen the edit session.'
        )
      })
    },
    { immediate: true }
  )

  return { resume }
}
