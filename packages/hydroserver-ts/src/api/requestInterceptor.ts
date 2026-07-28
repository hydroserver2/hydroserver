import { getCSRFToken } from './getCSRFToken'

type AccessTokenProvider = () => Promise<string | null>

let accessTokenProvider: AccessTokenProvider | null = null

export function registerAccessTokenProvider(
  provider: AccessTokenProvider | null
) {
  accessTokenProvider = provider
}

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
 * - Adds a CSRF header when a CSRF cookie is present (session auth)
 * - Adds a bearer token when an access token provider is registered (OIDC auth)
 * - If a body is present and it's an object, the body is stringified.
 */
export async function requestInterceptor(
  options: RequestOptions
): Promise<RequestInit> {
  const headers = new Headers(options.headers)

  let body: BodyInit | undefined = undefined
  if (options.body !== undefined) {
    body = isBodyInit(options.body)
      ? options.body
      : JSON.stringify(options.body)
  }

  const csrfToken = getCSRFToken()
  if (csrfToken) {
    headers.set('X-CSRFToken', csrfToken)
  }

  const accessToken = accessTokenProvider
    ? await accessTokenProvider().catch(() => null)
    : null

  if (accessToken) {
    headers.set('Authorization', `Bearer ${accessToken}`)
  }

  return {
    ...options,
    headers,
    body,
    credentials: 'include',
  }
}
