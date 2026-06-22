/**
 * Wires the "Create Datastream for Editing" flow to the live stores:
 * delegates to the tested `createManagedDatastream` orchestration with the
 * HydroServer client and the QC history service.
 */

import { storeToRefs } from 'pinia'
import type { Datastream } from '@hydroserver/client'
import { useHydroServer } from '@/store/hydroserver'
import {
  createManagedDatastream,
  type CreateManagedDatastreamResult,
} from '@/services/qualityControl'

export interface CreateManagedDatastreamSpec {
  source: Datastream
  processingLevelId: string
  name?: string
}

export function useCreateManagedDatastream() {
  const { hs } = storeToRefs(useHydroServer())

  async function create(
    spec: CreateManagedDatastreamSpec
  ): Promise<CreateManagedDatastreamResult> {
    return createManagedDatastream(hs.value, hs.value.qualityControlHistories, {
      source: spec.source,
      processingLevelId: spec.processingLevelId,
      overrides: spec.name ? { name: spec.name } : undefined,
    })
  }

  return { create }
}
