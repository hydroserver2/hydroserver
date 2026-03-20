/* eslint-disable no-console */
import fs from 'node:fs'
import path from 'node:path'

export type OAS = {
  paths: Record<string, any>
  components?: {
    schemas?: Record<string, any>
    responses?: Record<string, any>
    requestBodies?: Record<string, any>
  }
}

export type GenerateContractsOptions = {
  schemaFile: string
  outDir: string
  typesImportPath: string
  explicitResources?: string[]
}

/* ----------------------------- utils ----------------------------- */

function toPascalCase(resource: string): string {
  return resource
    .split('-')
    .map((seg) => seg.charAt(0).toUpperCase() + seg.slice(1))
    .join('')
}

/** singularize only the last kebab segment: "observed-properties" -> "observed-property" */
function singularizeKebab(resource: string): string {
  const parts = resource.split('-')
  const last = parts.pop() || ''
  let singular = last
  if (last.endsWith('ies')) singular = last.slice(0, -3) + 'y'
  else if (last.endsWith('s') && !last.endsWith('ss'))
    singular = last.slice(0, -1)
  parts.push(singular)
  return parts.join('-')
}

/** "#/components/schemas/Thing" -> "Data.components['schemas']['Thing']" */
function refName(ref?: string): string | null {
  if (!ref) return null
  const name = ref.split('/').pop()
  return name ? `Data.components['schemas']['${name}']` : null
}

function schemaExists(spec: OAS, schemaName: string): boolean {
  return Boolean(spec.components?.schemas?.[schemaName])
}

function toDataRef(schemaName: string): string {
  return `Data.components['schemas']['${schemaName}']`
}

function derefResponse(spec: OAS, ref: string) {
  const name = ref.split('/').pop()
  return name ? spec.components?.responses?.[name] ?? null : null
}
function derefRequestBody(spec: OAS, ref: string) {
  const name = ref.split('/').pop()
  return name ? spec.components?.requestBodies?.[name] ?? null : null
}

function findJsonSchemaFromContent(content?: any) {
  if (!content || typeof content !== 'object') return undefined
  const key =
    Object.keys(content).find((k) => k.toLowerCase().includes('json')) ??
    Object.keys(content)[0]
  return key ? content[key]?.schema : undefined
}

/** Prefer 200; fall back to first 2xx response. */
function getResponseSchema(spec: OAS, op: any) {
  if (!op || !op.responses) return undefined
  let entry =
    op.responses['200'] ??
    Object.entries(op.responses).find(([code]) => {
      const n = Number(code)
      return Number.isFinite(n) && n >= 200 && n < 300
    })?.[1]
  if (!entry) return undefined
  if (entry.$ref) entry = derefResponse(spec, entry.$ref) ?? entry
  return findJsonSchemaFromContent(entry?.content)
}

function getRequestSchema(spec: OAS, op: any) {
  if (!op || !op.requestBody) return undefined
  let rb = op.requestBody
  if (rb.$ref) rb = derefRequestBody(spec, rb.$ref) ?? rb
  return findJsonSchemaFromContent(rb?.content)
}

function getOperationQueryType(op: any): string | null {
  const operationId = op?.operationId
  if (typeof operationId !== 'string' || operationId.trim().length === 0) {
    return null
  }

  return `([Data.operations['${operationId}']['parameters']['query']] extends [never] ? {} : NonNullable<Data.operations['${operationId}']['parameters']['query']>)`
}

/* ---------------------- deep ref discovery ---------------------- */

function derefSchema(spec: OAS, schema: any, seen = new Set<any>()) {
  if (!schema || typeof schema !== 'object') return schema
  if (seen.has(schema)) return schema
  seen.add(schema)
  if (schema.$ref) {
    const rn = refName(schema.$ref)
    const name = rn?.match(/Data\.components\['schemas'\]\['(.+)'\]/)?.[1]
    const target = name ? spec.components?.schemas?.[name] : null
    return target ? derefSchema(spec, target, seen) : schema
  }
  return schema
}

/** DFS collect all schema $refs in a subtree */
function collectAllRefsDeep(
  spec: OAS,
  node: any,
  out: string[],
  seen = new Set<any>()
) {
  const s = derefSchema(spec, node, seen)
  if (!s || typeof s !== 'object') return

  if (s.$ref) {
    const rn = refName(s.$ref)
    if (rn) out.push(rn)
  }

  if (s.items) collectAllRefsDeep(spec, s.items, out, seen)
  if (s.additionalProperties)
    collectAllRefsDeep(spec, s.additionalProperties, out, seen)

  if (s.properties && typeof s.properties === 'object') {
    for (const v of Object.values<any>(s.properties)) {
      collectAllRefsDeep(spec, v, out, seen)
    }
  }

  for (const key of ['allOf', 'oneOf', 'anyOf'] as const) {
    if (Array.isArray(s[key]))
      for (const x of s[key]) collectAllRefsDeep(spec, x, out, seen)
  }
}

