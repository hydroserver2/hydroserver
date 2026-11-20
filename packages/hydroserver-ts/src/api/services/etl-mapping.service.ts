import { HydroServerBaseService } from './base'
import { EtlMappingContract as C } from '../../generated/contracts'
import type { EtlMapping as M } from './etl-mapping.types'

export class EtlMappingService extends HydroServerBaseService<typeof C, M> {
  static route = C.route
  static writableKeys = C.writableKeys
}
