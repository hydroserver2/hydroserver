import type { HydroServer } from '../HydroServer'
import { apiMethods } from '../apiMethods'
import type { ApiResponse } from '../responseInterceptor'
import {
  normalizeAttachmentCollection,
  normalizeAttachmentRecord,
} from './attachment-link'

export const RATING_CURVE_ATTACHMENT_TYPE = 'rating_curve'

export interface ThingFileAttachment {
  id: string | number
  name: string
  description: string
  link: string
  fileAttachmentType: string
}

export type ThingFileAttachmentListParams = {
  page?: number | null
  page_size?: number | null
  type?: string | string[]
}

export type UploadThingFileAttachmentOptions = {
  type?: string
  name?: string
  description?: string
}

export type ThingFileAttachmentPatchBody = {
  name?: string
  description?: string
}

export interface RatingCurvePreviewRow {
  inputValue: string
  outputValue: string
}

export class ThingFileAttachmentService {
  private readonly _client: HydroServer

  constructor(client: HydroServer) {
    this._client = client
  }

  async list(thingId: string, params: ThingFileAttachmentListParams = {}) {
    const url = this.withQuery(this.baseAttachmentRoute(thingId), params)
    const res = (await apiMethods.paginatedFetch(url)) as ApiResponse<
      ThingFileAttachment[]
    >
    return {
      ...res,
      data: normalizeAttachmentCollection(
        res.data,
        this._client.host
      ) as ThingFileAttachment[],
    }
  }

  async listItems(thingId: string, params: ThingFileAttachmentListParams = {}) {
    const res = await this.list(thingId, params)
    return res.ok && Array.isArray(res.data) ? res.data : []
  }

  async upload(
    thingId: string,
    file: File | Blob,
    options: UploadThingFileAttachmentOptions = {}
  ) {
    const data = new FormData()
    data.append('file', file, file instanceof File ? file.name : 'attachment.csv')
    data.append('file_attachment_type', options.type ?? RATING_CURVE_ATTACHMENT_TYPE)
    if (options.name) data.append('name', options.name)
    if (options.description) data.append('description', options.description)

    const res = (await apiMethods.post(
      this.baseAttachmentRoute(thingId),
      data
    )) as ApiResponse<ThingFileAttachment>
    return {
      ...res,
      data: normalizeAttachmentRecord(
        res.data,
        this._client.host
      ) as ThingFileAttachment,
    }
  }

  async update(
    thingId: string,
    fileAttachmentId: string | number,
    body: ThingFileAttachmentPatchBody,
    originalBody?: ThingFileAttachmentPatchBody
  ) {
    const url = `${this.baseAttachmentRoute(thingId)}/${fileAttachmentId}`
    const res = (await apiMethods.patch(
      url,
      body,
      originalBody ?? null
    )) as ApiResponse<ThingFileAttachment>
    return {
      ...res,
      data: normalizeAttachmentRecord(
        res.data,
        this._client.host
      ) as ThingFileAttachment,
    }
  }

  async replaceFile(
    thingId: string,
    fileAttachmentId: string | number,
    file: File | Blob
  ) {
    const url = `${this.baseAttachmentRoute(thingId)}/${fileAttachmentId}/file`
    const makeData = () => {
      const data = new FormData()
      data.append('file', file, file instanceof File ? file.name : 'attachment.csv')
      return data
    }

    // Prefer POST for multipart file replace; some backend stacks do not
    // reliably parse multipart payloads on PUT.
    let res = (await apiMethods.post(url, makeData())) as ApiResponse<ThingFileAttachment>
    if (!res.ok && (res.status === 404 || res.status === 405)) {
      res = (await apiMethods.put(url, makeData())) as ApiResponse<ThingFileAttachment>
    }

    return {
      ...res,
      data: normalizeAttachmentRecord(
        res.data,
        this._client.host
      ) as ThingFileAttachment,
    }
  }

  delete(thingId: string, fileAttachmentId: string | number) {
    const url = `${this.baseAttachmentRoute(thingId)}/${fileAttachmentId}`
    return apiMethods.delete(url)
  }

