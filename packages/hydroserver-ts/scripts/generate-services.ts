/* eslint-disable no-console */
import fs from 'node:fs'
import path from 'node:path'

type OAS = {
  servers?: any[]
  paths: Record<string, any>
  components?: { schemas?: Record<string, any> }
}

const ROOT = process.cwd()
const SCHEMA_FILE = path.resolve('schemas/data.openapi.json')
const OUT_DIR = path.resolve('src/generated/services')
fs.mkdirSync(OUT_DIR, { recursive: true })

const spec: OAS = JSON.parse(fs.readFileSync(SCHEMA_FILE, 'utf8'))

/** kebab to Pascal: observed-properties -> ObservedProperties */
const toPascal = (s: string) =>
  s
    .split('-')
    .map((x) => x[0]?.toUpperCase() + x.slice(1))
    .join('')

/** singularize the last segment: observed-properties -> observed-property */
function singularizeKebab(resource: string): string {
  const parts = resource.split('-')
  const last = parts.pop() || ''
  let sg = last
  if (last.endsWith('ies')) sg = last.slice(0, -3) + 'y'
  else if (last.endsWith('s') && !last.endsWith('ss')) sg = last.slice(0, -1)
  parts.push(sg)
  return parts.join('-')
}

/** camelCase a space/kebab string */
const toCamel = (s: string) =>
  s
    .replace(/[-_\s]+(.)?/g, (_, c) => (c ? c.toUpperCase() : ''))
    .replace(/^(.)/, (m) => m.toLowerCase())

/** Return "/api/data/<resource>" path root if present */
function findCollectionRoot(resource: string) {
  const key = Object.keys(spec.paths).find((p) => p.endsWith(`/${resource}`))
  return key || null
}

/** Is canonical CRUD? These are on base class; don’t generate dupes. */
function isCanonicalCrud(
  resource: string,
  pathKey: string,
  verb: string
): boolean {
  const root = findCollectionRoot(resource)
  if (!root) return false
  // list/create on collection root
  if (pathKey === root && (verb === 'get' || verb === 'post')) return true
  // item id path: /{root}/{id}
  if (pathKey.startsWith(root + '/{')) {
    if (
      verb === 'get' ||
      verb === 'patch' ||
      verb === 'put' ||
      verb === 'delete'
    )
      return true
  }
  return false
}

/** Try getting an opId; if absent, derive a nice short name */
function makeMethodName(
  pathKey: string,
  verb: string,
  resource: string,
  opId?: string
) {
  if (opId) {
    // Trim resource prefixes/suffixes & http verbs from opIds to shorten them
    const cleaned = opId
      .replace(/^api_/i, '')
      .replace(/_view[s]?_/i, '_')
      .replace(
        new RegExp(`(^|_)${resource.replace(/-/g, '_')}(?=_|$)`, 'i'),
        '$1'
      )
      .replace(
        /^(get|list|create|update|delete|put|post|patch|regenerate)_/i,
        ''
      )
      .replace(/_/g, ' ')
    return toCamel((verbAlias(verb) + ' ' + cleaned).trim())
  }

  const root = findCollectionRoot(resource) || ''
  const local = pathKey.replace(new RegExp(`^${root}/?`), '')
  const segs = local
    .split('/')
    .filter(Boolean)
    .filter((s) => !/^{.+}$/.test(s))
  const tail = segs[segs.length - 1] || ''
  const singularTail = singularizeKebab(tail || resource)

  // action tails
  if (
    /regenerate|trigger|reset|start|stop|bulk-create|bulk-delete/i.test(tail)
  ) {
    return toCamel(`${tail} ${singularTail}`)
  }

  // general derivation
  if (verb === 'get')
    return toCamel(segs.length ? `list ${singularTail}` : 'list')
  if (verb === 'post') return toCamel(`create ${singularTail}`)
  if (verb === 'put') return toCamel(`update ${singularTail}`)
  if (verb === 'patch') return toCamel(`update ${singularTail}`)
  if (verb === 'delete') return toCamel(`delete ${singularTail}`)
  return toCamel(`${verb} ${singularTail}`)
}

function verbAlias(v: string) {
  if (v === 'get') return 'get'
  if (v === 'post') return 'create'
  if (v === 'put' || v === 'patch') return 'update'
  if (v === 'delete') return 'delete'
  return v
}