/** Choose a ref by name constraints: mustContain (e.g., "Workspace"), then preferRegex (e.g., /SummaryResponse$/) */
function pickRefByName(
  refs: string[],
  mustContain: string,
  preferRegex: RegExp
): string | null {
  const toName = (r: string) =>
    r.match(/Data\.components\['schemas'\]\['(.+)'\]/)?.[1] ?? ''
  let candidates = refs.filter((r) => toName(r).includes(mustContain))
  if (!candidates.length) candidates = refs // fallback: nothing matched token

  const preferred = candidates.find((r) => preferRegex.test(toName(r)))
  return preferred ?? candidates[0] ?? null
}

/* ----------------------- writable keys ------------------------- */

function gatherObjectProps(
  spec: OAS,
  schema: any,
  props: Record<string, any>,
  seen = new Set<any>()
) {
  const s = derefSchema(spec, schema, seen)
  if (!s || typeof s !== 'object') return
  if (s.type === 'object' && s.properties) {
    for (const [k, v] of Object.entries<any>(s.properties)) {
      if (v?.readOnly) continue
      props[k] = v
    }
  }
  for (const key of ['allOf', 'oneOf', 'anyOf'] as const) {
    if (Array.isArray(s[key])) {
      for (const part of s[key]) gatherObjectProps(spec, part, props, seen)
    }
  }
}

function extractWritableKeys(spec: OAS, schema: any): string[] {
  if (!schema) return []
  const props: Record<string, any> = {}
  gatherObjectProps(spec, schema, props)
  return Object.keys(props)
}

/* ----------------------- resource analysis --------------------- */

function analyzeResource(spec: OAS, resource: string) {
  const collectionPath = Object.keys(spec.paths).find((p) =>
    p.endsWith(`/${resource}`)
  )
  if (!collectionPath) return null

  const itemPath = Object.keys(spec.paths).find((p) =>
    p.startsWith(collectionPath + '/{')
  )
  const colPathObj = spec.paths[collectionPath] || {}
  const itemPathObj = itemPath ? spec.paths[itemPath] : {}

  const singular = singularizeKebab(resource)
  const pascalSingular = toPascalCase(singular)

  // 1) Strong exact-name preference if components exist
  const summaryName = `${pascalSingular}SummaryResponse`
  const detailName = `${pascalSingular}DetailResponse`
  const summaryByExact = schemaExists(spec, summaryName)
    ? toDataRef(summaryName)
    : null
  const detailByExact = schemaExists(spec, detailName)
    ? toDataRef(detailName)
    : null

  // 2) Otherwise, derive from responses but constrain by resource token
  const colGetSchema = getResponseSchema(spec, colPathObj.get)
  const itemGetSchema = getResponseSchema(spec, itemPathObj.get)

  let summaryRef: string | null = summaryByExact
  let detailRef: string | null = detailByExact

  if (!summaryRef) {
    // array -> items direct
    const s = derefSchema(spec, colGetSchema)
    if (s?.type === 'array' && s.items?.$ref) {
      summaryRef = refName(s.items.$ref)
    }
    if (!summaryRef) {
      const refs: string[] = []
      collectAllRefsDeep(spec, colGetSchema, refs)
      const uniq = Array.from(new Set(refs))
      summaryRef = pickRefByName(uniq, pascalSingular, /Summary(Response)?$/i)
    }
  }

  if (!detailRef) {
    const s = derefSchema(spec, itemGetSchema)
    if (s?.$ref) detailRef = refName(s.$ref)
    if (!detailRef) {
      const refs: string[] = []
      collectAllRefsDeep(spec, itemGetSchema ?? colGetSchema, refs)
      const uniq = Array.from(new Set(refs))
      detailRef = pickRefByName(uniq, pascalSingular, /Detail(Response)?$/i)
    }
  }

  // Bodies
  const postReqSchema = getRequestSchema(spec, colPathObj.post)
  const patchReqSchema = getRequestSchema(
    spec,
    itemPathObj.patch ?? colPathObj.patch
  )
  const deleteReqSchema = getRequestSchema(
    spec,
    itemPathObj.delete ?? colPathObj.delete
  )

  const postRef = postReqSchema?.$ref ? refName(postReqSchema.$ref) : null
  const patchRef = patchReqSchema?.$ref ? refName(patchReqSchema.$ref) : null
  const deleteRef = deleteReqSchema?.$ref ? refName(deleteReqSchema.$ref) : null

  const PostBody = postRef ?? null
  const PatchBody = patchRef ?? (postRef ? `Partial<${postRef}>` : null)
  const DeleteBody = deleteRef ?? null

  const candidateForWritable = patchReqSchema ?? postReqSchema ?? null
  const writableKeys = extractWritableKeys(spec, candidateForWritable)

  // Prefer operation-level query type to preserve true optionality from the endpoint.
  const operationQueryType = getOperationQueryType(colPathObj.get)

  // Fallback: QueryParameters → <Singular>QueryParameters if present
  const qpName = `${pascalSingular}QueryParameters`
  const queryType =
    operationQueryType ??
    (schemaExists(spec, qpName) ? toDataRef(qpName) : `{}`)

  return {
    summaryRef,
    detailRef,
    PostBody,
    PatchBody,
    DeleteBody,
    writableKeys,
    queryType,
  }
}

