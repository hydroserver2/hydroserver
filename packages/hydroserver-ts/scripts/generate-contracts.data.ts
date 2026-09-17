/* eslint-disable no-console */
import path from 'node:path'
import { generateContracts } from './generate-contracts.shared'
import { DATA_OPENAPI_FILE } from './openapi-paths'

const SCHEMA_FILE = DATA_OPENAPI_FILE
const OUT_DIR = path.resolve('src/generated/contracts')

const resources = [
  'workspaces',
  'monitoring-sites',
  'datastreams',
  'units',
  'methods',
  'observed-properties',
  'processing-levels',
  'result-qualifiers',
  'observations',

  // ETL
  {
    resource: 'data-connections',
    pathSuffix: '/etl-data-connections',
    route: 'etl-data-connections',
  },
  {
    resource: 'tasks',
    pathSuffix: '/etl-tasks',
    route: 'etl-tasks',
  },
  'runs',
  'etl-mappings',

  // Monitoring
  {
    resource: 'monitoring-tasks',
    pathSuffix: '/monitoring-tasks',
    route: 'monitoring-tasks',
  },
  'monitoring-rules',

  // Products
  {
    resource: 'data-product-tasks',
    pathSuffix: '/data-product-tasks',
    route: 'data-product-tasks',
  },
  {
    resource: 'rating-curves',
    pathSuffix: '/data-product-rating-curves',
    route: 'data-product-rating-curves',
  },
  'data-product-transformations',

  // Quality control
  {
    resource: 'quality-control-histories',
    pathSuffix: '/quality-control/histories',
    route: 'quality-control/histories',
  },
  {
    resource: 'quality-control-sessions',
    pathSuffix: '/quality-control/histories/{history_id}/sessions',
    route: 'quality-control/histories/{history_id}/sessions',
  },
  {
    resource: 'quality-control-operations',
    pathSuffix:
      '/quality-control/histories/{history_id}/sessions/{session_id}/operations',
    route:
      'quality-control/histories/{history_id}/sessions/{session_id}/operations',
  },
]

generateContracts({
  schemaFile: SCHEMA_FILE,
  outDir: OUT_DIR,
  typesImportPath: '../data.types',
  explicitResources: resources,
})
