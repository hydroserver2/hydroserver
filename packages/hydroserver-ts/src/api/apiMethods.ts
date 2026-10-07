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
    const isFormData =
      typeof FormData !== 'undefined' && body instanceof FormData

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
    const limitParam =
      Number(url.searchParams.get('limit')) || DEFAULT_PAGE_SIZE

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
        if (k === 'fields') {
          // Row-format's column-name list is identical on every page;
          // keep the first page's copy instead of concatenating duplicates.
          if (target[k] === undefined) target[k] = v
          continue
        }
        if (Array.isArray(v)) {
          if (!Array.isArray(target[k])) target[k] = []
          ;(target[k] as unknown[]).push(...v)
        } else if (target[k] === undefined) {
          // keep scalar metadata (e.g., units) from the first page only
          target[k] = v
        }
      }
    }

    // Row and column profiles of observations group values by datastream; a
    // datastream's group can continue on the next page.
    type Group = Columnar & { datastreamId: string }
    const isGrouped = (x: unknown): x is Group[] =>
      Array.isArray(x) &&
      x.length > 0 &&
      x.every(
        (g) =>
          isColumnar(g) &&
          typeof g.datastreamId === 'string' &&
          ('rows' in g || 'columns' in g)
      )

    // A column group with no selected per-observation property has no column
    // to count its observations by.
    const groupRowCount = (group: Group): number => {
      if (Array.isArray(group.rows)) return group.rows.length
      const column = isColumnar(group.columns)
        ? Object.values(group.columns).find(Array.isArray)
        : undefined
      return column ? column.length : 0
    }

    const groupKey = (group: Group) => String(group.datastreamId)
    const mergeGroups = (target: Map<string, Group>, groups: Group[]) => {
      for (const group of groups) {
        const existing = target.get(groupKey(group))
        if (!existing) {
          target.set(groupKey(group), {
            ...group,
            ...(Array.isArray(group.rows) ? { rows: [...group.rows] } : {}),
            ...(isColumnar(group.columns)
              ? {
                  columns: Object.fromEntries(
                    Object.entries(group.columns).map(([k, v]) => [
                      k,
                      Array.isArray(v) ? [...v] : v,
                    ])
                  ),
                }
              : {}),
          })
          continue
        }
        if (Array.isArray(existing.rows) && Array.isArray(group.rows)) {
          existing.rows.push(...group.rows)
        }
        if (isColumnar(existing.columns) && isColumnar(group.columns)) {
          concatInto(existing.columns, group.columns)
        }
      }
    }

    const pageRowCount = (data: unknown): number => {
      if (isGrouped(data)) {
        return data.reduce((sum, g) => sum + groupRowCount(g), 0)
      }
      if (Array.isArray(data)) return data.length
      if (isColumnar(data)) {
        if (Array.isArray((data as Columnar).results)) {
          return ((data as Columnar).results as unknown[]).length
        }
        for (const [k, v] of Object.entries(data as Columnar)) {
          if (k === 'fields') continue
          if (Array.isArray(v)) return v.length
        }
      }
      return 0
    }

    // Normalize first page
    let mode: 'array' | 'columnar' | 'grouped'
    let allArray: T[] = []
    const allGroups = new Map<string, Group>()
    let allColumnar: Columnar | null = null
    let firstPageMeta = res.meta as Record<string, unknown> | undefined

    type IncludedBuckets = Record<string, unknown[]>
    const mergeIncluded = (
      target: IncludedBuckets | undefined,
      src: unknown
    ): IncludedBuckets | undefined => {
      if (!isColumnar(src)) return target
      const merged = target ?? {}
      for (const [key, val] of Object.entries(src)) {
        if (!Array.isArray(val)) continue
        if (!Array.isArray(merged[key])) merged[key] = []
        merged[key].push(...val)
      }
      return merged
    }
    let mergedIncluded = mergeIncluded(undefined, res.included)

    if (isGrouped(res.data)) {
      mode = 'grouped'
      mergeGroups(allGroups, res.data)
    } else if (Array.isArray(res.data)) {
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

    const mergePageData = (page: ApiResponse<unknown>): boolean => {
      if (mode === 'grouped') {
        if (!Array.isArray(page.data)) return false
        if (isGrouped(page.data)) mergeGroups(allGroups, page.data)
        return true
      }
      if (mode === 'array') {
        if (Array.isArray(page.data)) {
          allArray.push(...(page.data as T[]))
          return true
        }
        if (isColumnar(page.data) && Array.isArray(page.data.results)) {
          // some endpoints expose { results: [] }
          allArray.push(...(page.data.results as T[]))
          return true
        }
        return false
      }
      if (isColumnar(page.data)) {
        concatInto(allColumnar!, page.data as Columnar)
        return true
      }
      if (Array.isArray(page.data)) {
        // if a later page comes back as a plain array, tuck it under `results`
        if (!Array.isArray(allColumnar!.results)) allColumnar!.results = []
        ;(allColumnar!.results as unknown[]).push(...page.data)
        return true
      }
      return false
    }

    const fetchPage = (offset: number) => {
      const pageUrl = new URL(url)
      pageUrl.searchParams.set('offset', String(offset))
      return limit(() =>
        interceptedFetch<unknown>(pageUrl.toString(), { method: 'GET' })
      )
    }

    const metaLimit = Number(firstPageMeta?.limit)
    const pageSize =
      Number.isInteger(metaLimit) && metaLimit > 0 ? metaLimit : limitParam

    const numberMatched =
      typeof firstPageMeta?.numberMatched === 'number'
        ? firstPageMeta.numberMatched
        : undefined

    const offsets: number[] = []
    if (numberMatched !== undefined) {
      for (let offset = pageSize; offset < numberMatched; offset += pageSize) {
        offsets.push(offset)
      }
    }

    const remainingPages = await Promise.all(offsets.map(fetchPage))

    let lastRowCount = pageRowCount(res.data)
    for (const page of remainingPages) {
      // Never report a partial multi-page result as successful. Callers use
      // `ok` to decide whether a management table is complete and actionable.
      if (!page.ok) return page
      mergedIncluded = mergeIncluded(mergedIncluded, page.included)
      if (!mergePageData(page)) break
      lastRowCount = pageRowCount(page.data)
    }

    let nextOffset = pageSize * (1 + offsets.length)
    const MAX_EXTRA_PAGES = 1000
    let extraPages = 0
    while (
      pageSize > 0 &&
      lastRowCount === pageSize &&
      extraPages < MAX_EXTRA_PAGES
    ) {
      const page = await fetchPage(nextOffset)
      if (!page.ok) return page
      mergedIncluded = mergeIncluded(mergedIncluded, page.included)
      if (!mergePageData(page)) break
      lastRowCount = pageRowCount(page.data)
      nextOffset += pageSize
      extraPages += 1
    }

    const merged =
      mode === 'grouped'
        ? ([...allGroups.values()] as unknown as T)
        : mode === 'array'
        ? (allArray as unknown as T)
        : (allColumnar as unknown as T)

    const mergedCount = pageRowCount(merged)

    return {
      ok: true,
      data: merged,
      status: res.status,
      message: res.message,
      meta: {
        ...(firstPageMeta ?? {}),
        offset: 0,
        limit: mergedCount,
        numberMatched: mergedCount,
        numberReturned: mergedCount,
      },
      included: mergedIncluded,
    }
  },
}
