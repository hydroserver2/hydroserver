import { HydroServerBaseService } from './base'
import { ResultQualifierContract as C } from '../../generated/contracts'
import { ResultQualifier as M } from '../../types'

export class ResultQualifierService extends HydroServerBaseService<
  typeof C,
  M
> {
  static route = C.route
  static writableKeys = C.writableKeys
  static Model = M
}
