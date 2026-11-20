import { HydroServerBaseService } from './base'
import { AggregationStatisticContract as C } from '../../generated/contracts'
import { AggregationStatistic as M } from '../../types'

export class AggregationStatisticService extends HydroServerBaseService<
  typeof C,
  M
> {
  static route = C.route
  static writableKeys = C.writableKeys
  static Model = M
}
