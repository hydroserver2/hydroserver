/* eslint-disable no-console */
import path from 'node:path'
import { generateContracts } from './generate-contracts.shared'

const SCHEMA_FILE = path.resolve('schemas/auth.openapi.json')
const OUT_DIR = path.resolve('src/generated/auth-contracts')

const resources = ['account', 'session']

generateContracts({
  schemaFile: SCHEMA_FILE,
  outDir: OUT_DIR,
  typesImportPath: '../auth.types',
  explicitResources: resources,
})
