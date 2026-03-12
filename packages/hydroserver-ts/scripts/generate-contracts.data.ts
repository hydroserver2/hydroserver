/* eslint-disable no-console */
import path from 'node:path'
import { generateContracts } from './generate-contracts.shared'

const SCHEMA_FILE = path.resolve('schemas/data.openapi.json')
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
