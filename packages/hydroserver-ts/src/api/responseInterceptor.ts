export interface ApiResponse<T = any> {
  data: T
  status: number
  message: string
  meta?: any
  ok: boolean
}

export function extractErrorMessage(body: any) {
  if (Array.isArray(body?.errors) && body.errors.length) {
    body = body.errors[0]
  }

  if (typeof body !== 'object' || body === null)
    return 'An unknown error occurred.'

  const possibleKeys = ['message', 'detail', 'error']
  for (const key of possibleKeys) {
    if (body[key]) return body[key]
  }

  return 'An unknown error occurred.'
}

function extractSuccessMessage(body: any, response: Response): string {
  if (typeof body?.message === 'string' && body.message.trim())
    return body.message

  if (body && typeof body === 'object' && !Array.isArray(body)) {
    const possibleKeys = ['message', 'detail']
    for (const key of possibleKeys) {
      const val = (body as any)[key]
      if (typeof val === 'string' && val.trim()) return val
    }
  }
  // Fallback to HTTP status text or "OK"
  return response.statusText || 'OK'
}

export async function responseInterceptor<T = any>(
  response: Response
): Promise<ApiResponse<T>> {
  const contentType = response.headers.get('content-type') || ''
  const noBody =
    response.headers.get('Content-Length') === '0' ||
    response.statusText === 'No Content'

  let body: any = null
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

  // Django AllAuth doesn't consider 401 responses errors but rather an
  // message to put the caller in an unauthenticated flow state.
  // Pass the response to the calling component to handle the returned AllAuth flows.

  // TODO: Clients and frontend apps shouldn't have to know anything about Django. Move AllAuth logic to the server
  if (response.ok || response.status === 401) {
    const looksEnveloped =
      body &&
      typeof body === 'object' &&
      !Array.isArray(body) &&
      ('data' in body || 'meta' in body)

    const data = (looksEnveloped ? body.data : body) as T
    const message = extractSuccessMessage(body, response)
    const meta = looksEnveloped ? body.meta : undefined

    return { data, status: response.status, message, meta, ok: true }
  }

  // Error path
  return {
    data: body as T,
    status: response.status,
    message: extractErrorMessage(body),
    ok: false,
  }
}
