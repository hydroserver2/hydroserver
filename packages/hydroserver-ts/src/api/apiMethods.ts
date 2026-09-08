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
  const opts = await requestInterceptor(options)
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
    const isFormData = typeof FormData !== 'undefined' && body instanceof FormData
    
    options.method = 'PATCH'
    options.body = isFormData
      ? body
      : originalBody
        ? createPatchObject(
            originalBody as Record<string, unknown>,
            body as Record<string, unknown>
          )
        : body

    const bodyIsEmpty =
      !isFormData &&
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
    const urlAlreadyHasOffset = url.searchParams.has('offset')
    if (!urlAlreadyHasOffset) url.searchParams.set('offset', '0')

    if (!url.searchParams.has('limit'))
      url.searchParams.set('limit', String(DEFAULT_PAGE_SIZE))
    const limitParam = Number(url.searchParams.get('limit')) || DEFAULT_PAGE_SIZE

    const res = await interceptedFetch<T>(url.toString(), { method: 'GET' })

    // If the caller explicitly asked for a specific offset, return it as-is
    if (urlAlreadyHasOffset) return res

    // Errors carry no `data` to merge; surface them to the caller unchanged.
    if (!res.ok) return res

    type Columnar = Record<string, unknown>
    const isColumnar = (x: unknown): x is Columnar =>
      !!x && typeof x === 'object' && !Array.isArray(x)

    const concatInto = (target: Columnar, src: Columnar) => {
      for (const [k, v] of Object.entries(src)) {
        if (k === 'meta') continue
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
    let firstPageMeta = res.meta as Record<string, unknown> | undefined

    if (Array.isArray(res.data)) {
      mode = 'array'
      allArray = [...(res.data as T[])]
    } else if (isColumnar(res.data)) {
      mode = 'columnar'
      const raw = res.data as Columnar
      if (!firstPageMeta && isColumnar(raw.meta))
        firstPageMeta = raw.meta as Record<string, unknown>
      allColumnar = {}
      concatInto(allColumnar, raw)
    } else {
      return res // unknown shape, don’t attempt to paginate
    }

    const totalCount =
      typeof firstPageMeta?.totalCount === 'number'
        ? firstPageMeta.totalCount
        : undefined

    const offsets: number[] = []
    if (totalCount !== undefined) {
      for (let offset = limitParam; offset < totalCount; offset += limitParam) {
        offsets.push(offset)
      }
    }

    const remainingPages = await Promise.all(
      offsets.map((offset) => {
        const pageUrl = new URL(url)
        pageUrl.searchParams.set('offset', String(offset))
        return limit(() =>
          interceptedFetch<unknown>(pageUrl.toString(), { method: 'GET' })
        )
      })
    )

    for (const page of remainingPages) {
      // Never report a partial multi-page result as successful. Callers use
      // `ok` to decide whether a management table is complete and actionable.
      if (!page.ok) return page
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

    const mergedCount =
      mode === 'array'
        ? allArray.length
        : ((Object.values(allColumnar!).find(Array.isArray) as
            | unknown[]
            | undefined)?.length ?? 0)

    return {
      ok: true,
      data: merged,
      status: res.status,
      message: res.message,
      meta: {
        ...(firstPageMeta ?? {}),
        offset: 0,
        limit: mergedCount,
        totalCount: totalCount ?? mergedCount,
      },
    }
  },
}
