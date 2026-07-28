/** Field-level validation errors, keyed by field name. */
export type FieldErrors = Record<string, string[]>

/**
 * Envelope metadata optionally returned alongside `data`. Untyped so the
 * shape can evolve without breaking the client.
 */
export interface Meta {
  [key: string]: unknown
}

// TODO: Return FieldErrors in the error case so the backend can be the one source of truth for the error message
export type ApiResponse<T> =
  | { ok: true; status: number; data: T; message?: string; meta?: Meta }
  | { ok: false; status: number; message: string; data?: unknown }

function asRecord(value: unknown): Record<string, unknown> | null {
  return value && typeof value === 'object' && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null
}

function firstStringField(
  obj: Record<string, unknown>,
  keys: readonly string[]
): string | null {
  for (const key of keys) {
    const val = obj[key]
    if (typeof val === 'string' && val.trim()) return val
  }
  return null
}

export function extractErrorMessage(body: unknown): string {
  let cursor = body
  const record = asRecord(cursor)
  if (record && Array.isArray(record.errors) && record.errors.length) {
    cursor = record.errors[0]
  }

  const target = asRecord(cursor)
  if (!target) return 'An unknown error occurred.'

  return (
    firstStringField(target, ['message', 'detail', 'error']) ??
    'An unknown error occurred.'
  )
}

function extractSuccessMessage(body: unknown, response: Response): string {
  const record = asRecord(body)
  if (record) {
    const message = firstStringField(record, ['message', 'detail'])
    if (message) return message
  }
  // Fallback to HTTP status text or "OK"
  return response.statusText || 'OK'
}

export async function responseInterceptor<T = unknown>(
  response: Response
): Promise<ApiResponse<T>> {
  const contentType = response.headers.get('content-type') || ''
  const noBody =
    response.headers.get('Content-Length') === '0' ||
    response.statusText === 'No Content'

  let body: unknown = null
  if (!noBody) {
    try {
      if (contentType.includes('application/json')) {
        body = await response.json()
      } else if (
        contentType.includes('text/csv') ||
        contentType.includes('application/octet-stream')
      ) {
        body = await response.blob()
      } else {
        body = await response.text().catch(() => null)
      }
    } catch {
      body = null
    }
  }

  if (response.ok) {
    const record = asRecord(body)
    const looksEnveloped =
      record !== null && ('data' in record || 'meta' in record)

    const data = (looksEnveloped ? record!.data : body) as T
    const message = extractSuccessMessage(body, response)
    const meta = looksEnveloped ? (record!.meta as Meta | undefined) : undefined

    return { ok: true, data, status: response.status, message, meta }
  }

  // Error path
  return {
    ok: false,
    status: response.status,
    message: extractErrorMessage(body),
    data: body,
  }
}
