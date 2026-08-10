import { HydroServerBaseService } from './base'
import { Method as M } from '../../types'
import { MethodContract as C } from '../../generated/contracts'
import { apiMethods } from '../apiMethods'

export class MethodService extends HydroServerBaseService<typeof C, M> {
  static route = C.route
  static writableKeys = C.writableKeys
  static Model = M

  getTypes = () => apiMethods.paginatedFetch<string[]>(`${this._route}/types`)
}
