/**
 * Orchestrates creating a managed datastream for QC editing (spec section 5):
 *   1. create an empty managed datastream from the source's metadata, with
 *      a new processing level,
 *   2. create the QC history linking source and managed,
 *   3. tag the source datastream so the app can mark it read-only.
 *
 * Pure (deps injected) so it unit-tests without Pinia/Vuetify; a thin
 * composable wires it to the live HydroServer client and stores.
 */

import type {
  Datastream,
  DatastreamExtended,
  HydroServer,
  QualityControlHistoryService,
  QualityControlHistoryContract,
} from '@hydroserver/client'
import { unwrap } from './unwrap'

type QcHistoryDetail = QualityControlHistoryContract.DetailResponse

/** Tag key placed on a source datastream, pointing at its managed datastream. */
export const SOURCE_TAG_KEY = 'qc-managed-datastream'

export interface CreateManagedDatastreamInput {
  /** Source datastream to derive the managed datastream from. */
  source: Datastream
  /** Processing level for the new managed datastream (must differ from source). */
  processingLevelId: string
  /** Optional metadata overrides (e.g. name, description). */
  overrides?: Partial<Datastream>
}

export interface CreateManagedDatastreamResult {
  managedDatastream: Datastream
  history: QcHistoryDetail
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
    thingId: s.thingId ?? s.thing?.id ?? '',
    unitId: s.unitId ?? s.unit?.id ?? '',
    observedPropertyId: s.observedPropertyId ?? s.observedProperty?.id ?? '',
    sensorId: s.sensorId ?? s.sensor?.id ?? '',
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
  const response = await hs.datastreams.create(body)
  if (!response.ok) {
    throw new Error(
      `Datastream creation failed (HTTP ${response.status}): ${
        response.message || 'the backend returned no datastream id'
      }`
    )
  }
  const managedDatastream = response.data
  if (!managedDatastream?.id) {
    throw new Error(
      'Datastream creation failed: the backend returned no datastream id.'
    )
  }

  const history = unwrap(
    await qcHistories.create({
      managedDatastreamId: managedDatastream.id,
      sourceDatastreamId: source.id,
    })
  )

  await hs.datastreams.createTag(source.id, {
    key: SOURCE_TAG_KEY,
    value: managedDatastream.id,
  })

  return { managedDatastream, history }
}
