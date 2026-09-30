import { HydroServerBaseService } from './base'
import { ObservedProperty as M } from '../../types'
import { ObservedPropertyContract as C } from '../../generated/contracts'

export class ObservedPropertyService extends HydroServerBaseService<
  typeof C,
  M
> {
  static route = C.route
  static writableKeys = C.writableKeys
  static Model = M
}
