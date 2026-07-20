import { getCSRFToken } from './getCSRFToken'

export interface RequestOptions extends Omit<RequestInit, 'body'> {
  body?: unknown
}

function isBodyInit(value: unknown): value is BodyInit {
  if (typeof value === 'string') return true
  if (typeof FormData !== 'undefined' && value instanceof FormData) return true
  if (typeof Blob !== 'undefined' && value instanceof Blob) return true
  if (
    typeof URLSearchParams !== 'undefined' &&
    value instanceof URLSearchParams
  )
    return true
  if (typeof ReadableStream !== 'undefined' && value instanceof ReadableStream)
    return true
  if (value instanceof ArrayBuffer) return true
  if (ArrayBuffer.isView(value)) return true

  return false
}

/**
 * Intercepts and enhances a request options object.
 *
 * - Adds CSRF Token header when available
 * - If a body is present and it's an object, the body is stringified.
 */
export function requestInterceptor(options: RequestOptions): RequestInit {
  const headers = new Headers(options.headers)

  let body: BodyInit | undefined = undefined
  if (options.body !== undefined) {
    body = isBodyInit(options.body)
      ? options.body
      : JSON.stringify(options.body)
  }

  headers.set('X-CSRFToken', getCSRFToken() || '')

  return {
    ...options,
    headers,
    body,
    credentials: 'include',
  }
}
