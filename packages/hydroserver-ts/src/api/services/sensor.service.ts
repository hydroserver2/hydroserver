import { HydroServerBaseService } from './base'
import { Sensor as M } from '../../types'
import { SensorContract as C } from '../../generated/contracts'
import { apiMethods } from '../apiMethods'

export class SensorService extends HydroServerBaseService<typeof C, M> {
  static route = C.route
  static writableKeys = C.writableKeys
  static Model = M

  getEncodingTypes = () =>
    apiMethods.paginatedFetch(`${this._route}/encoding-types`)
  getMethodTypes = () =>
    apiMethods.paginatedFetch(`${this._route}/method-types`)
}
