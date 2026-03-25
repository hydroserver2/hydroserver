/* eslint-disable no-console */
import path from 'node:path'
import { generateContracts } from './generate-contracts.shared'
import { AUTH_OPENAPI_FILE } from './openapi-paths'

const SCHEMA_FILE = AUTH_OPENAPI_FILE
const OUT_DIR = path.resolve('src/generated/auth-contracts')

const resources = ['account']

generateContracts({
  schemaFile: SCHEMA_FILE,
  outDir: OUT_DIR,
  typesImportPath: '../auth.types',
  explicitResources: resources,
})
