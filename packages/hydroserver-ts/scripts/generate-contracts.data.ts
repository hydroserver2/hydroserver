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
  'etl-data-connections',
  'etl-tasks',
  'runs',
  'etl-orchestration-systems',
]

generateContracts({
  schemaFile: SCHEMA_FILE,
  outDir: OUT_DIR,
  typesImportPath: '../data.types',
  explicitResources: resources,
})
