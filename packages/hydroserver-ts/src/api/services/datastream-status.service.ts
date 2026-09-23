import { HydroServerBaseService } from './base'
import { DatastreamStatusContract as C } from '../../generated/contracts'
import { DatastreamStatus as M } from '../../types'

export class DatastreamStatusService extends HydroServerBaseService<
  typeof C,
  M
> {
  static route = C.route
  static writableKeys = C.writableKeys
  static Model = M
}
