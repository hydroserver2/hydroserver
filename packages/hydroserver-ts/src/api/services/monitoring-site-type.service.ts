import { HydroServerBaseService } from './base'
import { MonitoringSiteTypeContract as C } from '../../generated/contracts'
import { MonitoringSiteType as M } from '../../types'

export class MonitoringSiteTypeService extends HydroServerBaseService<
  typeof C,
  M
> {
  static route = C.route
  static writableKeys = C.writableKeys
  static Model = M
}
