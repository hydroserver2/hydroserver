import { HydroServerBaseService } from './base'
import { LinkedResourceTypeContract as C } from '../../generated/contracts'
import { LinkedResourceType as M } from '../../types'

export class LinkedResourceTypeService extends HydroServerBaseService<
  typeof C,
  M
> {
  static route = C.route
  static writableKeys = C.writableKeys
  static Model = M
}
