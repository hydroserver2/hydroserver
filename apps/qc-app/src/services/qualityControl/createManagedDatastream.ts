/**
 * Orchestrates creating a managed datastream for QC editing:
 *   1. create an empty managed datastream from the source's metadata, with
 *      a new processing level,
 *   2. create the QC history linking source and managed.
 *
 * Pure (deps injected) so it unit-tests without Pinia/Vuetify; a thin
 * composable wires it to the live HydroServer client and stores.
 */

import type {
  Datastream,
  DatastreamExtended,
  HydroServer,
  QualityControlHistory,
  QualityControlHistoryService,
} from '@hydroserver/client'
import { unwrap } from './unwrap'

export interface CreateManagedDatastreamInput {
  /** Source datastream to derive the managed datastream from. */
  source: Datastream
  /** Processing level for the new managed datastream (must differ from source). */
  processingLevelId: string
  /** Optional metadata overrides (e.g. name, description). */
  overrides?: Partial<Datastream>
}

export interface CreateManagedDatastreamResult {
  /** Expanded shape, so it can be appended to the data-vis catalog as-is. */
  managedDatastream: Datastream & DatastreamExtended
  history: QualityControlHistory
}

/**
 * Extract flat FK ids from a datastream that may be the `expand_related`
 * (nested objects) shape rather than the bare flat model. Datastreams in the
 * data-vis store are loaded expanded, so the flat `*Id` fields are absent.
 */
function flatDatastreamIds(source: Datastream) {
  const s = source as Datastream & Partial<DatastreamExtended>
  return {
    workspaceId: s.workspaceId ?? s.workspace?.id ?? '',
    monitoringSiteId: s.monitoringSiteId ?? s.monitoringSite?.id ?? '',
    unitId: s.unitId ?? s.unit?.id ?? '',
    observedPropertyId: s.observedPropertyId ?? s.observedProperty?.id ?? '',
    methodId: s.methodId ?? s.method?.id ?? '',
    processingLevelId: s.processingLevelId ?? s.processingLevel?.id ?? '',
  }
}

/**
 * Build the datastream create body: copy the source's metadata, start
 * empty (no observations), and apply the new processing level. The id is
 * cleared so the server assigns one.
 */
export function buildManagedDatastreamBody(
  source: Datastream,
  processingLevelId: string,
  overrides: Partial<Datastream> = {}
): Datastream {
  return {
    ...source,
    id: '',
    ...flatDatastreamIds(source),
    processingLevelId,
    valueCount: 0,
    phenomenonBeginTime: null,
    phenomenonEndTime: null,
    ...overrides,
  } as Datastream
}

export async function createManagedDatastream(
  hs: HydroServer,
  qcHistories: QualityControlHistoryService,
  input: CreateManagedDatastreamInput
): Promise<CreateManagedDatastreamResult> {
  const { source, processingLevelId, overrides } = input

  if (!processingLevelId) {
    throw new Error('A processing level is required for the managed datastream.')
  }
  if (processingLevelId === flatDatastreamIds(source).processingLevelId) {
    throw new Error(
      'The managed datastream must use a different processing level than the source.'
    )
  }

  const body = buildManagedDatastreamBody(source, processingLevelId, overrides)
  // Read back with `expand_related`: the data-vis catalog this datastream
  // joins carries the nested relations.
  const response = await hs.datastreams.create(body, { expand_related: true })
  if (!response.ok) {
    throw new Error(
      `Datastream creation failed (HTTP ${response.status}): ${
        response.message || 'the backend returned no datastream id'
      }`
    )
  }
  // The SDK types every read as the flat model; `expand_related` above is
  // what actually makes the nested relations present.
  const managedDatastream = response.data as Datastream & DatastreamExtended
  if (!managedDatastream?.id) {
    throw new Error(
      'Datastream creation failed: the backend returned no datastream id.'
    )
  }

  // The API answers a create with the new id; read the history back for the rest.
  const { id: historyId } = unwrap(
    await qcHistories.create({
      managedDatastreamId: managedDatastream.id,
      sourceDatastreamId: source.id,
    })
  )
  const history = unwrap(await qcHistories.get(historyId))

  return { managedDatastream, history }
}
