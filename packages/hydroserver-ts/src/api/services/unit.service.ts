import { HydroServerBaseService } from './base'
import { Unit as M } from '../../types'
import { UnitContract as C } from '../../generated/contracts'
import { apiMethods } from '../apiMethods'

export class UnitService extends HydroServerBaseService<typeof C, M> {
  static route = C.route
  static writableKeys = C.writableKeys
  static Model = M

  getTypes = () => apiMethods.fetch(`${this._route}/types`)
}
