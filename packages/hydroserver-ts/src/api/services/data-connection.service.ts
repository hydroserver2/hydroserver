import { HydroServerBaseService } from './base'
import { DataConnectionContract as C } from '../../generated/contracts'
import { DataConnection as M } from '../Models/data-connection.model'

export class DataConnectionService extends HydroServerBaseService<typeof C, M> {
  static route = C.route
  static writableKeys = C.writableKeys
  static Model = M

  protected override getBaseUrl(): string {
    return this._client.etlDataBase
  }
}