  async fetchRatingCurvePreview(
    link: string,
    maxRows = 20
  ): Promise<ApiResponse<RatingCurvePreviewRow[]>> {
    if (!`${link ?? ''}`.trim()) {
      return {
        data: [],
        status: 0,
        message: 'Missing rating curve file link.',
        ok: false,
      }
    }

    const fetchOptions = {
      headers: {
        Accept: 'text/csv, text/plain, application/octet-stream, application/json',
      },
    }

    const previewUrls = this.resolveAttachmentPreviewUrls(link)
    let firstNonOkResponse: ApiResponse | null = null
    let fallbackOkResponse: ApiResponse | null = null
    let fallbackRows: RatingCurvePreviewRow[] = []
    let onlyHtmlLikePayloads = true

    for (const previewUrl of previewUrls) {
      try {
        const candidate = await apiMethods.fetch(previewUrl, fetchOptions)
        if (!candidate.ok) {
          firstNonOkResponse ??= candidate
          continue
        }

        const csvText = await this.resolveCsvText(candidate.data, fetchOptions)
        const rows = parsePreviewRows(csvText, maxRows)
        const isHtmlPayload = looksLikeHtmlPayload(csvText)
        if (!isHtmlPayload) {
          onlyHtmlLikePayloads = false
        }

        if (rows.length > 0) {
          return {
            data: rows,
            status: candidate.status,
            message: candidate.message,
            meta: candidate.meta,
            ok: true,
          }
        }

        if (!isHtmlPayload && rows.length >= fallbackRows.length) {
          fallbackRows = rows
          fallbackOkResponse = candidate
        }
      } catch {
        // try the next URL candidate
      }
    }

    if (fallbackOkResponse) {
      return {
        data: fallbackRows,
        status: fallbackOkResponse.status,
        message: fallbackOkResponse.message,
        meta: fallbackOkResponse.meta,
        ok: true,
      }
    }

    if (onlyHtmlLikePayloads && previewUrls.length > 0) {
      return {
        data: [],
        status: 0,
        message: 'Unable to load rating curve preview.',
        ok: false,
      }
    }

    if (firstNonOkResponse) {
      return { ...firstNonOkResponse, data: [] }
    }

    return {
      data: [],
      status: 0,
      message: 'Unable to load preview.',
      ok: false,
    }
  }

  private async resolveCsvText(
    raw: unknown,
    fetchOptions: { headers: { Accept: string } }
  ) {
    let csvText = await normalizeCsvText(raw)
    const followupUrl = extractFollowupUrl(raw)
    if (!followupUrl) {
      return csvText
    }

    for (const candidateUrl of this.resolveAttachmentPreviewUrls(followupUrl)) {
      try {
        const followedResponse = await apiMethods.fetch(candidateUrl, fetchOptions)
        if (followedResponse.ok) {
          csvText = await normalizeCsvText(followedResponse.data)
          if (csvText.trim()) break
        }
      } catch {
        // keep trying candidate URLs
      }
    }

    return csvText
  }

  private baseAttachmentRoute(thingId: string) {
    return `${this._client.baseRoute}/things/${thingId}/file-attachments`
  }

  private resolveAttachmentPreviewUrls(link: string) {
    const urls: string[] = []
    try {
      const parsed = new URL(link, globalThis.location?.origin ?? undefined)

      if (isThingAttachmentDownloadPath(parsed.pathname)) {
        const pathAndQuery = `${parsed.pathname}${parsed.search}`

        const hostOrigin = this.hostOrigin()
        if (hostOrigin) {
          urls.push(new URL(pathAndQuery, hostOrigin).toString())
        }

        urls.push(parsed.toString())

        const locationOrigin = this.locationOrigin()
        if (locationOrigin) {
          urls.push(new URL(pathAndQuery, locationOrigin).toString())
        }
      } else {
        urls.push(parsed.toString())
      }
    } catch {
      urls.push(link)
    }

    return dedupe(urls)
  }

  private locationOrigin() {
    try {
      return globalThis.location?.origin ?? null
    } catch {
      return null
    }
  }

  private hostOrigin() {
    try {
      if (this._client.host) {
        return new URL(this._client.host, globalThis.location?.origin).origin
      }
    } catch {
      // no-op
    }

    return null
  }

  private withQuery(base: string, params?: ThingFileAttachmentListParams) {
    if (!params || Object.keys(params).length === 0) return base
    const url = new URL(base, globalThis.location?.origin ?? undefined)

    if (params.page !== undefined && params.page !== null) {
      url.searchParams.set('page', String(params.page))
    }
    if (params.page_size !== undefined && params.page_size !== null) {
      url.searchParams.set('page_size', String(params.page_size))
    }

    const type = params.type
    if (Array.isArray(type)) {
      for (const value of type) {
        if (value) url.searchParams.append('type', value)
      }
    } else if (typeof type === 'string' && type) {
      url.searchParams.set('type', type)
    }

    return url.toString()
  }
}

