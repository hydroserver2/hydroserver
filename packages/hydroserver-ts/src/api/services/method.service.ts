import { HydroServerBaseService } from './base'
import { Method as M } from '../../types'
import { MethodContract as C } from '../../generated/contracts'

export class MethodService extends HydroServerBaseService<typeof C, M> {
  static route = C.route
  static writableKeys = C.writableKeys
  static Model = M
}
