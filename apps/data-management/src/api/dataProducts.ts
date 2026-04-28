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

export type AggregationMethod = 'mean' | 'sum' | 'min' | 'max' | 'first' | 'last'
export type IntervalUnit = 'minutes' | 'hours' | 'days' | 'weeks' | 'months'
export type TimezoneType = 'utc' | 'offset' | 'iana'

export type AggregationTransformationPayload = {
  outputDatastreamId: string
  inputDatastreamId: string
  aggregationMethod: AggregationMethod
  outputIntervalUnits: IntervalUnit
  outputInterval: number
  timezoneType?: TimezoneType | null
  timezone?: string | null
  minValues?: number | null
}

export type AggregationTransformationResponse = {
  id: string
  outputDatastream?: { id: string; name: string; thingId?: string }
  inputDatastream?: { id: string; name: string; thingId?: string }
  aggregationMethod: AggregationMethod
  outputIntervalUnits: IntervalUnit
  outputInterval: number
  timezoneType?: TimezoneType | null
  timezone?: string | null
  minValues?: number | null
}

export const createAggregationTransformation = (
  taskId: string,
  payload: AggregationTransformationPayload
) =>
  request<AggregationTransformationResponse>(
    `/api/data/products/tasks/${taskId}/transformations/aggregation`,
    { method: 'POST', body: payload }
  )

export const listAggregationTransformations = (taskId: string) =>
  request<AggregationTransformationResponse[]>(
    `/api/data/products/tasks/${taskId}/transformations/aggregation`
  )

export const updateAggregationTransformation = (
  taskId: string,
  transformationId: string,
  payload: Partial<AggregationTransformationPayload>
) =>
  request<AggregationTransformationResponse>(
    `/api/data/products/tasks/${taskId}/transformations/aggregation/${transformationId}`,
    { method: 'PATCH', body: payload }
  )

export const deleteAggregationTransformation = (
  taskId: string,
  transformationId: string
) =>
  request(
    `/api/data/products/tasks/${taskId}/transformations/aggregation/${transformationId}`,
    { method: 'DELETE' }
  )

export const updateDataProductTask = (
  taskId: string,
  payload: Partial<DataProductTaskPayload>
) =>
  request<DataProductTaskResponse>(`/api/data/products/tasks/${taskId}`, {
    method: 'PATCH',
    body: payload,
  })

export const deleteDataProductTask = (taskId: string) =>
  request(`/api/data/products/tasks/${taskId}`, { method: 'DELETE' })

export const getDataProductTask = (taskId: string) =>
  request<DataProductTaskResponse>(`/api/data/products/tasks/${taskId}`)

export type CompositeExpressionInput = {
  datastreamId: string
  variableName: string
}

export type CompositeExpressionTransformationPayload = {
  outputDatastreamId: string
  inputDatastreams: CompositeExpressionInput[]
  formula: string
  outputIntervalUnits: IntervalUnit
  outputInterval: number
  maxGapInterval?: number | null
  maxGapIntervalUnits?: IntervalUnit | null
}

export type CompositeExpressionTransformationResponse = {
  id: string
  outputDatastream?: { id: string; name: string }
  inputDatastreams?: Array<{
    datastream?: { id: string; name: string }
    variableName?: string | null
  }>
  formula: string
  outputIntervalUnits: IntervalUnit
  outputInterval: number
  maxGapInterval?: number | null
  maxGapIntervalUnits?: IntervalUnit | null
}

export const createCompositeExpressionTransformation = (
  taskId: string,
  payload: CompositeExpressionTransformationPayload
) =>
  request<CompositeExpressionTransformationResponse>(
    `/api/data/products/tasks/${taskId}/transformations/composite-expression`,
    { method: 'POST', body: payload }
  )

export const listCompositeExpressionTransformations = (taskId: string) =>
  request<CompositeExpressionTransformationResponse[]>(
    `/api/data/products/tasks/${taskId}/transformations/composite-expression`
  )

export const updateCompositeExpressionTransformation = (
  taskId: string,
  transformationId: string,
  payload: Omit<CompositeExpressionTransformationPayload, 'outputDatastreamId'>
) =>
  request<CompositeExpressionTransformationResponse>(
    `/api/data/products/tasks/${taskId}/transformations/composite-expression/${transformationId}`,
    { method: 'PATCH', body: payload }
  )

export const deleteCompositeExpressionTransformation = (
  taskId: string,
  transformationId: string
) =>
  request(
    `/api/data/products/tasks/${taskId}/transformations/composite-expression/${transformationId}`,
    { method: 'DELETE' }
  )
