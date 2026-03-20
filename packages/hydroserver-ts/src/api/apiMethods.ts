import { requestInterceptor } from './requestInterceptor'
import { ApiResponse, responseInterceptor } from './responseInterceptor'
import { createPatchObject } from './createPatchObject'
import pLimit from 'p-limit'

const limit = pLimit(10)
const DEFAULT_PAGE_SIZE = 1000

async function interceptedFetch(endpoint: string, options: any) {
  const opts = requestInterceptor(options)
  const response = await fetch(endpoint, opts)
  return await responseInterceptor(response)
}

export const apiMethods = {
  async fetch(endpoint: string, options: any = {}): Promise<ApiResponse> {
    options.method = 'GET'
    return await limit(() => interceptedFetch(endpoint, options))
  },
  async patch(
    endpoint: string,
    body: any,
    originalBody: any = null,
    options: any = {}
  ): Promise<ApiResponse> {
    options.method = 'PATCH'
    options.body = originalBody ? createPatchObject(originalBody, body) : body
    const bodyIsEmpty =
      typeof options.body === 'object' && Object.keys(options.body).length === 0

    if (!options.body || bodyIsEmpty) {
      return {
        data: originalBody ?? null,
        status: 204,
        message: 'No changes',
        ok: true,
      }
    }
    return await limit(() => interceptedFetch(endpoint, options))
  },
  async post(
    endpoint: string,
    body: any = undefined,
    options: any = {}
  ): Promise<ApiResponse> {
    options.method = 'POST'
    options.body = body
    return await limit(() => interceptedFetch(endpoint, options))
  },
  async put(
    endpoint: string,
    body: any = undefined,
    options: any = {}
  ): Promise<ApiResponse> {
    options.method = 'PUT'
    options.body = body
    return await limit(() => interceptedFetch(endpoint, options))
  },
  async delete(
    endpoint: string,
    body: any = undefined,
    options: any = {}
  ): Promise<ApiResponse> {
    options.method = 'DELETE'
    options.body = body
    return await limit(() => interceptedFetch(endpoint, options))
  },

  async paginatedFetch<T>(base: string): Promise<ApiResponse> {
    const url = new URL(String(base), globalThis.location?.origin ?? undefined)
    const urlAlreadyHasPage = url.searchParams.has('page')
    if (!urlAlreadyHasPage) url.searchParams.set('page', '1')

    if (!url.searchParams.has('page_size'))
      url.searchParams.set('page_size', String(DEFAULT_PAGE_SIZE))

    const opts = requestInterceptor({ method: 'GET' })

    // fetch first page without response interceptor so we can read headers
    const firstResponse = await limit(() => fetch(url, opts))
    const totalPages = Number(firstResponse.headers.get('X-Total-Pages')) || 1
    const res = await responseInterceptor(firstResponse)

    // If the caller explicitly asked for a single page, return it as-is
    if (urlAlreadyHasPage) return res

    type Columnar = Record<string, any>
    const isColumnar = (x: unknown): x is Columnar =>
      !!x && typeof x === 'object' && !Array.isArray(x)

    const concatInto = (target: Columnar, src: Columnar) => {
      for (const [k, v] of Object.entries(src)) {
        if (Array.isArray(v)) {
          if (!Array.isArray(target[k])) target[k] = []
          ;(target[k] as any[]).push(...v)
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

    // Fetch remaining pages and merge
    for (let p = 2; p <= totalPages; p++) {
      url.searchParams.set('page', String(p))
      const page = await limit(() =>
        interceptedFetch(url.toString(), { method: 'GET' })
      )

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
          ;(allColumnar!.results as any[]).push(...page.data)
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
      data: merged,
      status: res.status,
      message: res.message,
      meta: res.meta,
      ok: res.ok,
    }
  },
}