/** Build a method signature using openapi-typescript’s Data.paths typing */
function buildMethod(
  resource: string,
  pathKey: string,
  verb: 'get' | 'post' | 'put' | 'patch' | 'delete',
  operation: any
) {
  const methodName = makeMethodName(
    pathKey,
    verb,
    resource,
    operation?.operationId
  )
  const pathLiteral = JSON.stringify(pathKey)
  const base = `Data.paths[${pathLiteral}]['${verb}']`
  const hasPath = !!operation?.parameters?.some((p: any) => p.in === 'path')
  const hasQuery = !!operation?.parameters?.some((p: any) => p.in === 'query')
  const hasBody = !!operation?.requestBody

  // arg list
  const pathParams = (operation?.parameters || [])
    .filter((p: any) => p.in === 'path')
    .map((p: any) => p.name)

  const args: string[] = []
  for (const p of pathParams) args.push(`${p}: string`)
  if (hasQuery) args.push(`query?: ${base}['parameters']['query']`)
  if (hasBody)
    args.push(`body?: ${base}['requestBody']['content']['application/json']`)

  // response type
  const resType =
    `${base}['responses']['200']['content']['application/json']` +
    ` | ${base}['responses']['201'] extends infer _T ? _T extends { content: any } ? _T['content']['application/json'] : never : never`

  // URL builder from template (fast and safe)
  const tmpl = pathKey.replace(/{/g, '${').replace(/}/g, '}')
  const urlExpr = '`' + tmpl + '`'

  // query merge
  const addQuery = hasQuery
    ? `
    if (query) {
      const u = new URL(url, globalThis.location?.origin ?? undefined)
      Object.entries(query as Record<string, any>).forEach(([k,v]) => v !== undefined && u.searchParams.set(k,String(v)))
      url = u.toString()
    }`
    : ''

  const bodyLine = hasBody ? ', body' : ''

  return `
  async ${methodName}(${args.join(', ')}): Promise<ApiResponse<${resType}>> {
    let url = ${urlExpr}
    ${addQuery}
    return apiMethods.${verb}(url${bodyLine}) as Promise<ApiResponse<${resType}>>
  }`
}

// resources you already emit contracts for (keep in sync with contracts generator)
const resources = [
  'workspaces',
  'things',
  'datastreams',
  'units',
  'sensors',
  'observed-properties',
  'processing-levels',
  'result-qualifiers',
  'orchestration-systems',
  'data-sources',
  'data-archives',
]

const header = `/* AUTO-GENERATED. DO NOT EDIT.
   Generated from ${path.relative(ROOT, SCHEMA_FILE)} */
import type { ApiResponse } from '../../api/responseInterceptor'
import { apiMethods } from '../../api/apiMethods'
import type { HydroServer } from '../../api/HydroServer'
import type * as Data from '../data.types'
import { ${resources
  .map((r) => `${toPascal(singularizeKebab(r))}Contract`)
  .join(', ')} } from '../contracts'
import { HydroServerBaseService } from '../../api/services/base'
`

for (const resource of resources) {
  const nsName = `${toPascal(singularizeKebab(resource))}Contract`
  const className = `${toPascal(singularizeKebab(resource))}ServiceBase`

  // collect non-CRUD endpoints for this resource
  const colRoot = Object.keys(spec.paths).find((p) =>
    p.endsWith(`/${resource}`)
  )
  const myPaths = Object.entries(spec.paths).filter(([p]) =>
    colRoot
      ? p === colRoot || p.startsWith(colRoot + '/')
      : p.endsWith(`/${resource}`)
  )

  const methodBlocks: string[] = []

  for (const [pathKey, pathObj] of myPaths) {
    for (const verb of ['get', 'post', 'put', 'patch', 'delete'] as const) {
      const op = pathObj[verb]
      if (!op) continue
      if (isCanonicalCrud(resource, pathKey, verb)) continue
      methodBlocks.push(buildMethod(resource, pathKey, verb, op))
    }
  }

  const body = `${header}

export class ${className} extends HydroServerBaseService<typeof ${nsName}> {
  static route = ${nsName}.route
  constructor(client: HydroServer) { super(client) }
${methodBlocks.join('\n')}
}
`

  const outFile = path.join(OUT_DIR, `${resource}.service.base.ts`)
  fs.writeFileSync(outFile, body, 'utf8')
  console.log('✅ wrote', path.relative(ROOT, outFile))

  // Ensure a user sugar file exists (don’t overwrite)
  const sugarDir = path.resolve('src/api/services')
  fs.mkdirSync(sugarDir, { recursive: true })
  const sugarName = `${singularizeKebab(resource)}.service.ts`
  const sugarPath = path.join(sugarDir, sugarName)
  if (!fs.existsSync(sugarPath)) {
    const sugar = `// Hand-written sugar for ${resource}. Safe from codegen.
import type { HydroServer } from '../HydroServer'
import { ${className} } from '../../generated/services/${resource}.service.base'

export class ${toPascal(
      singularizeKebab(resource)
    )}Service extends ${className} {
  // Add your sugar here, e.g.:
  // async myShortcut(...) { return this.someGeneratedMethod(...) }
}
`
    fs.writeFileSync(sugarPath, sugar, 'utf8')
    console.log('📝 created sugar stub', path.relative(ROOT, sugarPath))
  }
}

// Barrel for generated bases
const index =
  resources.map((r) => `export * from './${r}.service.base'`).join('\n') + '\n'
fs.writeFileSync(path.join(OUT_DIR, 'index.ts'), index, 'utf8')
console.log('Services generated.')
