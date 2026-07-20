import { apiMethods } from '../apiMethods'
import type { HydroServer } from '../HydroServer'
import type { ApiResponse } from '../responseInterceptor'
import {
  QualityControlHistoryContract,
  QualityControlOperationContract,
  QualityControlSessionContract,
} from '../../generated/contracts'

type FetchAll = { fetch_all?: boolean }

export type QualityControlHistory =
  | QualityControlHistoryContract.SummaryResponse
  | QualityControlHistoryContract.DetailResponse
export type QualityControlSession =
  | QualityControlSessionContract.SummaryResponse
  | QualityControlSessionContract.DetailResponse
export type QualityControlOperation =
  QualityControlOperationContract.SummaryResponse

export class QualityControlHistoryService {
  private readonly _route: string

  constructor(client: HydroServer) {
    this._route = `${client.baseRoute}/quality-control/histories`
  }

  async list(
    params: Partial<QualityControlHistoryContract.QueryParameters> &
      FetchAll = {}
  ): Promise<ApiResponse<QualityControlHistory[]>> {
    const { fetch_all, ...query } = params
    const url = this.withQuery(this._route, query)
    return fetch_all
      ? apiMethods.paginatedFetch<QualityControlHistory[]>(url)
      : apiMethods.fetch<QualityControlHistory[]>(url)
  }

  async listItems(
    params: Partial<QualityControlHistoryContract.QueryParameters> &
      FetchAll = {}
  ): Promise<QualityControlHistory[]> {
    const res = await this.list(params)
    return res.ok ? res.data : []
  }

  async listAllItems(
    params: Partial<QualityControlHistoryContract.QueryParameters> = {}
  ): Promise<QualityControlHistory[]> {
    return this.listItems({ ...params, fetch_all: true })
  }

  get(
    historyId: string,
    params?: Pick<QualityControlHistoryContract.QueryParameters, 'expand_related'>
  ): Promise<ApiResponse<QualityControlHistory>> {
    return apiMethods.fetch<QualityControlHistory>(
      this.withQuery(`${this._route}/${historyId}`, params)
    )
  }

  async getItem(
    historyId: string,
    params?: Pick<QualityControlHistoryContract.QueryParameters, 'expand_related'>
  ): Promise<QualityControlHistory | null> {
    const res = await this.get(historyId, params)
    return res.ok ? res.data : null
  }

  create(
    body: QualityControlHistoryContract.PostBody
  ): Promise<ApiResponse<QualityControlHistoryContract.DetailResponse>> {
    return apiMethods.post<QualityControlHistoryContract.DetailResponse>(
      this._route,
      body
    )
  }

  async createItem(
    body: QualityControlHistoryContract.PostBody
  ): Promise<QualityControlHistoryContract.DetailResponse | null> {
    const res = await this.create(body)
    return res.ok ? res.data : null
  }

  delete(historyId: string): Promise<ApiResponse<null>> {
    return apiMethods.delete<null>(`${this._route}/${historyId}`)
  }

  private withQuery(base: string, params?: Record<string, unknown>): string {
    return withQuery(base, params)
  }
}

export class QualityControlSessionService {
  private readonly _route: string

  constructor(client: HydroServer) {
    this._route = `${client.baseRoute}/quality-control/histories`
  }

  async list(
    historyId: string,
    params: Partial<QualityControlSessionContract.QueryParameters> &
      FetchAll = {}
  ): Promise<ApiResponse<QualityControlSession[]>> {
    const { fetch_all, ...query } = params
    const url = this.withQuery(this.sessionsRoute(historyId), query)
    return fetch_all
      ? apiMethods.paginatedFetch<QualityControlSession[]>(url)
      : apiMethods.fetch<QualityControlSession[]>(url)
  }

  async listItems(
    historyId: string,
    params: Partial<QualityControlSessionContract.QueryParameters> &
      FetchAll = {}
  ): Promise<QualityControlSession[]> {
    const res = await this.list(historyId, params)
    return res.ok ? res.data : []
  }

  async listAllItems(
    historyId: string,
    params: Partial<QualityControlSessionContract.QueryParameters> = {}
  ): Promise<QualityControlSession[]> {
    return this.listItems(historyId, { ...params, fetch_all: true })
  }

  get(
    historyId: string,
    sessionId: string,
    params?: Pick<QualityControlSessionContract.QueryParameters, 'expand_related'>
  ): Promise<ApiResponse<QualityControlSession>> {
    return apiMethods.fetch<QualityControlSession>(
      this.withQuery(`${this.sessionsRoute(historyId)}/${sessionId}`, params)
    )
  }

  async getItem(
    historyId: string,
    sessionId: string,
    params?: Pick<QualityControlSessionContract.QueryParameters, 'expand_related'>
  ): Promise<QualityControlSession | null> {
    const res = await this.get(historyId, sessionId, params)
    return res.ok ? res.data : null
  }

  create(
    historyId: string,
    body: QualityControlSessionContract.PostBody
  ): Promise<ApiResponse<QualityControlSessionContract.DetailResponse>> {
    return apiMethods.post<QualityControlSessionContract.DetailResponse>(
      this.sessionsRoute(historyId),
      body
    )
  }

  async createItem(
    historyId: string,
    body: QualityControlSessionContract.PostBody
  ): Promise<QualityControlSessionContract.DetailResponse | null> {
    const res = await this.create(historyId, body)
    return res.ok ? res.data : null
  }

