import { HydroServerBaseService } from './base'
import { ObservedPropertyTypeContract as C } from '../../generated/contracts'
import { ObservedPropertyType as M } from '../../types'

export class ObservedPropertyTypeService extends HydroServerBaseService<
  typeof C,
  M
> {
  static route = C.route
  static writableKeys = C.writableKeys
  static Model = M
}