/* -------------------------- generator -------------------------- */

export function generateContracts(opts: GenerateContractsOptions) {
  const SCHEMA_FILE = path.resolve(opts.schemaFile)
  const OUT_DIR = path.resolve(opts.outDir)
  fs.mkdirSync(OUT_DIR, { recursive: true })

  // Clean stale contracts
  for (const f of fs.readdirSync(OUT_DIR)) {
    if (f.endsWith('.contract.ts')) fs.unlinkSync(path.join(OUT_DIR, f))
  }

  const spec: OAS = JSON.parse(fs.readFileSync(SCHEMA_FILE, 'utf8'))
  const resources =
    opts.explicitResources && opts.explicitResources.length > 0
      ? opts.explicitResources
      : inferResourcesFromPaths(spec)

  const header = `/* AUTO-GENERATED. DO NOT EDIT.
   Generated from ${path.relative(process.cwd(), SCHEMA_FILE)} */
import type * as Data from '${opts.typesImportPath}'
`

  const written: string[] = []

  for (const resource of resources) {
    const analyzed = analyzeResource(spec, resource)
    if (!analyzed) {
      console.warn(`Skipping ${resource}: could not analyze from OpenAPI`)
      continue
    }

    const singularRes = singularizeKebab(resource)
    const ns = `${toPascalCase(singularRes)}Contract`

    const {
      summaryRef,
      detailRef,
      PostBody,
      PatchBody,
      DeleteBody,
      writableKeys,
      queryType,
    } = analyzed

    const SummaryResponse = summaryRef ?? 'never'
    const DetailResponse = detailRef ?? 'never'
    const PostBodyType = PostBody ?? 'never'
    const PatchBodyType = PatchBody ?? 'never'
    const DeleteBodyType = DeleteBody ?? 'never'

    const lines: string[] = []
    lines.push(`export namespace ${ns} {`)
    lines.push(`  export const route = '${resource}' as const`)
    lines.push(`  export type QueryParameters = ${queryType}`)
    lines.push(`  export type SummaryResponse = ${SummaryResponse}`)
    lines.push(`  export type DetailResponse  = ${DetailResponse}`)
    lines.push(`  export type PostBody        = ${PostBodyType}`)
    lines.push(`  export type PatchBody       = ${PatchBodyType}`)
    lines.push(`  export type DeleteBody      = ${DeleteBodyType}`)
    lines.push(
      `  export const writableKeys = ${JSON.stringify(writableKeys)} as const`
    )
    lines.push(`  export declare const __types: {`)
    lines.push(`    SummaryResponse: SummaryResponse`)
    lines.push(`    DetailResponse: DetailResponse`)
    lines.push(`    PostBody: PostBody`)
    lines.push(`    PatchBody: PatchBody`)
    lines.push(`    DeleteBody: DeleteBody`)
    lines.push(`    QueryParameters: QueryParameters`)
    lines.push(`  }`)
    lines.push(`}`)

    const ts = `${header}\n${lines.join('\n')}\n`
    const fileBase = `${resource}.contract.ts`
    const outFile = path.join(OUT_DIR, fileBase)
    fs.writeFileSync(outFile, ts, 'utf8')
    written.push(fileBase)
    console.log('✅ wrote', path.relative(process.cwd(), outFile))
  }

  const index =
    written
      .map((f) => {
        const resource = f.replace('.contract.ts', '')
        const ns = `${toPascalCase(singularizeKebab(resource))}Contract`
        const base = f.replace('.ts', '')
        return `export { ${ns} } from './${base}'`
      })
      .join('\n') + '\n'

  fs.writeFileSync(path.join(OUT_DIR, 'index.ts'), index, 'utf8')
  console.log('Contracts generated.')
}

/* -------------------------- helpers ---------------------------- */

function inferResourcesFromPaths(spec: OAS): string[] {
  const set = new Set<string>()
  for (const p of Object.keys(spec.paths)) {
    const seg = p.split('/').filter(Boolean).pop()
    if (!seg) continue
    if (seg.startsWith('{') && seg.endsWith('}')) continue
    set.add(seg)
  }
  return Array.from(set).sort()
}
