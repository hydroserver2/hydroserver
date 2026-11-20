import { HydroServerBaseService } from './base'
import { MonitoringRuleContract as C } from '../../generated/contracts'
import type { MonitoringRule as M } from '../Models/monitoring-task.model'

export class MonitoringRuleService extends HydroServerBaseService<typeof C, M> {
  static route = C.route
  static writableKeys = C.writableKeys
}