  update(
    historyId: string,
    sessionId: string,
    body: QualityControlSessionContract.PatchBody
  ): Promise<ApiResponse<QualityControlSessionContract.DetailResponse>> {
    return apiMethods.patch<QualityControlSessionContract.DetailResponse>(
      `${this.sessionsRoute(historyId)}/${sessionId}`,
      body
    )
  }

  async updateItem(
    historyId: string,
    sessionId: string,
    body: QualityControlSessionContract.PatchBody
  ): Promise<QualityControlSessionContract.DetailResponse | null> {
    const res = await this.update(historyId, sessionId, body)
    return res.ok ? res.data : null
  }

  delete(historyId: string, sessionId: string): Promise<ApiResponse<null>> {
    return apiMethods.delete<null>(
      `${this.sessionsRoute(historyId)}/${sessionId}`
    )
  }

  commit(
    historyId: string,
    sessionId: string
  ): Promise<ApiResponse<QualityControlSessionContract.DetailResponse>> {
    return apiMethods.post<QualityControlSessionContract.DetailResponse>(
      `${this.sessionsRoute(historyId)}/${sessionId}/commit`
    )
  }

  private sessionsRoute(historyId: string): string {
    return `${this._route}/${historyId}/sessions`
  }

  private withQuery(base: string, params?: Record<string, unknown>): string {
    return withQuery(base, params)
  }
}

export class QualityControlOperationService {
  private readonly _route: string

  constructor(client: HydroServer) {
    this._route = `${client.baseRoute}/quality-control/histories`
  }

  async list(
    historyId: string,
    sessionId: string,
    params: Partial<QualityControlOperationContract.QueryParameters> &
      FetchAll = {}
  ): Promise<ApiResponse<QualityControlOperation[]>> {
    const { fetch_all, ...query } = params
    const url = this.withQuery(this.operationsRoute(historyId, sessionId), query)
    return fetch_all
      ? apiMethods.paginatedFetch<QualityControlOperation[]>(url)
      : apiMethods.fetch<QualityControlOperation[]>(url)
  }

  async listItems(
    historyId: string,
    sessionId: string,
    params: Partial<QualityControlOperationContract.QueryParameters> &
      FetchAll = {}
  ): Promise<QualityControlOperation[]> {
    const res = await this.list(historyId, sessionId, params)
    return res.ok ? res.data : []
  }

  async listAllItems(
    historyId: string,
    sessionId: string,
    params: Partial<QualityControlOperationContract.QueryParameters> = {}
  ): Promise<QualityControlOperation[]> {
    return this.listItems(historyId, sessionId, { ...params, fetch_all: true })
  }

  get(
    historyId: string,
    sessionId: string,
    operationId: string
  ): Promise<ApiResponse<QualityControlOperation>> {
    return apiMethods.fetch<QualityControlOperation>(
      `${this.operationsRoute(historyId, sessionId)}/${operationId}`
    )
  }

  async getItem(
    historyId: string,
    sessionId: string,
    operationId: string
  ): Promise<QualityControlOperation | null> {
    const res = await this.get(historyId, sessionId, operationId)
    return res.ok ? res.data : null
  }

  create(
    historyId: string,
    sessionId: string,
    body: QualityControlOperationContract.PostBody
  ): Promise<ApiResponse<QualityControlOperation[]>> {
    return apiMethods.post<QualityControlOperation[]>(
      this.operationsRoute(historyId, sessionId),
      body
    )
  }

  async createItems(
    historyId: string,
    sessionId: string,
    body: QualityControlOperationContract.PostBody
  ): Promise<QualityControlOperation[]> {
    const res = await this.create(historyId, sessionId, body)
    return res.ok ? res.data : []
  }

  update(
    historyId: string,
    sessionId: string,
    operationId: string,
    body: QualityControlOperationContract.PatchBody
  ): Promise<ApiResponse<QualityControlOperation>> {
    return apiMethods.patch<QualityControlOperation>(
      `${this.operationsRoute(historyId, sessionId)}/${operationId}`,
      body
    )
  }

  async updateItem(
    historyId: string,
    sessionId: string,
    operationId: string,
    body: QualityControlOperationContract.PatchBody
  ): Promise<QualityControlOperation | null> {
    const res = await this.update(historyId, sessionId, operationId, body)
    return res.ok ? res.data : null
  }

  delete(
    historyId: string,
    sessionId: string,
    operationId: string
  ): Promise<ApiResponse<null>> {
    return apiMethods.delete<null>(
      `${this.operationsRoute(historyId, sessionId)}/${operationId}`
    )
  }

  private operationsRoute(historyId: string, sessionId: string): string {
    return `${this._route}/${historyId}/sessions/${sessionId}/operations`
  }

  private withQuery(base: string, params?: Record<string, unknown>): string {
    return withQuery(base, params)
  }
}

function withQuery(base: string, params?: Record<string, unknown>): string {
  if (!params || Object.keys(params).length === 0) return base
  const url = new URL(base, globalThis.location?.origin ?? undefined)
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined) continue
    if (Array.isArray(value)) {
      for (const entry of value) {
        if (entry === undefined) continue
        url.searchParams.append(key, String(entry))
      }
      continue
    }
    url.searchParams.set(key, String(value))
  }
  return url.toString()
}