function isThingAttachmentDownloadPath(pathname: string) {
  return /^\/api\/data\/things\/[^/]+\/file-attachments\/[^/]+\/download\/?$/.test(
    pathname
  )
}

function parsePreviewRows(csvText: string, maxRows = 20): RatingCurvePreviewRow[] {
  const normalizedText = csvText.replace(/^\uFEFF/, '')
  const lines = normalizedText
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => !!line)

  if (lines.length < 1) return []

  const delimiter = detectDelimiter(lines)
  const firstColumns = splitCsvLine(lines[0], delimiter)
  const header = firstColumns.map(normalizeHeaderName)

  let inputIndex = header.findIndex((name) =>
    [
      'input_value',
      'input',
      'stage',
      'x',
      'independent',
      'lookup_col1',
      'lookupcol1',
    ].includes(name)
  )
  let outputIndex = header.findIndex((name) =>
    [
      'output_value',
      'output',
      'discharge',
      'y',
      'dependent',
      'lookup_col2',
      'lookupcol2',
    ].includes(name)
  )

  if (inputIndex === -1 || outputIndex === -1 || inputIndex === outputIndex) {
    // Common source format includes an identifier column first:
    // STATION_ID,LOOKUP_COL1,LOOKUP_COL2
    const hasLeadingIdentifierColumn =
      header.length >= 3 &&
      /(id|station|site|thing)/.test(header[0]) &&
      /(lookup|stage|input|x)/.test(header[1]) &&
      /(lookup|output|discharge|y)/.test(header[2])
    if (hasLeadingIdentifierColumn) {
      inputIndex = 1
      outputIndex = 2
    }
  }

  if (inputIndex === -1 || outputIndex === -1 || inputIndex === outputIndex) {
    inputIndex = 0
    outputIndex = 1
  }

  const firstIsData = tryGetNumericPair(firstColumns, inputIndex, outputIndex) !== null
  const startIndex = firstIsData ? 0 : 1

  const rows: RatingCurvePreviewRow[] = []
  for (const line of lines.slice(startIndex)) {
    const columns = splitCsvLine(line, delimiter)
    const pair = tryGetNumericPair(columns, inputIndex, outputIndex)
    if (!pair) continue

    rows.push({
      inputValue: String(pair.inputValue),
      outputValue: String(pair.outputValue),
    })

    if (rows.length >= maxRows) break
  }

  return rows
}

function detectDelimiter(lines: string[]) {
  const candidates: Array<',' | ';' | '\t'> = [',', ';', '\t']
  let best = candidates[0]
  let bestCount = -1

  for (const delimiter of candidates) {
    const count = lines
      .slice(0, 6)
      .reduce(
        (sum, line) => sum + countUnquotedDelimiterOccurrences(line, delimiter),
        0
      )
    if (count > bestCount) {
      best = delimiter
      bestCount = count
    }
  }

  return best
}

async function normalizeCsvText(raw: unknown) {
  if (raw instanceof Blob) {
    const buffer = await raw.arrayBuffer()
    return decodeCsvText(new Uint8Array(buffer))
  }
  if (typeof raw === 'string') return raw.replace(/\u0000/g, '')

  if (raw && typeof raw === 'object') {
    const typed = raw as Record<string, unknown>
    const inlineText =
      readStringField(typed, 'csv') ||
      readStringField(typed, 'text') ||
      readStringField(typed, 'content') ||
      readStringField(typed, 'data')
    if (inlineText) return inlineText.replace(/\u0000/g, '')
  }

  return raw == null ? '' : String(raw)
}

function decodeCsvText(bytes: Uint8Array) {
  if (bytes.length === 0) return ''
  if (bytes.length >= 2) {
    if (bytes[0] === 0xff && bytes[1] === 0xfe) {
      return new TextDecoder('utf-16le').decode(bytes).replace(/\u0000/g, '')
    }
    if (bytes[0] === 0xfe && bytes[1] === 0xff) {
      return new TextDecoder('utf-16be').decode(bytes).replace(/\u0000/g, '')
    }
  }

  const utf8 = new TextDecoder('utf-8').decode(bytes)
  if (!looksLikeInterleavedUtf16(utf8)) return utf8.replace(/\u0000/g, '')

  const utf16le = new TextDecoder('utf-16le').decode(bytes)
  const utf16be = new TextDecoder('utf-16be').decode(bytes)

  const candidates = [utf8, utf16le, utf16be]
  return candidates
    .sort((a, b) => scoreCsvLikeText(b) - scoreCsvLikeText(a))[0]
    .replace(/\u0000/g, '')
}

