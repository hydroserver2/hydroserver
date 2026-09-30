import { HydroServerBaseService } from './base'
import { MethodTypeContract as C } from '../../generated/contracts'
import { MethodType as M } from '../../types'

export class MethodTypeService extends HydroServerBaseService<typeof C, M> {
  static route = C.route
  static writableKeys = C.writableKeys
  static Model = M
}
