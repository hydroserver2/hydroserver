import hs, { type ApiResponse } from '@hydroserver/client'

type RequestOptions = {
  method?: 'GET' | 'POST' | 'PATCH' | 'DELETE'
  body?: unknown
  query?: Record<string, unknown>
}

const getCookie = (name: string) => {
  const value = `; ${document.cookie}`
  const parts = value.split(`; ${name}=`)
  if (parts.length !== 2) return ''
  return parts.pop()?.split(';').shift() ?? ''
}

const withQuery = (url: string, query?: Record<string, unknown>) => {
  if (!query) return url
  const next = new URL(url, globalThis.location?.origin ?? undefined)
  for (const [key, value] of Object.entries(query)) {
    if (value === undefined || value === null || value === '') continue
    if (Array.isArray(value)) {
      value.forEach((entry) => {
        if (entry !== undefined && entry !== null) {
          next.searchParams.append(key, String(entry))
        }
      })
    } else {
      next.searchParams.set(key, String(value))
    }
  }
  return next.toString()
}

async function request<T>(
  path: string,
  { method = 'GET', body, query }: RequestOptions = {}
): Promise<ApiResponse<T>> {
  const response = await fetch(withQuery(`${hs.host}${path}`, query), {
    method,
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCookie('csrftoken'),
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  })

  const text = await response.text()
  let data: any = null
  try {
    data = text ? JSON.parse(text) : null
  } catch {
    data = text
  }

  return {
    ok: response.ok,
    status: response.status,
    data,
    message:
      typeof data === 'string'
        ? data
        : data?.detail || data?.message || response.statusText,
  } as ApiResponse<T>
}

export type DataProductTaskPayload = {
  name: string
  description?: string | null
  thingId: string
  schedule?: unknown | null
}

export type DataProductTaskResponse = DataProductTaskPayload & {
  id: string
  thing?: { id: string; name: string }
}

export type ProductRatingCurve = {
  id: string
  name: string
  description?: string | null
  fittingMethod?: 'linear' | 'power_law'
  fitting_method?: 'linear' | 'power_law'
  thing?: { id: string; name: string }
  points?: [number, number][]
}

export type ProductRatingCurvePayload = {
  name: string
  description?: string | null
  fittingMethod: 'linear' | 'power_law'
  thingId: string
  points: [number, number][]
}

export const createDataProductTask = (payload: DataProductTaskPayload) =>
  request<DataProductTaskResponse>('/api/data/products/tasks', {
    method: 'POST',
    body: payload,
  })

export const createExpressionTransformation = (
  taskId: string,
  payload: {
    outputDatastreamId: string
    inputDatastreamId: string
    variableName: string
    formula: string
  }
) =>
  request(`/api/data/products/tasks/${taskId}/transformations/expression`, {
    method: 'POST',
    body: payload,
  })

export const listProductRatingCurves = (thingId: string) =>
  request<ProductRatingCurve[]>('/api/data/products/rating-curves', {
    query: {
      thing_id: [thingId],
      page_size: 1000,
    },
  })

export const createProductRatingCurve = (
  payload: ProductRatingCurvePayload
) =>
  request<ProductRatingCurve>('/api/data/products/rating-curves', {
    method: 'POST',
    body: payload,
  })

export const createRatingCurveTransformation = (
  taskId: string,
  payload: {
    outputDatastreamId: string
    inputDatastreamId: string
    ratingCurveId: string
  }
) =>
  request(`/api/data/products/tasks/${taskId}/transformations/rating-curve`, {
    method: 'POST',
    body: payload,
  })
