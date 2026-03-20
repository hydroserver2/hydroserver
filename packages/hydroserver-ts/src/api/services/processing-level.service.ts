import { HydroServerBaseService } from './base'
import { ProcessingLevel as M } from '../../types'
import { ProcessingLevelContract as C } from '../../generated/contracts'

export class ProcessingLevelService extends HydroServerBaseService<
  typeof C,
  M
> {
  static route = C.route
  static writableKeys = C.writableKeys
  static Model = M
}
