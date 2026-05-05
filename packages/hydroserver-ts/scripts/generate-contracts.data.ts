/* eslint-disable no-console */
import path from 'node:path'
import { generateContracts } from './generate-contracts.shared'
import { DATA_OPENAPI_FILE } from './openapi-paths'

const SCHEMA_FILE = DATA_OPENAPI_FILE
const OUT_DIR = path.resolve('src/generated/contracts')

const resources = [
  'workspaces',
  'things',
  'datastreams',
  'units',
  'sensors',
  'observed-properties',
  'processing-levels',
  'result-qualifiers',
  'observations',

  // ETL
  'data-connections',
  'tasks',
  'runs',

  // Monitoring
  {
    resource: 'monitoring-tasks',
    pathSuffix: '/monitoring/tasks',
    route: 'tasks',
  },

  // Products
  {
    resource: 'data-product-tasks',
    pathSuffix: '/products/tasks',
    route: 'tasks',
  },
  'rating-curves',
]

generateContracts({
  schemaFile: SCHEMA_FILE,
  outDir: OUT_DIR,
  typesImportPath: '../data.types',
  explicitResources: resources,
})
