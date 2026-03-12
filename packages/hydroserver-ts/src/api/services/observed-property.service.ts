import { HydroServerBaseService } from './base'
import { ObservedProperty as M } from '../../types'
import { ObservedPropertyContract as C } from '../../generated/contracts'
import { apiMethods } from '../apiMethods'

export class ObservedPropertyService extends HydroServerBaseService<
  typeof C,
  M
> {
  static route = C.route
  static writableKeys = C.writableKeys
  static Model = M

  getVariableTypes = () =>
    apiMethods.paginatedFetch(`${this._route}/variable-types`)
}
