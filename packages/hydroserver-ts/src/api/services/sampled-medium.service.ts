import { HydroServerBaseService } from './base'
import { SampledMediumContract as C } from '../../generated/contracts'
import { SampledMedium as M } from '../../types'

export class SampledMediumService extends HydroServerBaseService<
  typeof C,
  M
> {
  static route = C.route
  static writableKeys = C.writableKeys
  static Model = M
}
