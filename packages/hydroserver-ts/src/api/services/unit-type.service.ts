import { HydroServerBaseService } from './base'
import { UnitTypeContract as C } from '../../generated/contracts'
import { UnitType as M } from '../../types'

export class UnitTypeService extends HydroServerBaseService<typeof C, M> {
  static route = C.route
  static writableKeys = C.writableKeys
  static Model = M
}
