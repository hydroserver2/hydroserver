import { requestInterceptor, RequestOptions } from './requestInterceptor'
import { ApiResponse, responseInterceptor } from './responseInterceptor'
import { createPatchObject } from './createPatchObject'
import pLimit from 'p-limit'

const limit = pLimit(10)
const DEFAULT_PAGE_SIZE = 200

async function interceptedFetch<T>(
  endpoint: string,
  options: RequestOptions
): Promise<ApiResponse<T>> {
  const opts = requestInterceptor(options)
  const response = await fetch(endpoint, opts)
  return await responseInterceptor<T>(response)
}

export const apiMethods = {
  async fetch<T = unknown>(
    endpoint: string,
    options: RequestOptions = {}
  ): Promise<ApiResponse<T>> {
    options.method = 'GET'
    return await limit(() => interceptedFetch<T>(endpoint, options))
  },
  async patch<T = unknown>(
    endpoint: string,
    body: unknown,
    originalBody: unknown = null,
    options: RequestOptions = {}
  ): Promise<ApiResponse<T>> {
    options.method = 'PATCH'
    options.body = originalBody
      ? createPatchObject(
          originalBody as Record<string, unknown>,
          body as Record<string, unknown>
        )
      : body
    const bodyIsEmpty =
      typeof options.body === 'object' &&
      options.body !== null &&
      Object.keys(options.body).length === 0

    if (!options.body || bodyIsEmpty) {
      return {
        ok: true,
        data: (originalBody ?? null) as T,
        status: 204,
        message: 'No changes',
      }
    }
    return await limit(() => interceptedFetch<T>(endpoint, options))
  },
  async post<T = unknown>(
    endpoint: string,
    body: unknown = undefined,
    options: RequestOptions = {}
  ): Promise<ApiResponse<T>> {
    options.method = 'POST'
    options.body = body
    return await limit(() => interceptedFetch<T>(endpoint, options))
  },
  async put<T = unknown>(
    endpoint: string,
    body: unknown = undefined,
    options: RequestOptions = {}
  ): Promise<ApiResponse<T>> {
    options.method = 'PUT'
    options.body = body
    return await limit(() => interceptedFetch<T>(endpoint, options))
  },
  async delete<T = unknown>(
    endpoint: string,
    body: unknown = undefined,
    options: RequestOptions = {}
  ): Promise<ApiResponse<T>> {
    options.method = 'DELETE'
    options.body = body
    return await limit(() => interceptedFetch<T>(endpoint, options))
  },

  async paginatedFetch<T>(base: string): Promise<ApiResponse<T>> {
    const url = new URL(String(base), globalThis.location?.origin ?? undefined)
    const urlAlreadyHasPage = url.searchParams.has('page')
    if (!urlAlreadyHasPage) url.searchParams.set('page', '1')

    if (!url.searchParams.has('page_size'))
      url.searchParams.set('page_size', String(DEFAULT_PAGE_SIZE))

    const opts = requestInterceptor({ method: 'GET' })

    // fetch first page without response interceptor so we can read headers
    const firstResponse = await limit(() => fetch(url, opts))
    const totalPages = Number(firstResponse.headers.get('X-Total-Pages')) || 1
    const res = await responseInterceptor<T>(firstResponse)

    // If the caller explicitly asked for a single page, return it as-is
    if (urlAlreadyHasPage) return res

    // Errors carry no `data` to merge; surface them to the caller unchanged.
    if (!res.ok) return res

    type Columnar = Record<string, unknown>
    const isColumnar = (x: unknown): x is Columnar =>
      !!x && typeof x === 'object' && !Array.isArray(x)

    const concatInto = (target: Columnar, src: Columnar) => {
      for (const [k, v] of Object.entries(src)) {
        if (Array.isArray(v)) {
          if (!Array.isArray(target[k])) target[k] = []
          ;(target[k] as unknown[]).push(...v)
        } else if (target[k] === undefined) {
          // keep scalar metadata (e.g., units) from the first page only
          target[k] = v
        }
      }
    }

    // Normalize first page
    let mode: 'array' | 'columnar'
    let allArray: T[] = []
    let allColumnar: Columnar | null = null

    if (Array.isArray(res.data)) {
      mode = 'array'
      allArray = [...(res.data as T[])]
    } else if (isColumnar(res.data)) {
      mode = 'columnar'
      allColumnar = {}
      concatInto(allColumnar, res.data as Columnar)
    } else {
      return res // unknown shape, don’t attempt to paginate
    }

    // Fetch remaining pages concurrently (bounded by the shared `limit`) and merge in page order.
    // Each page gets its own URL so the requests don't share mutable searchParams state.
    const remainingPages = await Promise.all(
      Array.from({ length: Math.max(totalPages - 1, 0) }, (_, index) => {
        const pageUrl = new URL(url)
        pageUrl.searchParams.set('page', String(index + 2))
        return limit(() =>
          interceptedFetch<unknown>(pageUrl.toString(), { method: 'GET' })
        )
      })
    )

    for (const page of remainingPages) {
      // A failed page has no data; stop merging to avoid silent gaps.
      if (!page.ok) break
      if (mode === 'array') {
        if (Array.isArray(page.data)) {
          allArray.push(...(page.data as T[]))
        } else if (isColumnar(page.data) && Array.isArray(page.data.results)) {
          // some endpoints expose { results: [] }
          allArray.push(...(page.data.results as T[]))
        } else {
          // mixed shapes across pages — stop merging to avoid corrupting data
          break
        }
      } else {
        if (isColumnar(page.data)) {
          concatInto(allColumnar!, page.data as Columnar)
        } else if (Array.isArray(page.data)) {
          // if a later page comes back as a plain array, tuck it under `results`
          if (!Array.isArray(allColumnar!.results)) allColumnar!.results = []
          ;(allColumnar!.results as unknown[]).push(...page.data)
        } else {
          break
        }
      }
    }

    const merged =
      mode === 'array'
        ? (allArray as unknown as T)
        : (allColumnar as unknown as T)

    return {
      ok: true,
      data: merged,
      status: res.status,
      message: res.message,
      meta: res.meta,
    }
  },
}