function looksLikeInterleavedUtf16(text: string) {
  if (!text.length) return false
  const nulls = (text.match(/\u0000/g) ?? []).length
  return nulls / text.length > 0.15
}

function scoreCsvLikeText(text: string) {
  if (!text) return 0
  const commas = (text.match(/,/g) ?? []).length
  const semicolons = (text.match(/;/g) ?? []).length
  const tabs = (text.match(/\t/g) ?? []).length
  const newlines = (text.match(/\n/g) ?? []).length
  const digits = (text.match(/\d/g) ?? []).length
  return commas + semicolons + tabs + newlines + digits * 0.05
}

function dedupe(values: string[]) {
  return [...new Set(values.filter((value) => !!value))]
}

function looksLikeHtmlPayload(text: string) {
  const normalized = `${text ?? ''}`.trim().toLowerCase()
  if (!normalized) return false

  return (
    normalized.startsWith('<!doctype html') ||
    normalized.startsWith('<html') ||
    (normalized.includes('<head') && normalized.includes('<body'))
  )
}

function extractFollowupUrl(raw: unknown) {
  if (!raw || typeof raw !== 'object') return ''
  const typed = raw as Record<string, unknown>
  return (
    readStringField(typed, 'url') ||
    readStringField(typed, 'download_url') ||
    readStringField(typed, 'downloadUrl') ||
    readStringField(typed, 'link') ||
    ''
  )
}

function readStringField(obj: Record<string, unknown>, key: string) {
  const value = obj[key]
  return typeof value === 'string' && value.trim() ? value.trim() : ''
}

function splitCsvLine(line: string, delimiter: string) {
  const columns: string[] = []
  let current = ''
  let inQuotes = false

  for (let i = 0; i < line.length; i += 1) {
    const char = line[i]

    if (char === '"') {
      if (inQuotes && line[i + 1] === '"') {
        current += '"'
        i += 1
        continue
      }
      inQuotes = !inQuotes
      continue
    }

    if (char === delimiter && !inQuotes) {
      columns.push(current.trim())
      current = ''
      continue
    }

    current += char
  }

  columns.push(current.trim())
  return columns.map((part) => part.replace(/^"|"$/g, ''))
}

function countUnquotedDelimiterOccurrences(line: string, delimiter: string) {
  let inQuotes = false
  let count = 0

  for (let i = 0; i < line.length; i += 1) {
    const char = line[i]
    if (char === '"') {
      if (inQuotes && line[i + 1] === '"') {
        i += 1
        continue
      }
      inQuotes = !inQuotes
      continue
    }
    if (char === delimiter && !inQuotes) count += 1
  }

  return count
}

function normalizeHeaderName(value: string) {
  return value
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_+|_+$/g, '')
}

function parseNumericValue(raw: string | undefined) {
  const source = `${raw ?? ''}`.trim()
  if (!source) return null

  const stripped = source.replace(/,/g, '')
  const direct = Number(stripped)
  if (Number.isFinite(direct)) return direct

  // Ignore labels (e.g., "LOOKUP_COL1") while still allowing values like "2.1 ft".
  if (!/^[-+]?(\d|\.\d)/.test(stripped)) return null

  const match = stripped.match(/[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?/)
  if (!match) return null

  const parsed = Number(match[0])
  return Number.isFinite(parsed) ? parsed : null
}

function tryGetNumericPair(
  columns: string[],
  inputIndex: number,
  outputIndex: number
) {
  if (Math.max(inputIndex, outputIndex) < columns.length) {
    const inputValue = parseNumericValue(columns[inputIndex])
    const outputValue = parseNumericValue(columns[outputIndex])
    if (inputValue !== null && outputValue !== null) {
      return { inputValue, outputValue }
    }
  }

  const numericValues = columns
    .map((value) => parseNumericValue(value))
    .filter((value): value is number => value !== null)

  if (numericValues.length >= 2) {
    return {
      inputValue: numericValues[0],
      outputValue: numericValues[1],
    }
  }

  return null
}
