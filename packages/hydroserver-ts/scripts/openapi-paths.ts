import path from 'node:path'

export const OPENAPI_DIR = path.resolve('../../django/contracts/openapi')
export const DATA_OPENAPI_FILE = path.join(OPENAPI_DIR, 'data.openapi.json')
export const AUTH_OPENAPI_FILE = path.join(OPENAPI_DIR, 'auth.openapi.json')
