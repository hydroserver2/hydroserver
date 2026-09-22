/**
 * Create processing levels from inside the QC app so operators don't have to
 * leave for the Data Management app just to add one. Creation is workspace
 * scoped to the active workspace; the caller is responsible for adding the
 * returned level to the catalog it renders.
 */

import { storeToRefs } from 'pinia'
import { ProcessingLevel } from '@hydroserver/client'
import { useHydroServer } from '@/store/hydroserver'
import { useWorkspaceStore } from '@/store/workspaces'

export interface NewProcessingLevelInput {
  code: string
  definition?: string
  explanation?: string
}

export function useProcessingLevels() {
  const { hs } = storeToRefs(useHydroServer())
  const { selectedWorkspaceId } = storeToRefs(useWorkspaceStore())

  /** Create a processing level in the active workspace. Throws on failure. */
  async function createProcessingLevel(
    input: NewProcessingLevelInput
  ): Promise<ProcessingLevel> {
    const workspaceId = selectedWorkspaceId.value
    if (!workspaceId) {
      throw new Error('Select a workspace before adding a processing level.')
    }
    const body = Object.assign(new ProcessingLevel(), {
      workspaceId,
      code: input.code,
      definition: input.definition ?? '',
      explanation: input.explanation ?? '',
    })
    const res = await hs.value.processingLevels.create(body)
    if (!res.ok || !res.data) {
      throw new Error(res.message || 'Could not create the processing level.')
    }
    return res.data
  }

  return { createProcessingLevel }
}
