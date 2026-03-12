import { apiMethods } from '../apiMethods'
import type { HydroServer } from '../HydroServer'
import { ApiResponse } from '../responseInterceptor'

export type ApiTypes = {
  SummaryResponse: unknown
  DetailResponse: unknown
  PostBody: unknown
  PatchBody: unknown
  DeleteBody: unknown
  QueryParameters: Record<string, unknown>
}

export type ApiContract = {
  route: string
  writableKeys: readonly string[]
  __types: ApiTypes
}

export type QueryParamsOf<C extends ApiContract> =
  C['__types']['QueryParameters']
export type WritableKeysOf<C extends ApiContract> = C['writableKeys']

export type ServiceClass<C extends ApiContract, M extends { id: string }> = {
  new (client: HydroServer): HydroServerBaseService<C, M>
  route: string
  writableKeys: string[]
  Model: new () => M
}

export type PatchBody<M extends { id: string }> = Partial<M> & Pick<M, 'id'>

export abstract class HydroServerBaseService<
  C extends ApiContract,
  M extends { id: string }
> {
  protected _client: HydroServer
  protected _route: string
  protected _writableKeys: readonly string[]
  private _ModelCtor: new () => M

  constructor(client: HydroServer) {
    this._client = client
    const ctor = this.constructor as ServiceClass<C, M>
    this._route = `${this.getBaseUrl()}/${ctor.route}`
    this._writableKeys = (ctor.writableKeys ?? []) as readonly string[]
    this._ModelCtor = ctor.Model
  }

  /**  Not all resources are at api/data/ so provide this function to allow a service to override  */
  protected getBaseUrl(): string {
    return this._client.baseRoute
  }
  async list(
    params: Partial<QueryParamsOf<C>> & {
      fetch_all?: boolean
    } = {} as Partial<QueryParamsOf<C>>
  ): Promise<ApiResponse<M[]>> {
    const { fetch_all, ...query } = params
    const url = this.withQuery(this._route, query)
    return fetch_all ? apiMethods.paginatedFetch(url) : apiMethods.fetch(url)
  }

  async listItems(
    params?: Partial<QueryParamsOf<C>> & { fetch_all?: boolean }
  ) {
    const res = await this.list(params as any)
    return res.ok ? res.data : []
  }

  async listAllItems(params?: Partial<QueryParamsOf<C>>) {
    return this.listItems({ ...(params as any), fetch_all: true })
  }

  get = async (
    id: string,
    params?: {
      expand_related: boolean
    }
  ): Promise<ApiResponse<M>> =>
    await apiMethods.fetch(this.withQuery(`${this._route}/${id}`, params))

  getItem = async (
    id: string,
    params?: {
      expand_related: boolean
    }
  ) => {
    const res = await this.get(id, params)
    return res.ok ? res.data : null
  }

  create = async (body: M): Promise<ApiResponse<M>> =>
    apiMethods.post(this._route, this.serialize(body))

  createItem = async (body: M): Promise<M | null> => {
    const res = await apiMethods.post(this._route, this.serialize(body))
    return res.ok ? res.data : null
  }

  update = async (
    body: Partial<M> & Pick<M, 'id'>,
    originalBody?: Partial<M> & Pick<M, 'id'>
  ) => apiMethods.patch(`${this._route}/${body.id}`, body, originalBody ?? null)

  updateItem = async (
    body: PatchBody<M>,
    originalBody?: PatchBody<M>
  ): Promise<M | null> => {
    const res = await apiMethods.patch(
      `${this._route}/${body.id}`,
      body,
      originalBody ?? null
    )
    return res.ok ? res.data : null
  }

  delete = async (id: string) => apiMethods.delete(`${this._route}/${id}`)

  protected withQuery(base: string, params?: Record<string, unknown>): string {
    if (!params || Object.keys(params).length === 0) return base
    const url = new URL(base, globalThis.location?.origin ?? undefined)
    for (const [key, value] of Object.entries(params)) {
      if (value === undefined) continue
      url.searchParams.set(key, String(value))
    }
    return url.toString()
  }

  protected serialize(body: M): unknown {
    return body ?? {}
  }

  protected deserialize(model: M): M {
    const m = new this._ModelCtor()
    Object.assign(m as any, model)
    return m
  }
}
