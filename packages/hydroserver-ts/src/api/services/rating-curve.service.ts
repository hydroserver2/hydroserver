import { HydroServerBaseService, type PatchBody, type QueryParamsOf } from './base'
import { RatingCurveContract as C } from '../../generated/contracts'
import { RatingCurve as M } from '../Models/rating-curve.model'
import { apiMethods } from '../apiMethods'
import type { ApiResponse } from '../responseInterceptor'

type RatingCurveCreateBody = C.PostBody
type RatingCurvePatchBody = PatchBody<M>

export class RatingCurveService extends HydroServerBaseService<typeof C, M> {
  static route = C.route
  static writableKeys = C.writableKeys
  static Model = M

  protected override getBaseUrl(): string {
    return `${this._client.host}/api/data/products`
  }

  override create = async (
    body: M | RatingCurveCreateBody
  ): Promise<ApiResponse<M>> => {
    return apiMethods.post<M>(this._route, this.serializeCreate(body))
  }

  override createItem = async (
    body: M | RatingCurveCreateBody
  ): Promise<M | null> => {
    const res = await this.create(body)
    return res.ok ? res.data : null
  }

  override update = async (
    body: RatingCurvePatchBody,
    originalBody?: RatingCurvePatchBody
  ) => {
    return apiMethods.patch<M>(
      `${this._route}/${body.id}`,
      this.serializePatch(body),
      originalBody ? this.serializePatch(originalBody) : null
    )
  }

  override updateItem = async (
    body: RatingCurvePatchBody,
    originalBody?: RatingCurvePatchBody
  ): Promise<M | null> => {
    const res = await this.update(body, originalBody)
    return res.ok ? res.data : null
  }

  async listForThing(
    thingId: string,
    params: Partial<QueryParamsOf<typeof C>> & { fetch_all?: boolean } = {}
  ) {
    return this.list({
      ...params,
      thing_id: [thingId],
    })
  }

  async listItemsForThing(
    thingId: string,
    params: Partial<QueryParamsOf<typeof C>> & { fetch_all?: boolean } = {}
  ) {
    const res = await this.listForThing(thingId, {
      fetch_all: true,
      ...params,
    })
    return res.ok ? res.data : []
  }

  private serializeCreate(body: M | RatingCurveCreateBody): RatingCurveCreateBody {
    return {
      id: body.id || undefined,
      name: body.name,
      description: body.description ?? null,
      fittingMethod: body.fittingMethod,
      thingId: body.thingId,
      points: body.points ?? [],
    }
  }

  private serializePatch(body: RatingCurvePatchBody): C.PatchBody {
    return {
      ...(body.name !== undefined ? { name: body.name } : {}),
      ...(body.description !== undefined ? { description: body.description } : {}),
      ...(body.fittingMethod !== undefined
        ? { fittingMethod: body.fittingMethod }
        : {}),
      ...(body.points !== undefined ? { points: body.points } : {}),
    }
  }
}
