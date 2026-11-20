/* eslint-disable no-console */
import path from 'node:path'
import { generateContracts } from './generate-contracts.shared'
import { OGC_OPENAPI_FILE } from './openapi-paths'

const SCHEMA_FILE = OGC_OPENAPI_FILE
const OUT_DIR = path.resolve('src/generated/contracts')

/** An OGC API collection: list/create at /collections/{id}/items, items at /items/{itemId}. */
const collection = (collectionId: string, resource = collectionId) => ({
  resource,
  pathSuffix: `/collections/${collectionId}/items`,
  route: `collections/${collectionId}/items`,
})

const QC_HISTORY_ITEM = 'collections/quality-control-histories/items/{history_id}'

const resources = [
  collection('workspaces'),
  collection('monitoring-sites'),
  collection('monitoring-site-types'),
  collection('linked-resource-types'),
  collection('datastreams'),
  collection('datastream-statuses'),
  collection('aggregation-statistics'),
  collection('units'),
  collection('unit-types'),
  collection('methods'),
  collection('method-types'),
  collection('observed-properties'),
  collection('observed-property-types'),
  collection('processing-levels'),
  collection('result-qualifiers'),
  collection('sampled-mediums'),
  collection('observations'),

  // ETL
  collection('etl-data-connections', 'data-connections'),
  collection('etl-tasks', 'tasks'),
  'runs',
  collection('etl-mappings'),

  // Monitoring
  collection('monitoring-tasks'),
  collection('monitoring-rules'),

  // Products
  collection('data-product-tasks'),
  collection('data-product-rating-curves', 'rating-curves'),
  collection('data-product-transformations'),

  // Quality control
  collection('quality-control-histories'),
  {
    resource: 'quality-control-sessions',
    pathSuffix: `/${QC_HISTORY_ITEM}/sessions`,
    route: `${QC_HISTORY_ITEM}/sessions`,
  },
  {
    resource: 'quality-control-operations',
    pathSuffix: `/${QC_HISTORY_ITEM}/sessions/{session_id}/operations`,
    route: `${QC_HISTORY_ITEM}/sessions/{session_id}/operations`,
  },
]

generateContracts({
  schemaFile: SCHEMA_FILE,
  outDir: OUT_DIR,
  typesImportPath: '../ogc.types',
  explicitResources: resources,
})
