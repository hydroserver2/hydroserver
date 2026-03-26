type AccessTokenProvider = () => Promise<string | null>

let accessTokenProvider: AccessTokenProvider | null = null

export function registerAccessTokenProvider(
  provider: AccessTokenProvider | null
) {
  accessTokenProvider = provider
}

/**
 * Intercepts and enhances a request options object.
 *
 * - Adds a bearer token when available
 * - If a body is present and it's an object, the body is stringified.
 *
 * @param {any} options - The original request options object.
 *
 * @returns {any} The enhanced request options with possible modified headers and body.
 */
export async function requestInterceptor(options: any) {
  const headers = options.headers ? { ...options.headers } : {}

  let body: string | FormData | undefined = undefined
  if (options.body !== undefined) {
    body =
      typeof options.body === 'string' || options.body instanceof FormData
        ? options.body
        : JSON.stringify(options.body)
  }

  const accessToken = accessTokenProvider
    ? await accessTokenProvider().catch(() => null)
    : null

  if (accessToken) {
    headers.Authorization = `Bearer ${accessToken}`
  }

  return {
    ...options,
    headers,
    body,
  }
}
