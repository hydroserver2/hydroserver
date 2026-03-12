import { HydroServerBaseService } from './base'
import { apiMethods } from '../apiMethods'
import { EtlDataConnectionContract as C } from '../../generated/contracts'
import { ApiResponse } from '../../index'
import { DataConnection as M } from '../Models/data-connection.model'

export class DataConnectionService extends HydroServerBaseService<typeof C, M> {
  static route = C.route
  static writableKeys = C.writableKeys
  static Model = M

  // protected override getBaseUrl() {
  //   return this._client.etlBase
  // }

  create = async (body: M): Promise<ApiResponse<M>> =>
    apiMethods.post(this._route, this.toPostObject(body))

  update = async (body: Partial<M> & Pick<M, 'id'>) =>
    apiMethods.patch(`${this._route}/${body.id}`, this.toPostObject(body as M))

  updatePartial = async (body: M) => {
    return apiMethods.patch(
      `${this._route}/${body.id}?expand_related=true`,
      body
    )
  }

  // linkDatastream = async (id: string, datastreamId: string) => {
  //   const url = `${this._route}/${id}/datastreams/${datastreamId}`
  //   return apiMethods.post(url)
  // }

  // unlinkDatastream = async (id: string, datastreamId: string) => {
  //   const url = `${this._route}/${id}/datastreams/${datastreamId}`
  //   return apiMethods.delete(url)
  // }

  private toPostObject(m: M) {
    return {
      name: m.name,
      type: m.type,
      extractor: m.extractor,
      transformer: m.transformer,
      loader: m.loader,
      workspaceId: m.workspace?.id,
    }
  }
}
